# PramanRx Directory and File Guide

This guide explains what each project directory and important file does, whether it should be edited manually, and how the pieces work together.

## 1. Top-Level Structure

```text
PramanRx/
|-- backend/       Python API and PramanRx verification engine
|-- frontend/      React user interface
|-- data/          Patient database and verified knowledge base
|-- scripts/       Setup, import, compile, run, and test utilities
|-- docs/          Architecture and project documentation
|-- README.md      Quick-start instructions
`-- .gitignore     Files that Git should not track
```

## 2. Backend

The `backend/` directory contains the API server and the core PramanRx verification logic.

| Path | Purpose | Edit manually? |
| --- | --- | --- |
| `backend/app/` | Main application source code | Yes |
| `backend/tests/` | Automated backend tests | Yes |
| `backend/.venv/` | Installed Python environment and packages | No |
| `backend/requirements.txt` | Tested Python dependency versions | Carefully |
| `backend/__init__.py` | Marks `backend` as a Python package | Usually no |
| `backend/__pycache__/` | Generated Python bytecode cache | No |

### `backend/app/`

#### `main.py`

The backend entry point. It creates the FastAPI application, initializes the database and signed knowledge base, registers API endpoints, and connects incoming requests to the service layer.

#### `config.py`

Defines configuration for:

- SQLite database path
- Compiled knowledge-base path
- KB signature and signing-key paths
- Ollama URL and model name
- Optional external AI endpoint and token

Most settings can be overridden with environment variables.

#### `models.py`

Defines the validated request and response structures used by the API, including:

- Medication candidates
- Evaluation requests
- Generation requests
- Findings
- Verdicts
- Evaluation results
- Clinician actions
- Patient creation requests

These Pydantic models prevent malformed data from silently entering the verification engine.

#### `adapters.py`

Connects PramanRx to sources of AI output:

- `DeterministicAdapter`: returns a predictable test recommendation. It uses ibuprofen as the fallback when no supported medication appears in the prompt.
- `OllamaAdapter`: calls a local Ollama model, currently `llama3.2:3b` by default.
- `ExternalAdapter`: supports a future external AI service.

All adapter output is treated as untrusted input.

#### `service.py`

Coordinates one complete verification request:

1. Retrieves authoritative patient context from the database.
2. Parses a medication candidate from the untrusted AI response.
3. Calls the deterministic rules engine.
4. Builds the final verdict and findings.
5. Appends a signed audit record.

#### `database.py`

Owns SQLite access and database schema operations. It retrieves patients, allergies, medications, conditions, observations, and audit records.

#### `kb.py`

Loads the compiled knowledge base only after verifying its Ed25519 signature. If the signature is invalid or required files are missing, the application fails closed instead of using untrusted medical knowledge.

#### `rules.py`

Contains deterministic verification logic. It currently handles:

- Medication normalization
- Allergy conflicts
- Drug-drug interactions
- Duplicate therapy
- Pregnancy contraindications
- Renal-risk checks
- Dose-related prototype checks
- Insufficient-context findings

The rules engine does not trust the AI model to perform these checks.

#### `audit.py`

Creates a tamper-evident audit chain for evaluations and clinician actions. Each record includes hashes and a signature so later modifications can be detected.

#### `crypto.py`

Handles SHA-256 hashing and Ed25519 key generation, signing, and signature verification. It protects the compiled KB and audit records.

#### `__init__.py`

Marks `backend/app/` as an importable Python package. It normally contains little or no application logic.

### `backend/tests/`

| File | Purpose |
| --- | --- |
| `test_api.py` | Tests API workflows, evaluations, actions, and fail-closed behavior |
| `test_kb.py` | Tests KB loading, signature verification, and tamper detection |
| `test_importer.py` | Tests Synthea patient-data import behavior |
| `__init__.py` | Marks the tests directory as a Python package |

## 3. Frontend

The `frontend/` directory contains the browser interface.

| Path | Purpose | Edit manually? |
| --- | --- | --- |
| `frontend/src/` | React and TypeScript source code | Yes |
| `frontend/tests/` | Browser-level tests | Yes |
| `frontend/node_modules/` | Installed npm packages | No |
| `frontend/dist/` | Generated production build | No |

### `frontend/src/`

#### `App.tsx`

The main React application. It contains the verification workspace and the scenario, audit, knowledge-base, integration, architecture, and status views. It also manages the UI state for generation, verification, findings, and clinician actions.

#### `api.ts`

Contains frontend-to-backend HTTP calls and maps raw API responses into frontend data types.

#### `types.ts`

Defines TypeScript types for patients, findings, scenarios, audit events, severity levels, and application views.

#### `main.tsx`

The frontend entry point. It mounts the React application into `index.html`.

#### `styles.css`

Contains the interface layout, typography, colors, responsive behavior, loading states, panels, navigation, findings, and modal styles.

#### `icons.tsx`

Provides the shared icon component and supported icon names used across the interface.

#### `demoData.ts`

Contains sample frontend data for demonstrations and fallback display behavior. It is not the authoritative patient database.

#### `lib/risk.ts`

Contains small reusable helpers for comparing severity, shortening hashes, and deriving initials.

#### `lib/risk.test.ts`

Tests the helpers in `risk.ts`.

### Frontend Configuration

| File | Purpose |
| --- | --- |
| `index.html` | Base HTML document loaded by the browser |
| `package.json` | Frontend dependencies and development commands |
| `package-lock.json` | Locks exact npm dependency versions |
| `vite.config.ts` | Vite development server, build, and API proxy configuration |
| `vitest.config.ts` | Frontend unit-test configuration |
| `playwright.config.ts` | Browser end-to-end test configuration |
| `tsconfig.json` | Shared TypeScript configuration |
| `tsconfig.app.json` | TypeScript settings for browser source code |
| `tsconfig.node.json` | TypeScript settings for build/config files |
| `*.tsbuildinfo` | Generated TypeScript compilation cache; do not edit |
| `tests/app.spec.ts` | Playwright browser workflow test |

## 4. Data

```text
data/
|-- source/       Raw external knowledge sources
|-- compiled/     Application-ready signed knowledge base
`-- runtime/      Local database and private signing key
```

