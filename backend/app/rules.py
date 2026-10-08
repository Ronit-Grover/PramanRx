from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from .kb import KnowledgeBase
from .models import Finding, MedicationCandidate, Severity, Verdict


DOSE_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|g)\b", re.I)
FREQUENCY_PATTERN = re.compile(r"(?P<count>\d+)\s*(?:times?|x)\s*(?:a|per)?\s*(?:day|daily)", re.I)


@dataclass(frozen=True)
class RuleOutcome:
    candidate: MedicationCandidate | None
    findings: list[Finding]
    verdict: Verdict


def _active(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not row.get("stop_date") or row["stop_date"] >= date.today().isoformat()]


def _evidence(rule: dict[str, Any]) -> list[dict[str, Any]]:
    return rule.get("evidence", [])


def parse_candidate(ai_response: str, kb: KnowledgeBase) -> MedicationCandidate | None:
    name, _ = kb.normalize_medication(ai_response)
    if not name:
        return None
    dose = DOSE_PATTERN.search(ai_response)
    frequency = FREQUENCY_PATTERN.search(ai_response)
    return MedicationCandidate(
        name=name,
        dose_value=float(dose.group("value")) if dose else None,
        dose_unit=dose.group("unit").lower() if dose else None,
        frequency=f"{frequency.group('count')} times daily" if frequency else None,
    )


