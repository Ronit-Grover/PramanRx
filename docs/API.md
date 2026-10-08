# PramanRx API

The local FastAPI service uses JSON under `/api/v1`. Swagger/OpenAPI documentation is available at `/docs`. All clinical content is synthetic research data.

## Patients

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/patients?limit=25&offset=0&q=` | Search or page the imported patient corpus |
| `POST` | `/api/v1/patients` | Create a clearly labeled synthetic patient |
| `GET` | `/api/v1/patients/{patient_id}` | Read the source patient row |
| `GET` | `/api/v1/patients/{patient_id}/context` | Retrieve normalized authoritative `PatientContext` |
| `GET` | `/fhir/Patient/{patient_id}` | Retrieve the FHIR-compatible Patient projection |

Patient context is retrieved by PramanRx only after recommendation capture in the primary workflow. It is never automatically sent to an AI adapter.

## AI Adapters

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/adapters` | List deterministic, Ollama, external, and direct-ingestion capabilities |
| `POST` | `/api/v1/ai/generate` | Generate untrusted text through deterministic, Ollama, or configured external adapter |

Generation request:

```json
{"adapter":"ollama","prompt":"Suggest one medication option for the demonstration."}
```

The response explicitly includes `trust: "untrusted"`, model provenance, and `authoritative_patient_context_shared: false`. Direct ingestion is represented by submitting frozen external text to the evaluation endpoint with `source_adapter: "direct"`.

## Evaluations

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/evaluations` | Freeze and evaluate an untrusted recommendation |
| `GET` | `/api/v1/evaluations/{evaluation_id}` | Read an immutable evaluation result |
| `GET` | `/api/v1/evaluations/{evaluation_id}/timeline` | Read evaluation and clinician-action audit events |
| `POST` | `/api/v1/evaluations/{evaluation_id}/actions` | Record accept, reject, acknowledge, or override |

Evaluation request:

```json
{
  "patient_id": "demo-warfarin",
  "ai_response": "Consider ibuprofen 400 mg twice daily.",
  "source_adapter": "deterministic",
  "source_model": "pramanrx-deterministic-fixture-v1",
  "request_id": "caller-generated-replay-resistant-id"
}
```

The verdict is one of `pass`, `caution`, `critical_flag`, `insufficient_context`, or `integrity_failure`. Each finding returns rule ID, severity, explanation, patient fact, exact source records, recommended action, certainty category, and override requirement.

Clinician action request:

```json
{"action":"override","actor":"Dr. Demo","reason":"Required documented rationale for this synthetic demonstration."}
```

## Integrity And Audit

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/kb/status` | Read verified KB version, digest, and source/policy counts |
| `POST` | `/api/v1/kb/verify` | Re-run schema, validity-window, and Ed25519 checks |
| `GET` | `/api/v1/audit/events` | List evaluation and action events |
| `GET` | `/api/v1/audit/verify` | Verify content hashes, signatures, and the SHA-256 chain |

KB failure disables evaluation with HTTP 503 and a fail-closed error. Audit verification reports record-level hash, link, or signature failures.

## Scenarios And Status

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/scenarios` | List repeatable demo scenarios |
| `POST` | `/api/v1/scenarios/{scenario_id}/run` | Execute a real evaluation or isolated integrity simulation |
| `GET` | `/api/v1/system/status` | Check API, database, patient store, KB, and Ollama |
| `GET` | `/health` | Lightweight service and KB readiness |

## Error Behavior

- `404`: unknown patient, evaluation, or scenario.
- `422`: Pydantic rejected malformed or extra request fields.
- `502`: selected AI adapter is unavailable or returned unusable output.
- `503`: KB is unavailable, invalid, stale, or has a bad signature. Evaluation remains blocked.

Malformed AI content that reaches evaluation is preserved as untrusted input and produces `insufficient_context`; it is never silently discarded or executed.
