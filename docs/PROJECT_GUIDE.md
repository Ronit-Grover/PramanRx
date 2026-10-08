# PramanRx Comprehensive Developer Guide

This document explains how to install, start, understand, change, test, and troubleshoot the PramanRx research prototype. It describes the implementation as it exists today, not an aspirational production system.

> Research prototype only. The software uses synthetic data and a deliberately limited knowledge subset. It is not clinically validated, regulatory-approved, or suitable for patient care.

## 1. What PramanRx Is

PramanRx is an independent, AI-agnostic assurance middleware layer for clinical AI recommendations:

> PramanRx independently verifies AI-generated clinical recommendations against authoritative patient context, verified knowledge, and enforceable policies before those recommendations influence care.

PramanRx is not the recommendation model. It treats every model response as untrusted input. Its defensible core is the independent verification path:

```text
Clinical request
      |
      v
AI adapter or external AI system
      |
      v
Freeze untrusted recommendation + provenance
      |
      +-----------------------------+
      |                             |
      v                             v
Normalize recommendation     Retrieve authoritative patient context
      |                       after the recommendation is frozen
      +-------------+---------------+
                    |
                    v
          Verify signed local KB
                    |
                    v
       Run deterministic policies
                    |
                    v
     Verdict + findings + evidence
                    |
                    v
       Signed, hash-chained audit
                    |
                    v
      Accept / reject / override
```

In the primary demo, the AI adapter does not receive the authoritative patient record. The UI explicitly shows the context given to the AI. After the AI output is frozen, PramanRx retrieves the patient record independently and evaluates the two separately.

## 2. Repository Location

Clone or place the repository in any convenient directory. Run all commands in this guide from the repository root unless a command explicitly changes into `frontend/`.

## 3. Technology Stack

| Area | Technology | Why it is used |
| --- | --- | --- |
| Frontend | React 19, TypeScript, Vite | Typed operational UI and fast local development |
| Backend | FastAPI, Pydantic | Typed API contracts and strict request validation |
| Persistence | SQLite | Small, local, inspectable research database |
| Patient data | Synthea CSV | Synthetic patient corpus for realistic local scale |
| Patient projection | FHIR-compatible Patient JSON | Integration-facing representation |
| AI adapters | Deterministic, Ollama, external, direct ingestion | AI-agnostic recommendation contract |
| Local model | Ollama with `llama3.2:3b` | Genuine local-model demonstration |
| Knowledge | RxTerms/RxNorm, RxClass, DDInter, openFDA snapshots | Medication normalization and curated prototype evidence |
| Integrity | Ed25519 and SHA-256 | Signed KB artifacts and tamper-evident audit records |
| Tests | Pytest, Vitest, Playwright | Backend, frontend utility, desktop, and mobile verification |

No cloud account or live medical API is required at runtime.

## 4. Directory Map

```text
PramanRx/
├── backend/
│   ├── app/                  FastAPI application and assurance engine
│   ├── tests/                Backend and API tests
│   ├── requirements.txt     Python dependency ranges
│   └── .venv/                Local Python environment; Git-ignored
├── frontend/
│   ├── src/                  React application source
│   ├── tests/                Playwright browser tests
│   ├── dist/                 Production frontend build; Git-ignored
│   ├── node_modules/         Installed JavaScript packages; Git-ignored
│   ├── package.json          Scripts and dependency declarations
│   └── package-lock.json     Reproducible dependency lock
├── data/
│   ├── compiled/             Signed, versioned prototype KB artifact
│   ├── runtime/              SQLite DB and private signing key; Git-ignored
│   └── source/kb/            Read-only local source snapshot copy; Git-ignored
├── docs/                     Architecture, trust, API, threat, ethics, and demo docs
├── scripts/                  Import, compile, run, reset, and test commands
├── README.md                 Short project entry point
└── .gitignore                Prevents secrets, datasets, builds, and caches entering Git
```

`frontend/dist` is the compiled web build. The backend has no separate build directory; Python runs the source in `backend/app` through Uvicorn.

## 5. Prerequisites

Install or confirm:

```bash
python3 --version
node --version
npm --version
ollama --version
```

Recommended minimums:

- Python 3.12+
- Node.js 20+
- Ollama only for the genuine local-model adapter

The deterministic adapter works without Ollama.

## 6. First-Time Setup

### 6.1 Create the Python environment

```bash
cd /path/to/PramanRx
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
```

