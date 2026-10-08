# Demo Script

## Goal

Demonstrate that PramanRx is an independent assurance layer: it freezes an untrusted recommendation first, retrieves synthetic authoritative patient context afterward, validates a signed local knowledge artifact, applies deterministic policies, and records explainable results and clinician actions.

This is a software and security demonstration, not a clinical demonstration or treatment recommendation.

## Before the Demo

Confirm the System Status view shows:

- API and database available;
- Synthea import complete with 1,171 synthetic patients expected from the supplied sample archive, subject to importer verification;
- compiled KB schema, checksums, version, and Ed25519 signature valid;
- audit chain valid;
- deterministic adapter available;
- Ollama adapter availability and configured `llama3.2:3b` model status.

Do not describe a source row count as imported until the import report confirms it. Do not use real patient names or data.

## Primary Flow: Independent Verification

1. Open the main workspace and select a clearly labeled synthetic patient.
2. Show the patient identifier, but do not open or copy the authoritative record into the request.
3. Enter a clinician request asking for a medication recommendation.
4. Select the local Ollama adapter or deterministic adapter.
5. Point out the **Context disclosed to AI** panel. Confirm that the authoritative FHIR record and `PatientContext` are absent.
6. Generate the recommendation.
7. Show the raw output in the **Untrusted AI recommendation** panel.
8. Show its recommendation ID, adapter/model metadata, timestamp, and SHA-256 content hash.
9. Start verification. Explain that only now does PramanRx retrieve the authoritative patient record.
10. Show the trusted patient facts used, their source references, and any unknown or missing fields.
11. Show KB signature, checksum, schema, and version status.
12. Review the verdict and each deterministic finding: rule ID, severity, patient fact, recommendation fact, source/version, evidence reference, recommended action, and certainty.
13. Record an accept or reject action.
14. Open Audit Explorer and show the ordered capture, patient retrieval, KB verification, evaluation, and action events.
15. Run audit verification and show a valid chain.

Key statement: the model proposed; PramanRx independently checked. The model did not see the authoritative FHIR record in this primary flow.

## Scenario Launcher

Each scenario must use the normal backend path. A scenario may select a curated synthetic patient and deterministic recommendation, but it must still create a recommendation envelope, retrieve patient context, verify the KB, run policies, persist findings, and write audit events.

### Safe Medication

Expected behavior: `pass` only if integrity checks succeed, parsing is sufficient, required context is available, and no configured rule matches.

Explain that `pass` means "no configured concern found," not "clinically safe" or "approved."

### Allergy Conflict

Expected behavior: an allergy policy matches a proposed ingredient or curated class relationship. Show the allergy patient fact and knowledge evidence.

### Warfarin Plus Ibuprofen

Expected behavior: a drug-drug interaction finding based on an active medication and proposed medication. Show that the finding comes from deterministic matching, not a model-generated warning.

### Simvastatin Plus Clarithromycin

Expected behavior: a configured interaction finding with source record and policy version visible.

### Pregnancy Concern

Expected behavior: a pregnancy policy triggers only when the synthetic record and curated rule provide the required facts. If status is unknown, the system should prefer `insufficient_context` over assuming not pregnant.

### Renal Concern

Expected behavior: a renal-context policy links a configured medication or dose to supported synthetic observations/conditions. Missing or stale renal data remains visible.

### Excessive Dose or Frequency

Expected behavior: the parser extracts a structured dose/frequency and a curated threshold rule triggers. Show units and normalization; do not generalize beyond the exact policy scope.

### Duplicate Therapy

Expected behavior: a proposed item duplicates an active ingredient or configured therapeutic class.

### Missing Context

Expected behavior: `insufficient_context` with a precise statement of which required fact is unavailable. No silent default should convert unknown to negative.

### Unknown Medication

Expected behavior: the raw term remains visible and unresolved. The system must not map it speculatively or return an unqualified `pass`.

### Malformed Model Output

Expected behavior: raw malformed content is frozen, parser errors are visible, and the evaluation records why it cannot be safely interpreted. Nothing is silently discarded.

### Invalid KB Signature

Expected behavior: `integrity_failure`. Policy evaluation cannot use the invalid artifact, and the UI clearly distinguishes system integrity failure from a medication finding.

Use a controlled test artifact or simulation flag isolated from the normal KB. Restore and reverify the valid artifact after the scenario.

### Audit Tampering

Expected behavior: a controlled demo modification causes chain verification to identify the first invalid event or link. Verification must not auto-repair it.

Use only dedicated demo data. Do not modify the canonical research audit history.

### Override Reason

1. Open a flagged evaluation.
2. Choose override with an empty reason.
3. Show that the API and UI reject the action.
4. Enter a clearly labeled research-demo reason.
5. Submit and show the appended action and audit event.

Explain that an override records a human decision; it does not change the original verdict or prove safety.

## Direct Ingestion Flow

1. Select the direct-ingestion adapter.
2. Paste an externally produced recommendation and provide declared source/model metadata.
3. Freeze the input.
4. Run evaluation through the same independent retrieval, KB validation, policy, and audit flow.
5. Show that PramanRx is model-agnostic and does not require ownership of the generating model.

## KB Inspector

Show artifact version, schema version, signing key ID, verification timestamp, source snapshots, retrieval dates, transformations, licensing notes, and known limitations. Open one evidence record to connect a finding to its normalized record and original source reference.

State clearly that cryptographic integrity proves artifact consistency and signer identity, not clinical completeness or correctness.

## Closing

Summarize three properties:

1. The AI recommendation remains untrusted and immutable.
2. Patient context, knowledge, and policies are independently controlled and versioned.
3. The verdict is deterministic and explainable for the exact inputs, but the prototype is synthetic, incomplete, and not clinically validated.