def evaluate(
    context: dict[str, Any], candidate: MedicationCandidate | None, kb: KnowledgeBase
) -> RuleOutcome:
    if not candidate:
        finding = Finding(
            rule_id="PRX-INPUT-001", category="input",
            severity=Severity.warning, title="Medication could not be normalized",
            explanation="The untrusted AI response did not map to exactly one supported RxNorm-backed concept.",
            patient_fact="No structured medication candidate could be extracted from the frozen AI output.",
            recommended_next_action="Review the original output and enter a structured medication candidate.",
            certainty="insufficient_context",
            requires_override=True,
        )
        return RuleOutcome(None, [finding], Verdict.insufficient_context)

    normalized_name, medication = kb.normalize_medication(candidate.name)
    if not normalized_name or not medication:
        finding = Finding(
            rule_id="PRX-INPUT-002", category="input", severity=Severity.warning,
            title="Unsupported medication", explanation="No unique medication concept was found in the compiled KB.",
            patient_fact=f"Proposed medication: {candidate.name}",
            recommended_next_action="Verify the medication identity against an authoritative terminology source.",
            certainty="insufficient_context",
            requires_override=True,
        )
        return RuleOutcome(candidate, [finding], Verdict.insufficient_context)
    candidate = candidate.model_copy(update={"name": normalized_name})
    policies = {policy["id"]: policy for policy in kb.policies}
    findings: list[Finding] = []
    name_lower = normalized_name.casefold()

    allergy_terms = " ".join(row["description"] for row in _active(context.get("allergies", []))).casefold()
    allergy_groups = medication.get("allergy_terms", [])
    if any(term.casefold() in allergy_terms for term in allergy_groups):
        rule = policies["PRX-ALLERGY-001"]
        findings.append(Finding(
            rule_id=rule["id"], category="allergy", severity=Severity.critical,
            title=f"Possible allergy conflict: {normalized_name}",
            explanation="An active patient allergy matches this medication or its prototype cross-reactivity group.",
            patient_fact=f"Active allergy record: {allergy_terms}",
            evidence=_evidence(rule), requires_override=True,
            recommended_next_action="Do not proceed until the allergy conflict is independently reviewed.",
            certainty="deterministic_match",
        ))

    for current in _active(context.get("medications", [])):
        current_name, _ = kb.normalize_medication(current["description"])
        if current_name and current_name != normalized_name:
            interaction = kb.interaction(normalized_name, current_name)
            if interaction:
                severity = Severity.critical if interaction["level"].lower() == "major" else Severity.warning
                findings.append(Finding(
                    rule_id=interaction["rule_id"], category="drug_interaction", severity=severity,
                    title=f"{interaction['level']} interaction with {current_name}",
                    explanation=interaction["explanation"], evidence=interaction["evidence"],
                    patient_fact=f"Active medication: {current['description']}",
                    recommended_next_action="Review the interacting therapy and select or document an alternative.",
                    certainty="deterministic_match",
                    requires_override=severity == Severity.critical,
                ))

    duplicate = next((row for row in _active(context.get("medications", []))
                      if kb.normalize_medication(row["description"])[0] == normalized_name), None)
    if duplicate:
        rule = policies.get("PRX-DUPLICATE-001", policies["PRX-DOSE-001"])
        findings.append(Finding(
            rule_id="PRX-DUPLICATE-001", category="duplicate_therapy", severity=Severity.warning,
            title=f"Possible duplicate therapy: {normalized_name}",
            explanation="The proposed medication matches an active medication in the authoritative patient context.",
            patient_fact=f"Active medication: {duplicate['description']}", evidence=_evidence(rule),
            recommended_next_action="Confirm whether this is an intentional continuation or a duplicate order.",
            certainty="deterministic_match", requires_override=False,
        ))

    condition_text = " ".join(row["description"] for row in _active(context.get("conditions", []))).casefold()
    observation_text = " ".join(
        f"{row['description']} {row.get('value', '')} {row.get('units', '')}"
        for row in context.get("observations", [])
    ).casefold()
    pregnant = "pregnan" in condition_text or "pregnan" in observation_text
    if pregnant and name_lower in {"isotretinoin", "lisinopril"}:
        rule = policies["PRX-PREGNANCY-001"]
        findings.append(Finding(
            rule_id=rule["id"], category="pregnancy", severity=Severity.critical,
            title=f"Pregnancy contraindication: {normalized_name}",
            explanation=rule["explanation"], evidence=_evidence(rule), requires_override=True,
            patient_fact="Authoritative patient context contains an active pregnancy indicator.",
            recommended_next_action="Stop and obtain specialist review before any exposure.",
            certainty="deterministic_match",
        ))

    renal_risk = any(term in condition_text for term in ("chronic kidney", "renal failure", "kidney disease"))
    for row in context.get("observations", []):
        if row.get("code") in {"33914-3", "48642-3", "48643-1"}:
            try:
                renal_risk = renal_risk or float(row.get("value", 999)) < 30
            except (TypeError, ValueError):
                pass
    if renal_risk and name_lower in {"metformin", "ibuprofen"}:
        rule = policies["PRX-RENAL-001"]
        findings.append(Finding(
            rule_id=rule["id"], category="renal", severity=Severity.critical,
            title=f"Renal risk: {normalized_name}", explanation=rule["explanation"],
            evidence=_evidence(rule), requires_override=True,
            patient_fact="Authoritative context indicates severe renal impairment or eGFR below 30.",
            recommended_next_action="Review renal function and medication suitability before proceeding.",
            certainty="deterministic_match",
        ))

    renal_sensitive = name_lower in {"metformin", "ibuprofen"}
    has_renal_context = renal_risk or any(
        row.get("code") in {"33914-3", "48642-3", "48643-1"}
        for row in context.get("observations", [])
    )
    if renal_sensitive and not has_renal_context:
        rule = policies.get("PRX-CONTEXT-001", policies["PRX-RENAL-001"])
        findings.append(Finding(
            rule_id="PRX-CONTEXT-001", category="missing_context", severity=Severity.warning,
            title="Renal function is missing",
            explanation="The prototype requires recent renal context before evaluating this medication.",
            patient_fact="No recognized renal diagnosis or eGFR observation was found.",
            evidence=_evidence(rule),
            recommended_next_action="Obtain or confirm a recent renal-function result.",
            certainty="insufficient_context", requires_override=True,
        ))

    if candidate.dose_value and candidate.dose_unit == "mg":
        max_single = medication.get("prototype_max_single_dose_mg")
        if max_single and candidate.dose_value > max_single:
            rule = policies["PRX-DOSE-001"]
            findings.append(Finding(
                rule_id=rule["id"], category="dose", severity=Severity.critical,
                title=f"Dose exceeds prototype threshold ({max_single:g} mg)",
                explanation="The proposed single dose exceeds the conservative threshold encoded for this demo.",
                evidence=_evidence(rule), requires_override=True,
                patient_fact=f"Proposed single dose: {candidate.dose_value:g} mg",
                recommended_next_action="Confirm dose, units, formulation, and frequency before proceeding.",
                certainty="deterministic_match",
            ))

    frequency = FREQUENCY_PATTERN.search(candidate.frequency or "")
    if frequency and int(frequency.group("count")) > 4:
        rule = policies["PRX-DOSE-001"]
        findings.append(Finding(
            rule_id="PRX-FREQUENCY-001", category="frequency", severity=Severity.critical,
            title="Frequency exceeds prototype boundary",
            explanation="The proposed frequency exceeds the conservative prototype boundary of four administrations daily.",
            patient_fact=f"Proposed frequency: {candidate.frequency}", evidence=_evidence(rule),
            recommended_next_action="Confirm frequency, formulation, and indication before proceeding.",
            certainty="conservative_policy", requires_override=True,
        ))

    if medication.get("prototype_formulary") is False:
        rule = policies["PRX-FORMULARY-001"]
        findings.append(Finding(
            rule_id=rule["id"], category="formulary", severity=Severity.warning,
            title="Not on prototype formulary", explanation=rule["explanation"],
            evidence=_evidence(rule), requires_override=False,
            patient_fact=f"Proposed medication: {normalized_name}",
            recommended_next_action="Check the applicable local formulary or policy.",
            certainty="conservative_policy",
        ))

    if any(f.severity == Severity.critical for f in findings):
        verdict = Verdict.critical_flag
    elif any(f.category == "missing_context" for f in findings):
        verdict = Verdict.insufficient_context
    elif findings:
        verdict = Verdict.caution
    else:
        verdict = Verdict.pass_
    return RuleOutcome(candidate, findings, verdict)
