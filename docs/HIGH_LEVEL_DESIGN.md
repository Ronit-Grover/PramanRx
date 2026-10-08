# High-Level Design

## System Context

PramanRx is the independent assurance layer between recommendation-producing systems and clinical review. Systems before the boundary are connectors or recommendation sources. They may supply patient identifiers and provenance, but they do not determine the trusted patient facts, knowledge state, or verdict.

```text
Recommendation sources                  PramanRx assurance layer
----------------------------------      --------------------------------------
Local AI / external AI / fixed test     Ingestion and immutable capture
Clinician request                        Patient identity binding
Source and model metadata                Independent patient retrieval
                 |                       Separate normalizers
                 +-------------------->  Knowledge integrity gate
                                         Deterministic policy engine
                                         Verdict and evidence builder
                                         Action workflow
                                         Tamper-evident audit ledger
                                                    |
                                                    v
                                         Clinician-facing review UI
```

## Architectural Principles

1. **Independence:** the verifier does not ask the proposing model whether its own answer is safe.
2. **Order matters:** recommendation capture precedes authoritative patient retrieval.
3. **Least disclosure:** the primary demo does not send the authoritative FHIR record to the AI.
4. **Determinism:** once input is captured, the verdict is produced by versioned, deterministic logic.
5. **Fail closed:** trust-critical validation failures cannot become a normal `pass`.
6. **Evidence over assertion:** each finding links patient facts, policy, knowledge records, and versions.
7. **Immutability and auditability:** the original recommendation and significant workflow transitions are preserved.
8. **Adapter isolation:** upstream models use a narrow contract and cannot access trusted stores through the verifier.

## Major Components

### Operational Web Application

The React application provides patient search and creation, request entry, adapter selection, local generation or external ingestion, explicit trusted/untrusted labels, findings, actions, and audit inspection. It also exposes KB status, integration information, architecture, scenarios, and system status.

### Typed API

FastAPI exposes Pydantic-validated endpoints for patients, FHIR-compatible records, adapters, recommendation capture, evaluation, actions, audit verification, knowledge status, scenarios, and health status. Invalid input returns structured errors; malformed AI content is retained as an artifact and evaluated as malformed.

### Recommendation Gateway

The gateway invokes an adapter or accepts direct ingestion. It records source metadata, creates replay-resistant identifiers, hashes the raw content, and freezes the recommendation before trusted patient retrieval begins.

### Patient Context Service

The service imports Synthea CSV records into a local authoritative store and can expose a FHIR-compatible representation. For evaluation, it creates a normalized `PatientContext` containing only facts relevant to configured policies, with source references and missingness preserved.

### Knowledge Service

The service reads immutable source snapshots and a compiled, normalized artifact. At startup and before evaluation as required, it checks schema compatibility, artifact version, SHA-256 checksums, and Ed25519 signature. A failed integrity gate produces `integrity_failure`.

### Deterministic Policy Engine

The engine evaluates normalized recommendation items against patient context and the verified knowledge artifact. Initial policy families include allergy, drug-drug interaction, pregnancy, renal context, dose and frequency, duplicate therapy, unknown medication, missing context, and malformed recommendation checks.

### Decision and Evidence Service

The decision service combines findings using explicit precedence rules. It produces the verdict, structured explanations, policy and KB provenance, input hashes, timestamps, and recommended reviewer actions.

### Audit Ledger

Each event contains the previous event hash and its own canonical-content hash. The ledger records capture, retrieval, normalization, integrity checks, evaluation, action, override reason, and verification events. Hash chaining makes modification evident; it does not make the local host impossible to compromise.

## End-to-End Sequence

```text
Clinician   UI/API   AI Adapter   Capture Store   Patient Store   KB Gate   Rules   Audit
    |          |          |             |              |             |        |       |
    | request  |          |             |              |             |        |       |
    |--------->| generate |             |              |             |        |       |
    |          |--------->|             |              |             |        |       |
    |          |<---------| output      |              |             |        |       |
    |          | freeze raw output ---->|              |             |        |------>|
    |          |                        |              |             |        |       |
    |          | retrieve patient -------------------->|             |        |------>|
    |          |<--------------------------------------|             |        |       |
    |          | normalize separately  |              |             |        |       |
    |          | verify KB ----------------------------------------->|        |------>|
    |          | evaluate --------------------------------------------------->|------>|
    |          |<-------------------------------- verdict + evidence |        |       |
    | review   |                        |              |             |        |       |
    |<---------|                        |              |             |        |       |
    | action   |-------------------------------------------------------------|------>|
```

## Data Stores

| Store | Purpose | Trust notes |
|---|---|---|
| Synthea source archive | Immutable synthetic source material | Synthetic only; preserve source hashes and import metadata. |
| Patient database | Authoritative local demo patient records | Bound by patient ID; imported from Synthea or explicitly labeled fixtures. |
| Recommendation store | Raw frozen recommendation and provenance | Untrusted content; immutable after capture. |
| Compiled KB artifact | Normalized records used by policies | Signed, versioned, checksummed, schema validated. |
| Policy registry | Deterministic rule definitions and metadata | Versioned with authorship and test coverage. |
| Evaluation database | Findings, verdicts, and actions | References immutable inputs and exact versions. |
| Audit ledger | Hash-chained security and workflow events | Tamper evident, not tamper proof. |

## Deployment Model

The research deployment runs locally on a MacBook Air M2 with 8 GB RAM. The browser talks to a local FastAPI service. SQLite, patient data, compiled knowledge, and audit events remain local. Ollama is optional for genuine local generation; deterministic and direct-ingestion modes remain available without it. Runtime verification does not call cloud AI or live medical APIs.

## Failure Behavior

- Invalid KB signature, checksum, schema, or unsupported version: `integrity_failure`.
- Missing required patient context: `insufficient_context`, unless a higher-priority integrity failure exists.
- Malformed AI output: preserve raw output, create parsing findings, and do not silently infer a safe plan.
- Patient/request identifier mismatch: reject or return `integrity_failure`; never evaluate against a guessed patient.
- Unknown medication: `insufficient_context` or `caution` according to policy, never an implicit `pass`.
- Audit verification failure: surface integrity failure and preserve forensic information.
- Ollama unavailable: report adapter failure; optionally let the user select deterministic or direct ingestion explicitly.
