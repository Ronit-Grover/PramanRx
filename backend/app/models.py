from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


DISCLAIMER = (
    "Research prototype output only. Not medical advice or validated clinical "
    "decision support; a qualified clinician must independently review findings."
)


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Verdict(str, Enum):
    pass_ = "pass"
    caution = "caution"
    critical_flag = "critical_flag"
    insufficient_context = "insufficient_context"
    integrity_failure = "integrity_failure"


class MedicationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=160)
    dose_value: float | None = Field(default=None, gt=0)
    dose_unit: str | None = Field(default=None, max_length=20)
    route: str | None = Field(default=None, max_length=40)
    frequency: str | None = Field(default=None, max_length=80)

    @field_validator("name", "dose_unit", "route", "frequency")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=80)
    ai_response: str = Field(min_length=1, max_length=20_000)
    candidate: MedicationCandidate | None = None
    source_adapter: Literal["deterministic", "ollama", "external", "direct"] = "direct"
    source_model: str | None = Field(default=None, max_length=160)
    recommendation_timestamp: datetime | None = None
    request_id: str | None = Field(default=None, max_length=100)


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=4_000)
    adapter: Literal["deterministic", "ollama", "external"] = "deterministic"


class Finding(BaseModel):
    rule_id: str
    category: str
    severity: Severity
    title: str
    explanation: str
    patient_fact: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    recommended_next_action: str
    certainty: Literal["deterministic_match", "conservative_policy", "insufficient_context"]
    requires_override: bool = False


class EvaluationResult(BaseModel):
    evaluation_id: str
    created_at: datetime
    patient_id: str
    verdict: Verdict
    candidate: MedicationCandidate | None
    findings: list[Finding]
    patient_context_hash: str
    kb_version: str
    kb_digest: str
    source_adapter: str
    ai_trust: Literal["untrusted"] = "untrusted"
    disclaimer: str = DISCLAIMER


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["accept", "acknowledge", "override", "reject"]
    actor: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=3, max_length=1_000)


class PatientCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    gender: Literal["M", "F", "X", "U"]
    race: str | None = Field(default=None, max_length=80)
    ethnicity: str | None = Field(default=None, max_length=80)


class FHIRHumanName(BaseModel):
    use: str = "official"
    family: str
    given: list[str]


class FHIRPatient(BaseModel):
    resourceType: Literal["Patient"] = "Patient"
    id: str
    active: bool = True
    name: list[FHIRHumanName]
    gender: str
    birthDate: str
    deceasedDateTime: str | None = None
    address: list[dict[str, Any]] = Field(default_factory=list)
    extension: list[dict[str, Any]] = Field(default_factory=list)
