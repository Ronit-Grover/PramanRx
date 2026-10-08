# Low-Level Design

## Purpose

This document translates the high-level architecture into concrete modules, data contracts, state transitions, and evaluation behavior. Names are logical contracts; the implementation may organize files differently while preserving these boundaries.

## Domain Objects

### RecommendationEnvelope

An immutable capture of the untrusted proposal.

```json
{
  "recommendation_id": "rec_...",
  "request_id": "req_...",
  "patient_id": "synthea-uuid",
  "adapter_id": "ollama-local",
  "model": "llama3.2:3b",
  "created_at": "2026-10-06T20:00:00Z",
  "raw_content": "...",
  "content_type": "text/plain",
  "source_metadata": {},
  "raw_sha256": "hex",
  "frozen_at": "2026-10-06T20:00:01Z"
}
```

The record is append-only. Corrections create a new recommendation and request relationship; they do not overwrite the original.

### NormalizedRecommendation

```json
{
  "recommendation_id": "rec_...",
  "parser_version": "recommendation-parser/1.0.0",
  "status": "parsed",
  "medications": [
    {
      "raw_name": "ibuprofen",
      "normalized_name": "ibuprofen",
      "rxnorm_id": "5640",
      "dose": 400,
      "dose_unit": "mg",
      "frequency": "every 8 hours",
      "route": "oral",
      "intent": "start"
    }
  ],
  "parse_errors": [],
  "unparsed_fragments": []
}
```

Partial parsing is explicit. Unparsed fragments remain visible and contribute to malformed-input findings where relevant.

### PatientContext

`PatientContext` is derived from the authoritative local patient record after recommendation capture. It is not the input shown to the AI.

```json
{
  "patient_id": "synthea-uuid",
  "record_version": "import-2020-04/row-hashes",
  "retrieved_at": "2026-10-06T20:00:02Z",
  "demographics": {"birth_date": "...", "sex": "..."},
  "allergies": [],
  "active_medications": [],
  "active_conditions": [],
  "observations": [],
  "pregnancy_status": "unknown",
  "renal_context": {"status": "unknown", "evidence": []},
  "missing_fields": ["pregnancy_status"],
  "source_references": []
}
```

Unknown is different from negative. For example, `pregnancy_status: unknown` must not be normalized to `not_pregnant`.

### KnowledgeManifest

```json
{
  "artifact_id": "pramanrx-kb",
  "artifact_version": "2026.10.0",
  "schema_version": "1.0.0",
  "built_at": "...",
  "transformation_version": "kb-compiler/1.0.0",
  "source_snapshots": [],
  "files": [{"path": "knowledge.json", "sha256": "hex"}],
  "signing_algorithm": "Ed25519",
  "key_id": "demo-kb-key-1",
  "signature": "base64"
}
```

### Finding

```json
{
  "finding_id": "find_...",
  "rule_id": "DDI.WARFARIN.NSAID.001",
  "severity": "critical",
  "category": "drug_drug_interaction",
  "explanation": "...",
  "patient_fact": {"type": "active_medication", "value": "warfarin"},
  "recommendation_fact": {"value": "ibuprofen"},
  "knowledge_source": {"name": "DDInter", "version": "snapshot", "record_id": "..."},
  "policy_version": "1.0.0",
  "evidence_reference": "kb://interactions/...",
  "recommended_action": "Review and select an appropriate alternative.",
  "certainty": "rule_match"
}
```

### Evaluation

An evaluation references immutable inputs and exact runtime versions. It contains no mutable embedded copy that can drift independently.

```json
{
  "evaluation_id": "eval_...",
  "recommendation_id": "rec_...",
  "patient_id": "synthea-uuid",
  "verdict": "critical_flag",
  "findings": [],
  "kb_version": "2026.10.0",
  "policy_set_version": "1.0.0",
  "patient_context_hash": "hex",
  "created_at": "..."
}
```

## Service Modules

### Adapter Registry

The registry exposes adapter metadata and a single generation contract:

```text
generate(request_text, disclosed_context, generation_options)
  -> raw_content, content_type, model_metadata, timing_metadata
```

Adapters receive no database handle, KB handle, policy engine, or authoritative patient object. Supported logical adapters are:

- `ollama-local`: calls the configured local Ollama model;
- `deterministic`: returns fixture-controlled content for demos and tests;
- `direct-ingestion`: accepts caller-supplied content and declared source metadata.

### Recommendation Capture Service

1. Validate request and patient identifiers syntactically.
2. Generate a cryptographically random recommendation ID and request ID where needed.
3. Canonicalize metadata without altering raw recommendation bytes.
4. Calculate SHA-256 of the raw content.
5. Persist the envelope in a transaction with an audit event.
6. Mark it frozen.
7. Return the immutable identifier.

The service rejects duplicate idempotency keys with conflicting payload hashes. A replay with the same key and same hash returns the original result.

### Patient Repository and Importer

The Synthea importer processes the full supplied CSV corpus, preserving the original synthetic patient identifier and source row references. It maps patients, encounters, conditions, medications, allergies, observations, procedures, and other supported tables into normalized local tables and a FHIR-compatible representation.

Import requirements:

- source archive checksum and import timestamp;
- row counts and rejected-row report per table;
- stable identifiers and referential integrity checks;
- explicit handling of missing, duplicate, and malformed rows;
- no conversion of absent clinical information into a negative fact;
- no claim that Synthea records are real or clinically representative.

### Recommendation Normalizer

The recommendation normalizer parses untrusted content in a resource-limited process or defensive library boundary. It uses data parsers, not code execution. It resolves medication names against the verified terminology subset and retains unknown names and unparsed text.

### Patient Normalizer

The patient normalizer reads only from the patient repository. It never trusts patient facts embedded in model output. It produces a `PatientContext`, source references, a normalization version, and a canonical hash.

### Knowledge Integrity Gate

Validation order:

1. locate the expected manifest and artifact files;
2. parse with size limits and strict schema validation;
3. require a supported schema and artifact version;
4. recalculate every declared SHA-256 checksum;
5. verify the Ed25519 signature over canonical manifest content;
6. validate internal indexes and required provenance fields;
7. publish a read-only verified knowledge handle.

No rule evaluation receives a knowledge handle if any required step fails.

### Policy Registry

Every policy declares:

- stable rule ID and semantic version;
- category, severity, and verdict contribution;
- required patient and recommendation fields;
- knowledge dependencies;
- deterministic match function;
- explanation template and recommended reviewer action;
- author, reviewer status, tests, and change rationale.

Initial policies cover:

| Family | Example behavior |
|---|---|
| Allergy | Match proposed ingredients/classes to active allergy records. |
| DDI | Compare proposed medications with active and co-proposed medications. |
| Pregnancy | Apply only when status and policy prerequisites are supported. |
| Renal | Flag configured drugs/doses when renal evidence meets policy criteria; otherwise expose missingness. |
| Dose/frequency | Compare structured dose and frequency to curated limits with population/context qualifiers. |
| Duplicate | Detect same ingredient or configured therapeutic duplication. |
| Unknown medication | Prevent silent clearance of unresolved names. |
| Missing context | Identify absent facts required by another policy. |
| Malformed input | Retain and report parse failures and contradictory fields. |
| Integrity | Fail closed on KB, identity, or audit integrity failure. |

### Verdict Reducer

Verdict precedence is deterministic:

```text
integrity_failure
    > critical_flag
    > insufficient_context
    > caution
    > pass
```

An implementation may allow critical safety findings and insufficient-context findings to coexist, but the overall verdict follows this precedence. `pass` is permitted only when the integrity gate succeeds, parsing meets the minimum contract, required patient identity is verified, and no other finding changes the verdict.

### Action Service

Allowed actions are `accept`, `reject`, and `override`. The service validates the evaluation ID and current state. Override requires a non-empty reason, actor identity, timestamp, and optional structured category. Actions append events; they do not modify the evaluation or recommendation.

### Audit Service

Events are canonical JSON records containing:

```text
event_id, event_type, occurred_at, actor, subject_ids,
payload_hash, previous_event_hash, event_hash, schema_version
```

`event_hash = SHA256(canonical_event_without_event_hash)`. Verification starts from the genesis event and recalculates each link. The verifier reports the first broken sequence, missing event, or invalid canonical hash.

## Evaluation State Machine

```text
RECEIVED
   -> FROZEN
   -> PATIENT_RETRIEVED
   -> NORMALIZED
   -> KB_VERIFIED
   -> EVALUATED
   -> AWAITING_ACTION
   -> ACCEPTED | REJECTED | OVERRIDDEN

Any trust-critical failure -> INTEGRITY_FAILURE
Generation failure         -> ADAPTER_FAILURE
Validation failure         -> REJECTED_INPUT (raw model artifact retained when available)
```

State transitions occur in transactions and generate audit events. Retrying a completed transition is idempotent.

## Persistence

The prototype uses SQLite with foreign keys enabled and migrations under version control. Core logical tables are `patients`, `fhir_resources`, `patient_facts`, `recommendations`, `evaluations`, `findings`, `actions`, `audit_events`, `kb_installations`, and `import_runs`.

Raw recommendation text and source metadata are untrusted data. UI rendering escapes content and never interprets HTML or script from the model.

## Concurrency and Consistency

- One recommendation envelope is immutable after freeze.
- An evaluation pins patient record version, KB version, parser version, and policy version.
- A patient update after retrieval does not silently alter an existing evaluation; re-evaluation creates a new evaluation.
- Database transactions cover capture plus audit and action plus audit.
- Unique constraints protect IDs and idempotency keys.

## Testing Strategy

- Unit tests for every policy and verdict precedence.
- Property and boundary tests for doses, frequency, missing values, and canonical hashing.
- Import tests for Synthea relationships, malformed rows, and row counts.
- Contract tests for FHIR-compatible and internal normalization.
- Adapter-isolation tests proving no trusted patient store is supplied.
- KB tests for bad checksum, signature, schema, version, and missing provenance.
- API tests for validation, wrong patient IDs, replay, immutability, and malformed model output.
- Audit tests for insertion, deletion, modification, reordering, and broken links.
- UI tests for trust labels, actions, required override reason, and scenario flows.
