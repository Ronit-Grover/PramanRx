from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .adapters import AdapterResponse
from .audit import append_evaluation
from .config import Settings
from .database import Database
from .kb import KnowledgeBase
from .models import EvaluationRequest, EvaluationResult
from .rules import evaluate, parse_candidate


class EvaluationService:
    def __init__(self, db: Database, kb: KnowledgeBase, settings: Settings):
        self.db = db
        self.kb = kb
        self.settings = settings

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        context = self.db.patient_context(request.patient_id)
        if not context:
            raise KeyError(request.patient_id)
        candidate = request.candidate or parse_candidate(request.ai_response, self.kb)
        outcome = evaluate(context, candidate, self.kb)
        context_digest = hashlib.sha256(
            json.dumps(context, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        result = EvaluationResult(
            evaluation_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
            patient_id=request.patient_id,
            verdict=outcome.verdict,
            candidate=outcome.candidate,
            findings=outcome.findings,
            patient_context_hash=context_digest,
            kb_version=self.kb.version,
            kb_digest=self.kb.digest,
            source_adapter=request.source_adapter,
        )
        request_data = request.model_dump(mode="json")
        result_data = result.model_dump(mode="json")
        append_evaluation(self.db, request_data, result_data, self.settings.private_key_path)
        return result


def adapter_payload(response: AdapterResponse) -> dict[str, Any]:
    return {
        "adapter": response.adapter,
        "model": response.model,
        "text": response.text,
        "trust": "untrusted",
        "authoritative_patient_context_shared": False,
        "context_disclosure": list(response.context_disclosure),
    }
