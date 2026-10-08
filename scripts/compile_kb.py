#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.crypto import ensure_keypair, sign_bytes  # noqa: E402


MEDICATIONS = {
    "acetaminophen": {"aliases": ["paracetamol", "tylenol"], "max": 1000, "formulary": True},
    "amoxicillin": {"aliases": ["amoxil"], "max": 1000, "formulary": True,
                    "allergy_terms": ["penicillin", "amoxicillin"]},
    "clarithromycin": {"aliases": ["biaxin"], "max": 500, "formulary": True,
                       "allergy_terms": ["macrolide", "clarithromycin"]},
    "ibuprofen": {"aliases": ["advil", "motrin"], "max": 800, "formulary": True,
                  "allergy_terms": ["ibuprofen", "nsaid", "non-steroidal anti-inflammatory"]},
    "isotretinoin": {"aliases": ["accutane"], "max": 80, "formulary": False,
                     "allergy_terms": ["isotretinoin"]},
    "lisinopril": {"aliases": ["zestril", "prinivil"], "max": 40, "formulary": True,
                   "allergy_terms": ["lisinopril", "ace inhibitor"]},
    "metformin": {"aliases": ["glucophage"], "max": 1000, "formulary": True,
                  "allergy_terms": ["metformin"]},
    "simvastatin": {"aliases": ["zocor"], "max": 40, "formulary": True,
                    "allergy_terms": ["simvastatin", "statin"]},
    "warfarin": {"aliases": ["coumadin", "jantoven"], "max": 10, "formulary": True,
                 "allergy_terms": ["warfarin"]},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sources(source_root: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    checksum_file = source_root / "SHA256SUMS.txt"
    if not checksum_file.exists():
        raise RuntimeError("SHA256SUMS.txt is missing")
    for line in checksum_file.read_text().splitlines():
        if not line.strip():
            continue
        expected, raw_path = line.split(maxsplit=1)
        listed_path = Path(raw_path.strip())
        if listed_path.is_absolute():
            source_folders = {"ddinter", "openfda", "rxclass", "rxnorm", "rxterms"}
            folder_index = next(
                (index for index, part in enumerate(listed_path.parts) if part in source_folders),
                None,
            )
            relative = (
                Path(*listed_path.parts[folder_index:])
                if folder_index is not None
                else Path(listed_path.name)
            )
        else:
            relative = listed_path
        path = (source_root / relative).resolve()
        try:
            relative = path.relative_to(source_root.resolve())
        except ValueError as exc:
            raise RuntimeError(f"Checksum path escapes source root: {path}") from exc
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"Integrity failure: {relative}")
        checksums[str(relative)] = actual
    if not checksums:
        raise RuntimeError("No source checksums were loaded")
    return checksums


def rxnorm_summary(source_root: Path, medication: str) -> dict[str, Any]:
    path = source_root / "rxnorm" / f"{medication}_concepts_2026-10-06.json"
    payload = json.loads(path.read_text())
    concepts: list[dict[str, str]] = []
    for group in payload.get("drugGroup", {}).get("conceptGroup", []):
        for item in group.get("conceptProperties", []) or []:
            if item.get("suppress") == "N":
                concepts.append({"rxcui": item["rxcui"], "name": item["name"], "tty": item["tty"]})
    return {"source_file": str(path.relative_to(source_root)), "concept_count": len(concepts),
            "sample_concepts": concepts[:12]}


def rxclass_summary(source_root: Path, medication: str) -> dict[str, Any]:
    path = source_root / "rxclass" / f"{medication}_atc_classes_2026-10-06.json"
    payload = json.loads(path.read_text())
    records = payload.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []) or []
    classes = [{"id": row["rxclassMinConceptItem"]["classId"],
                "name": row["rxclassMinConceptItem"]["className"]} for row in records]
    ingredient = records[0].get("minConcept", {}) if records else {}
    return {"source_file": str(path.relative_to(source_root)), "ingredient_rxcui": ingredient.get("rxcui"),
            "classes": classes}


def fda_evidence(source_root: Path, medication: str, section: str) -> dict[str, Any]:
    path = source_root / "openfda" / f"{medication}_labels_2026-10-06.json"
    payload = json.loads(path.read_text())
    result = (payload.get("results") or [{}])[0]
    record_id = result.get("id") or result.get("set_id") or result.get("openfda", {}).get("spl_id", ["unknown"])[0]
    return {"source": "openFDA", "source_file": str(path.relative_to(source_root)),
            "source_record": record_id, "section": section, "retrieved_at": "2026-10-06"}