### `data/source/kb/`

This directory contains the raw evidence used to build the prototype KB.

| Directory or file | Purpose |
| --- | --- |
| `rxnorm/` | Normalized medication names and RxNorm concepts |
| `rxclass/` | Medication classifications and ATC classes |
| `openfda/` | Drug-label warnings, contraindications, and other label evidence |
| `ddinter/` | Drug-drug interaction source records |
| `rxterms/` | Medication terminology data |
| `SHA256SUMS.txt` | Expected source-file hashes for integrity verification |
| `SOURCE_MANIFEST.md` | Source origin, retrieval, and provenance notes |

These files are local source evidence and should not normally be edited manually.

### `data/compiled/`

| File | Purpose |
| --- | --- |
| `kb-v1.json` | Normalized knowledge artifact read by the application |
| `kb-v1.sig` | Digital signature for `kb-v1.json` |
| `manifest.json` | KB version, compilation, and source metadata |
| `pramanrx-ed25519-public.pem` | Public key used to verify KB and audit signatures |

The compiled artifacts are produced by `scripts/compile_kb.py`.

### `data/runtime/`

| File | Purpose |
| --- | --- |
| `pramanrx.sqlite3` | Synthetic patients, clinical history, and audit records |
| `pramanrx-ed25519-private.pem` | Private key used to sign KB and audit records |

Runtime files are machine-specific. The private key must never be committed to GitHub.

## 5. Scripts

| File | Purpose |
| --- | --- |
| `bootstrap_backend.sh` | Creates the Python environment and prepares the initial backend |
| `run_backend.sh` | Starts the FastAPI backend server on the configured host and port |
| `test_backend.sh` | Runs the backend test suite |
| `import_synthea.py` | Imports Synthea CSV records into SQLite |
| `compile_kb.py` | Verifies raw source hashes, compiles the KB, and signs it |
| `reset_audit.py` | Clears local audit records for a fresh demo |
| `__pycache__/` | Generated Python cache; do not edit |

## 6. Documentation

| File | Purpose |
| --- | --- |
| `docs/PROJECT_GUIDE.md` | Comprehensive setup, development, and troubleshooting handbook |
| `docs/PRODUCT_OVERVIEW.md` | Product goal, users, scope, and behavior |
| `docs/HIGH_LEVEL_DESIGN.md` | System-level architecture and trust boundaries |
| `docs/LOW_LEVEL_DESIGN.md` | Modules, classes, data flow, and implementation details |
| `docs/API.md` | API endpoints and request/response formats |
| `docs/TRUST_MODEL.md` | Trusted and untrusted components and assumptions |
| `docs/THREAT_MODEL.md` | Threats, attack paths, and mitigations |
| `docs/KNOWLEDGE_PROVENANCE.md` | Origins and integrity of knowledge sources |
| `docs/LIMITATIONS_AND_ETHICS.md` | Prototype limitations, safety, and ethical boundaries |
| `docs/DEMO_SCRIPT.md` | Suggested demonstration sequence |

## 7. Root Files

### `README.md`

The short quick-start document. It should help a developer install dependencies, start the system, and find deeper documentation.

### `.gitignore`

Prevents generated, local, large, or sensitive files from being committed. This includes virtual environments, `node_modules`, build output, caches, the runtime database, the private key, and local KB source files.

### `.DS_Store`

A macOS-generated Finder metadata file. It is unrelated to PramanRx and should not be committed or edited.

## 8. End-to-End Request Flow

```text
frontend/src/App.tsx
        |
        v
frontend/src/api.ts
        |
        v
backend/app/main.py
        |
        v
backend/app/adapters.py       Generates or receives untrusted AI output
        |
        v
backend/app/service.py        Coordinates the verification request
        |
        |-- database.py       Retrieves authoritative patient history
        |-- kb.py             Provides signature-verified knowledge
        |-- rules.py          Runs deterministic safety checks
        `-- audit.py          Records a signed audit event
        |
        v
FastAPI response
        |
        v
frontend/src/App.tsx          Displays verdict and clinician actions
```

The AI adapter receives the clinical prompt but not the authoritative patient record. Its output is frozen as untrusted input. PramanRx then independently retrieves patient history, verifies the output against its signed KB and deterministic policies, and records the result.

## 9. What Developers Normally Edit

Frequently edited:

- `backend/app/`
- `backend/tests/`
- `frontend/src/`
- `frontend/tests/`
- `docs/`
- `scripts/` when setup or data workflows change

Do not manually edit:

- `backend/.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`
- `*.tsbuildinfo`
- `.DS_Store`
- Cryptographic signature files
- The SQLite database using a text editor
- The private signing key

Generated directories can normally be deleted and recreated, but runtime data and signing keys should only be removed intentionally and with a backup or regeneration plan.
