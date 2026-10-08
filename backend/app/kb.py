from __future__ import annotations

import json
from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .crypto import sha256_bytes, verify_bytes


class KnowledgeBaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class KnowledgeBase:
    artifact: dict[str, Any]
    digest: str

    @property
    def version(self) -> str:
        return str(self.artifact["version"])

    @property
    def medications(self) -> dict[str, dict[str, Any]]:
        return self.artifact["medications"]

    @property
    def interactions(self) -> list[dict[str, Any]]:
        return self.artifact["interactions"]

    @property
    def policies(self) -> list[dict[str, Any]]:
        return self.artifact["policies"]

    def normalize_medication(self, value: str) -> tuple[str | None, dict[str, Any] | None]:
        lowered = value.casefold()
        matches: list[tuple[str, dict[str, Any]]] = []
        for canonical, medication in self.medications.items():
            aliases = [canonical, *medication.get("aliases", [])]
            if any(alias.casefold() in lowered for alias in aliases):
                matches.append((canonical, medication))
        if len(matches) == 1:
            return matches[0]
        return None, None

    def interaction(self, first: str, second: str) -> dict[str, Any] | None:
        target = {first.casefold(), second.casefold()}
        for interaction in self.interactions:
            if {interaction["drug_a"].casefold(), interaction["drug_b"].casefold()} == target:
                return interaction
        return None


def load_verified_kb(kb_path: Path, signature_path: Path, public_key_path: Path) -> KnowledgeBase:
    try:
        payload = kb_path.read_bytes()
        signature = signature_path.read_bytes()
    except OSError as exc:
        raise KnowledgeBaseError(f"KB artifact unavailable: {exc}") from exc
    if not verify_bytes(payload, signature, public_key_path):
        raise KnowledgeBaseError("KB signature verification failed")
    try:
        artifact = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise KnowledgeBaseError("KB JSON is invalid") from exc
    required = {"schema_version", "version", "compiled_at", "valid_until", "medications", "interactions", "policies", "sources"}
    if not required.issubset(artifact) or artifact["schema_version"] != "pramanrx-kb/v1":
        raise KnowledgeBaseError("KB schema validation failed")
    try:
        valid_until = datetime.fromisoformat(artifact["valid_until"])
    except (TypeError, ValueError) as exc:
        raise KnowledgeBaseError("KB validity timestamp is invalid") from exc
    if valid_until < datetime.now(UTC):
        raise KnowledgeBaseError("KB artifact is stale")
    return KnowledgeBase(artifact=artifact, digest=sha256_bytes(payload))