def ddinter_pairs(source_root: Path) -> list[dict[str, Any]]:
    wanted = {frozenset(("warfarin", "ibuprofen")), frozenset(("simvastatin", "clarithromycin"))}
    found: dict[frozenset[str], dict[str, Any]] = {}
    for path in sorted((source_root / "ddinter").glob("*.csv")):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row_number, row in enumerate(csv.DictReader(handle), start=2):
                key = frozenset((row["Drug_A"].casefold(), row["Drug_B"].casefold()))
                if key in wanted and key not in found:
                    found[key] = {
                        "drug_a": row["Drug_A"].casefold(), "drug_b": row["Drug_B"].casefold(),
                        "level": row["Level"], "rule_id": "PRX-DDI-" + str(len(found) + 1).zfill(3),
                        "explanation": (
                            f"DDInter classifies the {row['Drug_A']} and {row['Drug_B']} pair as "
                            f"{row['Level']}. This prototype finding requires clinician review."
                        ),
                        "evidence": [{"source": "DDInter", "source_file": str(path.relative_to(source_root)),
                                      "source_record": f"row:{row_number}", "retrieved_at": "2026-10-06"}],
                    }
    missing = wanted - set(found)
    if missing:
        raise RuntimeError(f"Required DDInter pairs missing: {missing}")
    return sorted(found.values(), key=lambda value: (value["drug_a"], value["drug_b"]))


def compile_artifact(source_root: Path, checksums: dict[str, str]) -> dict[str, Any]:
    compiled_at = datetime.now(UTC)
    medications: dict[str, Any] = {}
    for name, policy in MEDICATIONS.items():
        medications[name] = {
            "aliases": policy["aliases"], "allergy_terms": policy.get("allergy_terms", [name]),
            "prototype_max_single_dose_mg": policy["max"],
            "prototype_formulary": policy["formulary"],
            "rxnorm": rxnorm_summary(source_root, name), "rxclass": rxclass_summary(source_root, name),
        }
    policy_author = "PramanRx prototype policy; not a source-authored clinical rule"
    policies = [
        {"id": "PRX-ALLERGY-001", "author": policy_author,
         "explanation": "Prototype matching of active allergy text to normalized medication groups.",
         "evidence": [fda_evidence(source_root, "amoxicillin", "contraindications")]},
        {"id": "PRX-PREGNANCY-001", "author": policy_author,
         "explanation": "The proposed medication has label evidence indicating serious pregnancy risk.",
         "evidence": [fda_evidence(source_root, "isotretinoin", "pregnancy")]},
        {"id": "PRX-RENAL-001", "author": policy_author,
         "explanation": "Severe renal impairment requires avoidance or expert dose review in this prototype.",
         "evidence": [fda_evidence(source_root, "metformin", "renal_impairment")]},
        {"id": "PRX-DOSE-001", "author": policy_author,
         "explanation": "Conservative prototype maximum single-dose thresholds derived from label dosage sections.",
         "evidence": [fda_evidence(source_root, "acetaminophen", "dosage_and_administration")]},
        {"id": "PRX-FORMULARY-001", "author": policy_author,
         "explanation": "The candidate is outside the prototype formulary and needs workflow review.",
         "evidence": [{"source": "PramanRx prototype policy", "source_record": "formulary-v1",
                       "retrieved_at": "2026-10-06"}]},
    ]
    return {
        "schema_version": "pramanrx-kb/v1", "version": "2026.10.06-prototype.1",
        "compiled_at": compiled_at.isoformat(), "valid_until": (compiled_at + timedelta(days=90)).isoformat(),
        "transformation_version": "compile-kb/1.1.0",
        "classification": "research-prototype-only", "medications": medications,
        "interactions": ddinter_pairs(source_root), "policies": policies,
        "sources": [{"path": path, "sha256": digest} for path, digest in sorted(checksums.items())],
        "limitations": [
            "Not medical advice or validated clinical decision support.",
            "openFDA records are unvalidated and product labels may differ.",
            "DDInter may be incomplete; absence of an interaction is not proof of safety.",
            "Compiled coverage is intentionally limited to prototype medications and scenarios.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile and sign the PramanRx prototype KB")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/compiled")
    parser.add_argument("--runtime-dir", type=Path, default=PROJECT_ROOT / "data/runtime")
    args = parser.parse_args()
    checksums = verify_sources(args.source_root)
    artifact = compile_artifact(args.source_root, checksums)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    private_key = args.runtime_dir / "pramanrx-ed25519-private.pem"
    public_key = args.output_dir / "pramanrx-ed25519-public.pem"
    ensure_keypair(private_key, public_key)
    payload = (json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
    output = args.output_dir / "kb-v1.json"
    signature = args.output_dir / "kb-v1.sig"
    output.write_bytes(payload)
    signature.write_bytes(sign_bytes(payload, private_key))
    manifest = {
        "artifact": output.name, "sha256": hashlib.sha256(payload).hexdigest(),
        "signature": signature.name, "algorithm": "Ed25519", "public_key": public_key.name,
        "source_integrity_verified": True,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