### 6.2 Install frontend dependencies

```bash
cd /path/to/PramanRx/frontend
npm install
cd ..
```

### 6.3 Confirm local models

```bash
ollama list
```

The default model is `llama3.2:3b`. Start Ollama if it is not already running:

```bash
ollama serve
```

### 6.4 Rebuild the database and KB when needed

The local development checkout can include runtime data for immediate use. To recreate it from separately downloaded datasets:

```bash
scripts/bootstrap_backend.sh
```

By default, that script expects:

```text
data/source/synthea_sample_data_csv_apr2020.zip
data/source/kb/
```

Override either location without editing code:

```bash
PRAMANRX_SYNTHEA_ZIP=/absolute/path/to/synthea.zip \
PRAMANRX_KB_SOURCE=/absolute/path/to/pramanrx_kb_sources \
scripts/bootstrap_backend.sh
```

The compiler verifies every listed source checksum before it creates or signs a KB artifact. Compilation fails closed on a mismatch.

## 7. Starting The Application

Use two terminal tabs.

### Terminal 1: backend

```bash
cd /path/to/PramanRx
scripts/run_backend.sh
```

Backend URLs:

- Health: `http://127.0.0.1:8000/health`
- OpenAPI/Swagger: `http://127.0.0.1:8000/docs`
- API base: `http://127.0.0.1:8000/api/v1`

### Terminal 2: frontend

```bash
cd /path/to/PramanRx/frontend
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:4173
```

Vite proxies `/api` calls to FastAPI on port 8000.

## 8. Stopping The Application

Preferred method: press `Ctrl+C` in each terminal that is running a server.

If those terminals are unavailable, identify the process first:

```bash
lsof -nP -iTCP:4173 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Then stop only the displayed process ID:

```bash
kill <PID>
```

The `lsof`/`kill` commands are operating-system process controls. They are not part of the PramanRx source code.

## 9. End-To-End Runtime Flow

1. The clinician selects an existing synthetic patient or creates one.
2. The clinician writes a request or pastes a proposed recommendation.
3. The chosen adapter returns text. The adapter response is labeled `untrusted`.
4. The response, adapter, model, timestamp, and request ID are frozen as the evaluation input.
5. Only now does PramanRx retrieve the authoritative patient context from SQLite.
6. Medication normalization operates on the untrusted recommendation.
7. Patient normalization operates separately on the trusted source record.
8. The KB loader verifies schema version, validity window, public-key signature, and artifact digest.
9. The deterministic engine evaluates the recommendation, patient facts, and policies.
10. The service emits `pass`, `caution`, `critical_flag`, `insufficient_context`, or `integrity_failure`.
11. The evaluation request and result are stored immutably with a SHA-256 record hash and Ed25519 signature.
12. A clinician can accept, reject, acknowledge, or override. Every action requires an actor and reason and becomes another signed chain event.

## 10. Trust Boundaries

### Untrusted

- Clinician-entered free text
- Local or external AI output
- Model-generated JSON or instructions
- Adapter metadata until validated

Model-produced text is parsed as data. It is never executed as code or treated as a policy.

### Authoritative for the prototype

- Patient data retrieved independently from the local Synthea-backed store
- The compiled KB only after signature/schema/freshness verification
- Deterministic policies contained in the running code and signed artifact
- Signed audit records whose complete chain verifies

“Authoritative” here describes the prototype trust model. It does not make synthetic data clinically authoritative.

## 11. Verdict Semantics

| Verdict | Meaning |
| --- | --- |
| `pass` | No configured prototype rule matched; this is not proof of safety |
| `caution` | A non-critical configured concern needs review |
| `critical_flag` | At least one critical deterministic finding matched |
| `insufficient_context` | Required data or a normalizable medication is missing |
| `integrity_failure` | KB or audit integrity failed; processing must fail closed |

Errors such as an unknown patient ID or unavailable adapter are API/evaluation errors, not clinical verdicts.

## 12. Backend Code, File By File

### `backend/app/config.py`

Defines immutable `Settings`. It resolves project-relative defaults and environment-variable overrides for the database, KB, signature, key files, Ollama, and external adapter.

Important variables:

- `PRAMANRX_DB_PATH`
- `PRAMANRX_KB_PATH`
- `PRAMANRX_KB_SIGNATURE_PATH`
- `PRAMANRX_PUBLIC_KEY_PATH`
- `PRAMANRX_PRIVATE_KEY_PATH`
- `PRAMANRX_OLLAMA_URL`
- `PRAMANRX_OLLAMA_MODEL`
- `PRAMANRX_EXTERNAL_AI_URL`
- `PRAMANRX_EXTERNAL_AI_TOKEN`

### `backend/app/models.py`

Contains Pydantic contracts and enums:

- `Severity` and `Verdict`
- `MedicationCandidate`
- `GenerateRequest`
- `EvaluationRequest`
- `Finding`
- `EvaluationResult`
- `ActionRequest`
- `PatientCreateRequest`
- FHIR-compatible `FHIRHumanName` and `FHIRPatient`

Models use length/range constraints and `extra="forbid"` where unrecognized input must be rejected.

### `backend/app/database.py`

Owns SQLite schema and access. Tables are:

- `patients`
- `allergies`
- `conditions`
- `medications`
- `observations`
- `evaluations`
- `audit_actions`
- `metadata`

The `Database` class initializes schema, opens transactional connections, searches/creates patients, creates normalized `PatientContext`, retrieves evaluations, and returns audit events/timelines. Foreign keys are enabled. WAL mode improves local read/write behavior.

### `backend/app/crypto.py`

Wraps mature OpenSSL commands for Ed25519 instead of implementing cryptography manually:

- Generates a private/public keypair
- Protects the private key with mode `0600`
- Signs raw bytes
- Verifies signatures
- Computes SHA-256 digests
- Base64-encodes signatures stored in SQLite

The private key belongs in `data/runtime` and must never be committed.

### `backend/app/kb.py`

Loads the compiled KB and fails closed if:

- Files are missing
- The Ed25519 signature is invalid
- JSON is malformed
- Required fields or schema version are wrong
- `valid_until` has passed

`KnowledgeBase` provides medication normalization and interaction lookup over the verified artifact.

### `backend/app/adapters.py`

Defines one adapter interface and three implementations:

- `DeterministicAdapter`: repeatable output for reliable demos
- `OllamaAdapter`: calls local Ollama `/api/generate`; defaults to `llama3.2:3b`
- `ExternalAdapter`: optional HTTP adapter controlled by environment variables

All adapter results become `AdapterResponse` objects with model/source metadata. The adapter does not receive authoritative patient context in the primary flow.

Current limitation: `llama3.2:3b` can return a safety refusal rather than a medication recommendation. PramanRx correctly treats that response as untrusted and returns `insufficient_context` when no medication can be normalized. A future adapter revision should request strict JSON, set deterministic model options, validate the JSON schema, and classify refusal responses explicitly.

### `backend/app/rules.py`

Contains the deterministic assurance engine.

- `parse_candidate` extracts a supported medication, dose, units, and frequency from untrusted text.
- `_active` filters patient facts using stop dates.
- `evaluate` applies allergy, drug interaction, duplicate therapy, pregnancy, renal, missing-context, dose, frequency, and formulary policies.

Every finding includes a rule ID, category, severity, explanation, patient fact, evidence, recommended next action, certainty, and override requirement. Critical findings dominate the final verdict.

### `backend/app/audit.py`

Creates the tamper-evident audit chain:

- Canonical JSON prevents key-order differences from changing semantics.
- Each record stores `previous_hash`.
- `record_hash` is SHA-256 over the full canonical payload.
- Ed25519 signs each record hash.
- `verify_chain` recomputes payload hashes, verifies signatures, and checks every link from the genesis hash.

Changing an evaluation or action directly in SQLite causes verification to fail.

### `backend/app/service.py`

`EvaluationService` is the orchestration layer. It retrieves patient context, parses the candidate, runs rules, hashes the patient context, constructs the typed result, and appends the evaluation audit record. It keeps HTTP routing separate from domain orchestration.

### `backend/app/scenarios.py`

Defines repeatable scenario metadata for:

- safe recommendation
- allergy
- warfarin plus ibuprofen
- simvastatin plus clarithromycin
- pregnancy
- renal impairment
- dose and frequency boundaries
- missing context
- unknown medication
- malformed model output
- duplicate therapy
- invalid KB signature simulation
- audit-tampering simulation

Normal scenarios call the real evaluation service. Integrity scenarios use isolated simulations so the real KB and audit database are not corrupted.

### `backend/app/main.py`

Creates the FastAPI application. Startup initializes SQLite, ensures signing keys, verifies the KB, and constructs `EvaluationService`. If KB verification fails, evaluation routes return a fail-closed 503.

It exposes:

- health and system status
- patient search/create/context/FHIR routes
- adapter listing and generation
- evaluation creation/retrieval
- clinician actions and timeline
- audit event listing and verification
- KB status and verification
- scenario listing and execution

### Backend tests

- `backend/tests/test_api.py`: routes, trust labels, scenarios, actions, chain verification, tampering, patient creation, status, and fail-closed behavior
- `backend/tests/test_importer.py`: small Synthea ZIP import behavior
- `backend/tests/test_kb.py`: signed KB loading and tamper rejection

## 13. Data And Build Scripts

### `scripts/compile_kb.py`

1. Reads `SHA256SUMS.txt`.
2. Verifies every source file.
3. Extracts RxNorm/RxClass summaries for the nine prototype medications.
4. Locates exact DDInter rows for the two demonstrated major interactions.
5. Captures openFDA source file, record, section, and retrieval date.
6. Adds PramanRx-authored prototype policies with explicit authorship.
7. Sets schema/version/transformation/validity metadata.
8. Writes `data/compiled/kb-v1.json`.
9. Signs it with Ed25519 and writes the signature and manifest.

The artifact intentionally covers only the prototype subset. Absence of a finding is not proof of safety.

### `scripts/import_synthea.py`

Streams CSV files directly from the supplied ZIP to stay memory-conscious. It imports all 1,171 patients and related allergy, condition, medication, and latest-per-code observation records. It then adds six clearly labeled demo patients for rules not reliably present in the corpus.

Synthea CSV, FHIR-compatible output, and internal `PatientContext` remain separate concepts.

### `scripts/bootstrap_backend.sh`

Runs the KB compiler and Synthea importer using configurable source paths. Use it after cloning or when rebuilding source-derived artifacts.

### `scripts/run_backend.sh`

Finds the repository root, selects `backend/.venv/bin/python`, and starts Uvicorn on `127.0.0.1:8000`. Override host, port, or Python with environment variables.

### `scripts/test_backend.sh`

Runs the complete backend test suite through the project-local virtual environment.

### `scripts/reset_audit.py`

Deletes evaluation/action audit rows from the local runtime database for a clean demo. It does not delete patients or the KB.

## 14. Frontend Code, File By File

### `frontend/src/main.tsx`

React entry point. It mounts `<App />` into the HTML root and imports global CSS.

### `frontend/src/types.ts`

Defines frontend view models: severity, navigation views, patient, finding, audit event, and scenario. These are presentation types; raw API responses are mapped before use.

### `frontend/src/api.ts`

Central API client.

- Prefixes requests with `/api/v1`
- Converts non-2xx responses into readable errors
- Maps backend patients/findings/verdicts to frontend display types
- Exposes patients, patient creation/context, adapters, generation, evaluation, scenarios, actions, timelines, KB status, system status, and audit operations

API changes should be made here before components are changed.

### `frontend/src/lib/risk.ts`

Small pure helpers:

- ranks finding severities
- computes the highest display severity
- shortens hashes safely for UI display
- creates initials

`risk.test.ts` tests this logic with Vitest.

### `frontend/src/icons.tsx`

Contains the typed internal icon system. Components request icons by `IconName`, preventing arbitrary string names and keeping visual controls consistent without external runtime assets.

### `frontend/src/demoData.ts`

Contains display metadata and fallback scenario text used by the scenario launcher. The backend scenario endpoint still executes the real rule engine. Integrity scenarios are simulated intentionally rather than mutating real artifacts.

### `frontend/src/App.tsx`

The operational application currently lives in one main file:

- Navigation shell and mobile sidebar
- `PatientPicker` and synthetic-patient modal
- `Workspace` orchestration
- untrusted AI output panel
- trusted patient-context panel
- findings and clinician-action controls
- scenario launcher
- audit explorer
- knowledge inspector
- adapter/integration view
- architecture/trust-boundary view
- system status view

The workspace preserves the required order: recommendation first, trusted context second. `scenarioIds` and `scenarioPatients` map UI demo labels to backend fixture IDs.

As the project grows, the next frontend refactor should split views and reusable controls into separate component files. Do that only after behavior is stable and covered by tests.

### `frontend/src/styles.css`

Defines the complete restrained clinical-security visual system. It includes desktop/tablet/mobile breakpoints, visible trust-boundary colors, accessible focus states, reduced-motion behavior, stable grids, tables, modals, and navigation.

### Frontend configuration

- `vite.config.ts`: React plugin, port 4173, and `/api` proxy
- `vitest.config.ts`: restricts unit-test discovery to `src/**/*.test.ts`
- `playwright.config.ts`: desktop Chromium and mobile Chromium projects
- `tsconfig*.json`: browser and Vite TypeScript settings
- `index.html`: root document metadata and React mount element

### Browser tests

`frontend/tests/app.spec.ts` verifies:

- API connectivity
- scenario navigation
- real warfarin/ibuprofen critical finding
- trusted/untrusted labels
- audited reason-required override
- desktop and mobile viewport fit
- screenshots for inspection

## 15. Knowledge Base Contents

`data/compiled/kb-v1.json` contains:

- schema and artifact version
- compilation and expiration timestamps
- transformation version
- prototype classification and limitations
- nine normalized prototype medications
- RxNorm/RxClass source summaries
- two exact DDInter major-interaction rows
- prototype rules and exact evidence references
- source paths and SHA-256 checksums

Adjacent files:

- `kb-v1.sig`: raw Ed25519 artifact signature
- `manifest.json`: artifact digest, algorithm, and source-integrity result
- `pramanrx-ed25519-public.pem`: verification key

Original source snapshots remain immutable. DDInter is CC BY-NC-SA 4.0. openFDA explicitly warns that its results are unvalidated. These limitations must remain visible in any paper, demo, or derivative.

## 16. Patient Data Model

The database stores source-oriented patient rows and related records. `Database.patient_context()` combines them into the internal normalized context used by rules.

The FHIR endpoint currently projects the Patient demographic resource. It is FHIR-compatible, not a complete FHIR server. Medication, condition, allergy, and observation resources would need fuller FHIR mapping before production integration.

The current runtime contains:

- 1,171 imported Synthea patients
- 6 curated demo patients
- approximately 42,989 medication records
- synthetic data only

## 17. API Summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Service/KB readiness |
| GET/POST | `/api/v1/patients` | Search or create synthetic patients |
| GET | `/api/v1/patients/{id}/context` | Normalized trusted context |
| GET | `/fhir/Patient/{id}` | FHIR-compatible Patient projection |
| GET | `/api/v1/adapters` | Adapter capabilities |
| POST | `/api/v1/ai/generate` | Generate untrusted output |
| POST | `/api/v1/evaluations` | Evaluate frozen output |
| GET | `/api/v1/evaluations/{id}` | Read evaluation |
| POST | `/api/v1/evaluations/{id}/actions` | Accept/reject/override |
| GET | `/api/v1/evaluations/{id}/timeline` | Request audit timeline |
| GET | `/api/v1/audit/events` | Audit explorer data |
| GET | `/api/v1/audit/verify` | Verify entire chain |
| GET/POST | `/api/v1/kb/status`, `/api/v1/kb/verify` | Inspect/reverify KB |
| GET/POST | `/api/v1/scenarios`, `/api/v1/scenarios/{id}/run` | Repeatable demos |
| GET | `/api/v1/system/status` | API/DB/patient/KB/Ollama state |

See `docs/API.md` for request and response examples.

## 18. Testing

### Backend

```bash
cd /path/to/PramanRx
scripts/test_backend.sh
```

### Frontend unit tests

```bash
cd /path/to/PramanRx/frontend
npm test
```

### TypeScript and production build

```bash
npm run build
```

The output is written to `frontend/dist`.

### Playwright

Start backend and frontend first, then:

```bash
cd /path/to/PramanRx/frontend
npx playwright install chromium
npm run test:e2e
```

### Manual integrity checks

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/audit/verify
sqlite3 data/runtime/pramanrx.sqlite3 'PRAGMA integrity_check;'
```

