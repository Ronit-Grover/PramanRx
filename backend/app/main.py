from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
import urllib.request

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .adapters import AdapterError, DeterministicAdapter, ExternalAdapter, OllamaAdapter
from .audit import append_action, verify_chain
from .config import Settings, settings
from .crypto import ensure_keypair
from .database import Database
from .kb import KnowledgeBaseError, load_verified_kb
from .models import ActionRequest, EvaluationRequest, FHIRHumanName, FHIRPatient, GenerateRequest, PatientCreateRequest
from .scenarios import SCENARIOS
from .service import EvaluationService, adapter_payload


def create_app(app_settings: Settings = settings) -> FastAPI:
    db = Database(app_settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.initialize()
        ensure_keypair(app_settings.private_key_path, app_settings.public_key_path)
        try:
            kb = load_verified_kb(
                app_settings.kb_path, app_settings.kb_signature_path, app_settings.public_key_path
            )
        except KnowledgeBaseError as exc:
            app.state.kb_error = str(exc)
            app.state.kb = None
        else:
            app.state.kb_error = None
            app.state.kb = kb
            app.state.service = EvaluationService(db, kb, app_settings)
        yield

    app = FastAPI(
        title="PramanRx API", version="0.1.0",
        description="Research prototype medication verification API. Not for clinical use.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False, allow_methods=["*"], allow_headers=["*"],
    )

    def require_kb() -> None:
        if app.state.kb is None:
            raise HTTPException(status_code=503, detail={
                "code": "KB_UNAVAILABLE", "message": app.state.kb_error, "fail_closed": True,
            })

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok" if app.state.kb else "degraded", "kb_verified": bool(app.state.kb),
                "kb_error": app.state.kb_error, "service": "pramanrx"}

    @app.get("/api/v1/kb/status")
    def kb_status() -> dict[str, Any]:
        require_kb()
        kb = app.state.kb
        return {"verified": True, "version": kb.version, "digest": kb.digest,
                "source_count": len(kb.artifact["sources"]), "policy_count": len(kb.policies)}

    @app.post("/api/v1/kb/verify")
    def kb_verify() -> dict[str, Any]:
        try:
            verified = load_verified_kb(
                app_settings.kb_path, app_settings.kb_signature_path, app_settings.public_key_path
            )
        except KnowledgeBaseError as exc:
            return {"verified": False, "verdict": "integrity_failure", "error": str(exc), "fail_closed": True}
        return {"verified": True, "version": verified.version, "digest": verified.digest, "fail_closed": False}

    @app.get("/api/v1/patients")
    def patients(limit: int = Query(25, ge=1, le=2000), offset: int = Query(0, ge=0),
                 q: str | None = Query(None, max_length=120)) -> dict[str, Any]:
        items = db.list_patients(limit, offset, q)
        return {"items": items, "limit": limit, "offset": offset}

    @app.post("/api/v1/patients", status_code=201)
    def create_patient(request: PatientCreateRequest) -> dict[str, Any]:
        return db.create_patient(request.model_dump())

    @app.get("/api/v1/patients/{patient_id}")
    def patient(patient_id: str) -> dict[str, Any]:
        result = db.get_patient(patient_id)
        if not result:
            raise HTTPException(status_code=404, detail="Patient not found")
        return result

    @app.get("/api/v1/patients/{patient_id}/context")
    def patient_context(patient_id: str) -> dict[str, Any]:
        result = db.patient_context(patient_id)
        if not result:
            raise HTTPException(status_code=404, detail="Patient not found")
        result["trust"] = "authoritative_synthetic_record"
        return result

    @app.get("/fhir/Patient/{patient_id}", response_model=FHIRPatient)
    def fhir_patient(patient_id: str) -> FHIRPatient:
        result = db.get_patient(patient_id)
        if not result:
            raise HTTPException(status_code=404, detail="Patient not found")
        address = result["address"]
        return FHIRPatient(
            id=result["id"], name=[FHIRHumanName(family=result["last_name"], given=[result["first_name"]])],
            gender={"M": "male", "F": "female"}.get(result["gender"], "unknown"),
            birthDate=result["birth_date"], deceasedDateTime=result["death_date"],
            address=[address] if address else [],
            extension=[
                {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                 "valueString": result.get("race") or "unknown"},
                {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                 "valueString": result.get("ethnicity") or "unknown"},
            ],
        )

    @app.post("/api/v1/ai/generate")
    def generate(request: GenerateRequest) -> dict[str, Any]:
        adapters = {
            "deterministic": DeterministicAdapter(),
            "ollama": OllamaAdapter(app_settings.ollama_url, app_settings.ollama_model),
            "external": ExternalAdapter(app_settings.external_ai_url, app_settings.external_ai_token),
        }
        try:
            response = adapters[request.adapter].generate(request.prompt)
        except AdapterError as exc:
            raise HTTPException(status_code=502, detail={"code": "ADAPTER_ERROR", "message": str(exc)}) from exc
        return adapter_payload(response)

    @app.get("/api/v1/adapters")
    def adapters() -> dict[str, Any]:
        return {"items": [
            {"id": "deterministic", "model": "pramanrx-deterministic-fixture-v1", "available": True,
             "patient_context_shared": False},
            {"id": "ollama", "model": app_settings.ollama_model, "available": True,
             "patient_context_shared": False},
            {"id": "external", "model": "configured-external", "available": bool(app_settings.external_ai_url),
             "patient_context_shared": False},
            {"id": "direct", "model": "direct-ingestion", "available": True,
             "patient_context_shared": False},
        ]}

    @app.post("/api/v1/evaluations", status_code=201)
    def create_evaluation(request: EvaluationRequest) -> dict[str, Any]:
        require_kb()
        try:
            return app.state.service.evaluate(request).model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Patient not found") from exc

    @app.get("/api/v1/evaluations/{evaluation_id}")
    def get_evaluation(evaluation_id: str) -> dict[str, Any]:
        result = db.get_evaluation(evaluation_id)
        if not result:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        return result

    @app.get("/api/v1/evaluations/{evaluation_id}/timeline")
    def evaluation_timeline(evaluation_id: str) -> dict[str, Any]:
        items = db.evaluation_timeline(evaluation_id)
        if not items:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        return {"items": items}

    @app.post("/api/v1/evaluations/{evaluation_id}/actions", status_code=201)
    def action(evaluation_id: str, request: ActionRequest) -> dict[str, Any]:
        try:
            return append_action(db, evaluation_id, request.actor, request.action,
                                 request.reason, app_settings.private_key_path)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Evaluation not found") from exc

    @app.get("/api/v1/audit/verify")
    def audit_verify() -> dict[str, Any]:
        return verify_chain(db, app_settings.public_key_path)

    @app.get("/api/v1/audit/events")
    def audit_events(limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
        return {"items": db.audit_events(limit)}

    @app.get("/api/v1/scenarios")
    def scenarios() -> dict[str, Any]:
        return {"items": SCENARIOS}

    @app.post("/api/v1/scenarios/{scenario_id}/run")
    def run_scenario(scenario_id: str) -> dict[str, Any]:
        scenario = next((item for item in SCENARIOS if item["id"] == scenario_id), None)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        if scenario.get("simulation") == "invalid_kb":
            return {"scenario_id": scenario_id, "verdict": "integrity_failure", "findings": [{
                "rule_id": "PRX-INTEGRITY-001", "category": "knowledge_integrity", "severity": "critical",
                "title": "KB signature verification failed", "explanation": "A deliberately invalid signature was rejected.",
                "patient_fact": None, "evidence": [], "recommended_next_action": "Block evaluation and restore a verified KB artifact.",
                "certainty": "deterministic_match", "requires_override": False,
            }], "simulated": True}
        if scenario.get("simulation") == "audit_tamper":
            return {"scenario_id": scenario_id, "verdict": "integrity_failure", "findings": [{
                "rule_id": "PRX-AUDIT-001", "category": "audit_integrity", "severity": "critical",
                "title": "Audit tampering detected", "explanation": "A deliberately altered copy fails hash-chain verification.",
                "patient_fact": None, "evidence": [], "recommended_next_action": "Preserve evidence and investigate the integrity event.",
                "certainty": "deterministic_match", "requires_override": False,
            }], "simulated": True}
        request = EvaluationRequest(patient_id=scenario["patient_id"], ai_response=scenario["ai_response"],
                                    source_adapter="deterministic", request_id=f"scenario:{scenario_id}")
        return app.state.service.evaluate(request).model_dump(mode="json")

    @app.get("/api/v1/system/status")
    def system_status() -> dict[str, Any]:
        try:
            with urllib.request.urlopen(f"{app_settings.ollama_url}/api/tags", timeout=0.4) as response:
                ollama_ok = response.status == 200
        except Exception:
            ollama_ok = False
        with db.connect() as connection:
            database_ok = connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            patient_count = connection.execute("SELECT count(*) FROM patients").fetchone()[0]
        return {"api": "ok", "database": "ok" if database_ok else "error",
                "patient_store": {"status": "ok", "patients": patient_count},
                "knowledge_base": "verified" if app.state.kb else "integrity_failure",
                "ollama": "available" if ollama_ok else "unavailable",
                "default_model": app_settings.ollama_model}

    return app


app = create_app()
