# PramanRx

PramanRx is a research prototype for independent, AI-agnostic assurance of AI-generated clinical recommendations.

> PramanRx independently verifies AI-generated clinical recommendations against authoritative patient context, verified knowledge, and enforceable policies before those recommendations influence care.

The AI recommendation is always treated as untrusted input. PramanRx freezes that recommendation, records its provenance, independently retrieves the correct patient's authoritative record, normalizes the two inputs separately, validates its local knowledge base, and runs deterministic safety and security policies. It then returns an explainable verdict and appends the event to a tamper-evident audit log.

PramanRx does not diagnose, prescribe, replace clinician judgment, or make an AI model trustworthy. It is not clinically validated, certified, or approved for patient care.

## Core Trust Boundary

```text
Untrusted side                          PramanRx trust boundary
------------------------------          -----------------------------------
Clinician request                       Freeze recommendation + provenance
        |                                             |
        v                                             v
AI adapter -> AI recommendation  ---->  Independent patient retrieval
                                                      |
                                                      v
                                         Separate normalization pipelines
                                                      |
                                                      v
                                         Signed/versioned KB validation
                                                      |
                                                      v
                                         Deterministic policy evaluation
                                                      |
                                                      v
                                         Verdict + evidence + audit event
```

In the primary demonstration, the local AI receives the clinician's request and only the explicitly displayed context. It does **not** receive the authoritative FHIR record. Authoritative patient retrieval occurs only after the untrusted recommendation has been frozen.

## Implemented Technology Stack

- React, TypeScript, and Vite for the operational user interface
- FastAPI and Pydantic for typed HTTP APIs and strict validation
- SQLite for prototype persistence
- Synthea CSV data for synthetic patient records only
- A FHIR-compatible patient representation plus an internal normalized `PatientContext`
- Ollama with `llama3.2:3b` for genuine local generation, with deterministic and direct-ingestion adapters
- RxNorm/RxTerms, RxClass, DDInter, openFDA label snapshots, DailyMed-derived references where curated, and project-authored policies for the local knowledge base
- Ed25519 signatures and SHA-256 hashes for knowledge integrity
- Hash-chained audit events for tamper evidence
- Pytest, frontend unit tests, and Playwright for verification

The runtime is local and deterministic after recommendation capture. It does not depend on live medical APIs or cloud AI services.

## Primary Workflow

1. A clinician selects or creates a patient and enters a clinical request or proposed plan.
2. An AI adapter generates a recommendation, or an external recommendation is ingested.
3. PramanRx freezes the recommendation as immutable untrusted input with request, adapter, model, and timestamp metadata.
4. PramanRx independently retrieves the authoritative patient record using the bound patient identifier.
5. The recommendation and patient record are normalized through separate pipelines.
6. The local knowledge base is checked for schema, version, checksum, and signature validity.
7. Deterministic policies evaluate allergies, interactions, contraindications, dose, frequency, pregnancy, renal context, duplicates, missing context, and input integrity.
8. PramanRx returns `pass`, `caution`, `critical_flag`, `insufficient_context`, or `integrity_failure`, with evidence and provenance.
9. The clinician accepts, rejects, or overrides the result. Overrides require a reason.
10. Every transition is written to a verifiable audit chain.

## Documentation

- [Directory and file guide](DIRECTORY_GUIDE.md)
- [Comprehensive developer guide](docs/PROJECT_GUIDE.md)
- [Product overview](docs/PRODUCT_OVERVIEW.md)
- [High-level design](docs/HIGH_LEVEL_DESIGN.md)
- [Low-level design](docs/LOW_LEVEL_DESIGN.md)
- [Trust model](docs/TRUST_MODEL.md)
- [Threat model](docs/THREAT_MODEL.md)
- [API contract](docs/API.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Limitations and ethics](docs/LIMITATIONS_AND_ETHICS.md)
- [Knowledge provenance](docs/KNOWLEDGE_PROVENANCE.md)

## Run Locally

Prerequisites: Python 3.12+ and Node.js 20+. Ollama is optional; the deterministic adapter runs without it.

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

The current local runtime database contains the imported synthetic corpus; runtime data and source snapshots are intentionally Git-ignored. After obtaining the documented source datasets, rebuild the signed KB and import them with:

```bash
scripts/bootstrap_backend.sh
```

Start the two local processes in separate terminals:

```bash
scripts/run_backend.sh
cd frontend && npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:4173`. FastAPI documentation is at `http://127.0.0.1:8000/docs`.

## Verification

```bash
scripts/test_backend.sh
cd frontend && npm test && npm run build && npm run test:e2e
```

The current corpus contains 1,171 imported Synthea patients plus six labeled demo patients. The local KB compiles a deliberately narrow prototype subset from checksum-verified RxTerms/RxNorm, RxClass, DDInter, and openFDA snapshots. It is Ed25519-signed, versioned, and rejected when its schema, validity window, or signature fails verification.

## Intended Demonstration Scenarios

The prototype is designed to demonstrate safe medication output, allergy conflicts, warfarin plus ibuprofen, simvastatin plus clarithromycin, pregnancy contraindications, renal concerns, excessive dose or frequency, duplicate therapy, missing context, unknown medication, malformed model output, invalid knowledge signatures, audit tampering, and documented override handling.

All patients used in the demo are synthetic. Scenario findings demonstrate software behavior and are not assertions of complete or clinically validated medical coverage.

## Project Status

The end-to-end research prototype is implemented: local recommendation generation/direct ingestion, post-freeze patient retrieval, deterministic evaluation, explainable evidence, clinician actions, signed KB verification, and hash-chained audit verification all run locally. This is still prototype software, not a claim of clinical completeness, regulatory compliance, or suitability for real patient care.