## 19. Common Development Changes

### Add a medication

1. Add verified RxNorm, RxClass, and exact label snapshots to the source package.
2. Update `MEDICATIONS` in `scripts/compile_kb.py`.
3. Add evidence-bearing policies if needed.
4. Recompile and sign the KB.
5. Add rule-engine and API tests.
6. Add a scenario only if it demonstrates a meaningful behavior.

### Add a deterministic rule

1. Define its evidence/provenance in the KB compiler.
2. Implement the match in `backend/app/rules.py`.
3. Return a complete `Finding`; never return only a message.
4. Decide how the rule affects verdict precedence.
5. Test match, non-match, missing context, and boundary values.

### Add an AI product

1. Implement `AIAdapter` in `backend/app/adapters.py`.
2. Return model/source metadata and raw text.
3. Do not give the adapter trusted patient context by default.
4. Add adapter availability to `/api/v1/adapters`.
5. Add failure/isolation tests.
6. Never execute output-provided instructions.

### Add an API endpoint

1. Add or reuse a Pydantic model.
2. Keep domain logic outside route functions.
3. Update `frontend/src/api.ts` if the UI consumes it.
4. Add API tests.
5. Update `docs/API.md`.

### Change the UI

1. Preserve visible trusted/untrusted separation.
2. Preserve recommendation-before-context ordering.
3. Test desktop and mobile.
4. Run TypeScript build, Vitest, and Playwright.
5. Inspect screenshots for overlap, clipping, and misleading labels.

