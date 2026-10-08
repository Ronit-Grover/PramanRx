# Trust Model

## Trust Claim

PramanRx does not trust an AI recommendation merely because it was produced locally, includes citations, follows a schema, or sounds clinically plausible. It earns a limited assurance result by comparing the frozen proposal with independently retrieved patient facts, integrity-checked knowledge, and deterministic policies.

The assurance claim is bounded: PramanRx can show that configured checks ran over specific inputs and versions. It cannot show that every clinically important risk was represented in the data or rules.

## Trust Domains

| Domain | Classification | Rationale |
|---|---|---|
| Clinician request text | Untrusted input | May be incomplete, mistaken, or contain adversarial content. |
| AI adapter and model | Untrusted | May hallucinate, omit, manipulate, or emit malformed content. |
| Raw recommendation | Untrusted and immutable | Preserved exactly for evaluation and audit. |
| Adapter-declared provenance | Unverified metadata until validated | Useful for traceability but not proof of clinical correctness. |
| Patient repository | Authoritative for the demo | Local source of synthetic patient facts after successful import and identity binding. |
| Patient normalizer | Trusted computing base | Must preserve meaning, source, and missingness. |
| Compiled knowledge artifact | Trusted only after verification | Requires schema, version, checksum, signature, and provenance validation. |
| Deterministic policy engine | Trusted computing base | Versioned code and policies with tests and review. |
| Frontend | Presentation boundary | Must label trust states and safely render untrusted content. |
| Audit ledger | Tamper evident | Detects changes under stated assumptions; not immutable against total host compromise. |

## Critical Ordering Invariant

The recommendation must be frozen before authoritative patient retrieval for that evaluation.

This ordering prevents an adapter from receiving the authoritative record through the evaluation path and creates evidence that the proposal existed before trusted facts were loaded. The capture event therefore precedes the patient-retrieval event in the audit chain.

In the primary demo, the AI receives only:

- clinician-entered request text;
- adapter and generation settings;
- any additional context explicitly displayed as disclosed to the AI.

It does not receive the authoritative FHIR-compatible patient record or the internal `PatientContext`.

## Root of Trust

The prototype's roots of trust are:

- the local verification code and configured policy set;
- the trusted public key used to verify the compiled KB;
- the expected knowledge schema and supported version policy;
- the patient repository import and identity-binding process;
- the canonicalization and cryptographic libraries;
- the local operating environment.

If these roots are compromised, assurance can be invalid. Ed25519 signatures establish that the artifact was signed by the corresponding private key; they do not establish that the source data or authored rule is medically complete or correct.

## Identity Binding

Every recommendation envelope binds `patient_id`, `request_id`, `recommendation_id`, adapter provenance, and content hash. Evaluation revalidates that the requested patient exists and that all referenced IDs agree. Patient facts contained in recommendation text are never used to repair an identity mismatch.

Identifiers must be generated with sufficient entropy. Idempotency keys prevent accidental duplicate execution, while mismatched reuse is rejected and audited.

## Knowledge Trust

The knowledge lifecycle has two layers:

1. immutable source snapshots with license, retrieval date, checksums, and source identifiers;
2. a normalized compiled artifact with record-level provenance and an Ed25519-signed manifest.

The runtime accepts only a supported, intact artifact. Staleness is a policy decision: an artifact past its configured review date must be surfaced and may fail closed. A technically valid signature does not remove the need for clinical review or timely updates.

## Policy Trust

Policies are deterministic and versioned. Each policy states its required inputs, evidence source, author, tests, and verdict effect. The engine does not ask a model to choose whether a rule applies. Natural-language explanations are generated from fixed templates and structured evidence, not from the untrusted model.

## Audit Trust

The hash chain detects modification, deletion, insertion, and reordering when verification begins from a trusted chain origin and expected head. It is not a substitute for remote anchoring, access control, backups, or a write-once log. A privileged attacker who can replace the full database and all trusted checkpoints may evade local-only detection.

## Fail-Closed Conditions

PramanRx must not return `pass` when any of these conditions holds:

- KB signature, checksum, schema, or required provenance is invalid;
- patient identity cannot be bound unambiguously;
- recommendation content is unavailable or below the minimum parse contract;
- required patient context is missing for a safety-sensitive rule;
- policy or parser version is unsupported;
- audit-chain integrity required for the workflow is invalid;
- an internal error prevents complete execution of configured mandatory checks.

## Residual Trust

The clinician remains responsible for interpreting findings and deciding what to do. A reviewer must be able to see the raw AI output, patient facts used, omitted or unknown context, policy version, knowledge source, and integrity status. Override is permitted for research workflow demonstration only and requires a reason; it does not convert a flagged recommendation into a verified safe recommendation.
