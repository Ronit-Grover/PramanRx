# Product Overview

## Problem

Clinical AI can produce recommendations that are fluent but unsafe, incomplete, malformed, based on stale knowledge, or mismatched to the patient. A model's confidence or explanation is not independent evidence. Sending more patient data to a model also increases privacy exposure without creating a reliable enforcement point.

PramanRx introduces an assurance boundary between an AI-generated recommendation and any downstream clinical action. It treats the model as an untrusted proposer and evaluates the proposal using independently retrieved patient facts, verified local knowledge, and deterministic policies.

## Product Statement

> PramanRx independently verifies AI-generated clinical recommendations against authoritative patient context, verified knowledge, and enforceable policies before those recommendations influence care.

## What PramanRx Is

PramanRx is middleware. It can sit between many AI sources and a clinician-facing workflow without depending on a particular model vendor, prompt format, or hospital system.

Its responsibilities are:

- capture and freeze the AI recommendation and its provenance;
- bind the evaluation to a patient, request, adapter, and unique identifiers;
- retrieve authoritative patient context independently of the AI;
- parse model output without executing instructions contained in it;
- verify the integrity and version of the local knowledge artifact;
- apply deterministic, testable policies;
- produce a structured verdict with explainable findings and evidence;
- record clinician actions in a tamper-evident audit chain.

## What PramanRx Is Not

PramanRx is not a diagnostic system, prescribing system, autonomous clinical agent, comprehensive drug database, electronic health record, or replacement for professional judgment. It does not prove that a recommendation is correct. A `pass` means only that no configured policy found a blocking issue in the supplied recommendation, available patient context, and active knowledge version.

## Users

- **Clinicians** inspect the original AI output, patient facts used by the verifier, findings, evidence, and final disposition.
- **Safety and informatics teams** author and review deterministic policies and knowledge transformations.
- **Security and compliance reviewers** inspect integrity state, provenance, overrides, and audit-chain verification.
- **AI integrators** connect local or external recommendation sources through a narrow adapter contract.
- **Researchers** test assurance behavior on synthetic data and explicitly scoped scenarios.

## Primary Demo Boundary

The primary demo intentionally separates what the AI sees from what PramanRx trusts.

1. The local AI receives the clinician request and only context explicitly shown in the UI.
2. The AI produces a recommendation.
3. PramanRx freezes the exact output and associated metadata.
4. Only then does PramanRx retrieve the authoritative FHIR-compatible patient record.
5. The verifier compares the proposal with authoritative patient context and the signed local knowledge base.

The authoritative FHIR record is not sent to the AI in this flow. This demonstrates independent verification rather than asking the same model to critique itself.

## Product Modes

### Local Generation

An Ollama adapter invokes a small local model, with `llama3.2:3b` as the default. The output is untrusted and may be malformed. Local generation shows that assurance is separate from model generation.

### Deterministic Generation

A deterministic adapter emits known recommendation structures for reliable demonstrations and automated tests. It does not bypass verification.

### Direct Ingestion

An external system submits an already-generated recommendation plus source metadata. This is the production-shaped integration path: PramanRx verifies the input without requiring control of the upstream model.

## Outcomes

| Verdict | Meaning |
|---|---|
| `pass` | No configured policy found a blocking concern with available context. |
| `caution` | A non-critical concern requires clinician review. |
| `critical_flag` | A configured high-severity safety rule was triggered. |
| `insufficient_context` | Required facts are missing or ambiguous, so the recommendation cannot be safely cleared. |
| `integrity_failure` | Knowledge, audit, identity, or other trust-critical integrity checks failed. |

Verdicts are not treatment instructions. Findings include a rule identifier, severity, explanation, relevant patient fact, source and version, evidence reference, recommended reviewer action, and certainty classification.

## Success Criteria for the Prototype

The prototype is successful when it can demonstrate end to end that:

- the original recommendation remains immutable;
- patient context is retrieved after capture from an authoritative local store;
- recommendation and patient normalization remain separate;
- malformed content is retained and surfaced rather than silently discarded;
- a signed and versioned knowledge artifact is required for evaluation;
- deterministic rules produce repeatable results and traceable evidence;
- clinician accept, reject, and reason-required override actions persist;
- audit-chain verification detects modification;
- all demo patients are synthetic and all limitations are visible.

## Non-Goals

- comprehensive clinical decision support;
- automated ordering or execution of treatment;
- training or fine-tuning a medical language model;
- live calls to openFDA, NLM, or other medical services at runtime;
- claiming regulatory compliance, clinical validation, or production security;
- evaluation on real protected health information.