## 20. Ollama Behavior And The Current Refusal Issue

The local `llama3.2:3b` model can respond with “I cannot provide medical advice” to symptom-only prompts. That is a model response, not a PramanRx failure. Because no supported medication is present, the deterministic engine emits `PRX-INPUT-001` and `insufficient_context`.

For reliable demonstrations:

- Use one-click deterministic scenarios when demonstrating assurance rules.
- Use direct ingestion to paste an external AI recommendation.
- Use Ollama to demonstrate that arbitrary/refusal/malformed outputs remain untrusted.

Recommended Ollama improvement:

1. Request a strict JSON object containing medication, dose, unit, route, frequency, and rationale.
2. Use Ollama structured output/JSON format.
3. Set temperature to zero and a fixed seed.
4. Validate with Pydantic before evaluation.
5. Preserve malformed/raw output rather than silently repairing it.
6. Classify refusal separately from unknown medication.
7. Keep deterministic fallback explicit; never substitute it silently.

## 21. Troubleshooting

### Frontend says API unavailable

```bash
curl http://127.0.0.1:8000/health
```

Start `scripts/run_backend.sh` if the request fails.

### Port already in use

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:4173 -sTCP:LISTEN
```

Stop only the process you recognize or use alternate ports.

### Ollama unavailable

```bash
ollama serve
ollama list
curl http://127.0.0.1:11434/api/tags
```

The deterministic adapter remains usable.

### KB unavailable or signature invalid

Do not bypass verification. Confirm source checksums and rebuild:

```bash
scripts/bootstrap_backend.sh
```

If the public key exists but the private key is missing, restore the matching ignored private key or intentionally create a new development keypair and recompile the artifact. Never replace a trusted public key silently.

### Playwright browser missing

```bash
cd frontend
npx playwright install chromium
```

### Reset demo audit events

```bash
backend/.venv/bin/python scripts/reset_audit.py
```

## 22. GitHub Preparation

Git initialization and GitHub publication are intentionally a later step. Before the first commit:

1. Review `.gitignore`.
2. Confirm `data/runtime/pramanrx-ed25519-private.pem` is ignored.
3. Confirm `data/runtime/*.sqlite3` is ignored.
4. Confirm `data/source/kb`, `node_modules`, `.venv`, `dist`, screenshots, and test artifacts are ignored.
5. Decide whether signed compiled KB artifacts belong in the repository.
6. Re-run all tests.
7. Inspect `git status` before staging anything.
8. Add license and attribution notices, especially for DDInter.
9. Never commit real patient data, secrets, access tokens, or private keys.

## 23. Production Gaps

This prototype still needs substantial work before any real clinical environment:

- clinical validation and governance
- complete terminology and interaction coverage
- authenticated users and role-based authorization
- authorization checks for overrides
- external key management and rotation
- production FHIR/OAuth integration
- replay prevention enforced across callers
- database migrations and concurrency design
- observability, backup, retention, and incident response
- validated UI accessibility and human-factors studies
- regulatory, privacy, licensing, and institutional review
- formal threat testing and independent security review

Do not describe the current prototype as complete clinical decision support, a safety guarantee, or an approved medical product.

## 24. Recommended Next Engineering Steps

1. Improve Ollama structured output and refusal classification.
2. Split `App.tsx` into tested feature modules.
3. Add authenticated clinician identity and authorization policy.
4. Add a real FHIR adapter behind the existing patient-context interface.
5. Move policy execution to a declarative, versioned rule format where appropriate.
6. Add migration tooling and reproducible development containers.
7. Initialize Git only after secret/data review, then create the GitHub repository.
