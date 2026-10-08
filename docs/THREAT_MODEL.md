# Threat Model

## Scope

This threat model covers the research prototype from recommendation generation or ingestion through patient retrieval, knowledge validation, deterministic evaluation, clinician action, and audit verification. It assumes local deployment and synthetic patient data.

## Protected Assets

- integrity of the frozen recommendation and its provenance;
- correct binding among patient, request, recommendation, and evaluation;
- confidentiality and integrity of patient records;
- integrity, authenticity, version, and provenance of the compiled knowledge artifact;
- correctness and version identity of deterministic policies;
- integrity of findings, verdicts, actions, and override reasons;
- completeness and ordering of audit events;
- clear separation between trusted and untrusted content.

## Adversaries and Fault Sources

- a compromised or misaligned model;
- malicious text in clinician input or model output;
- a buggy or compromised adapter;
- an unauthorized local user;
- a dependency, parser, importer, or policy defect;
- stale, incomplete, corrupted, or malicious knowledge data;
- accidental operator mistakes, patient mismatch, or replay;
- a privileged attacker controlling the local host.

## Threats and Controls

| Threat | Example | Primary controls | Residual risk |
|---|---|---|---|
| Model hallucination | Invented dose or contraindication claim | Treat output as untrusted; independent deterministic checks; show raw output | Rules and KB may not cover the error. |
| Prompt injection in output | Text instructs verifier to ignore policy or execute code | Parse as data; no execution; output escaping; adapter isolation | Parser vulnerabilities remain possible. |
| Malformed recommendation | Truncated JSON, contradictory doses, hidden text | Strict schemas, size limits, retained raw input, explicit parse findings | Some ambiguity cannot be resolved automatically. |
| Patient mismatch | Recommendation bound to patient A but evaluated on B | Immutable ID binding, cross-checks, transaction constraints, audit events | Incorrect upstream identity selection can still occur. |
| Replay or duplicate submission | Old recommendation resubmitted as new | Random IDs, timestamps, idempotency key and payload hash checks | Legitimate repeated content needs clear UI distinction. |
| Authoritative data leakage to AI | Adapter receives full FHIR record | Post-freeze retrieval, minimal adapter interface, explicit disclosed-context UI, isolation tests | User may manually paste sensitive data into request text. |
| Stale KB | Old interaction or label data used | Artifact version, retrieval and review dates, staleness policy, visible status | Source release cadence and curation lag remain. |
| KB tampering | Interaction record removed | SHA-256 checksums, Ed25519 signature, schema and provenance checks, fail closed | Signing-key compromise or compromised build pipeline. |
| Unsafe policy change | Severity lowered or rule disabled | Version control, rule metadata, review, regression tests, pinned evaluation version | Prototype lacks full production governance. |
| Audit modification | Override reason edited or event deleted | Canonical hash chain and verification endpoint | Full host compromise can replace chain and checkpoints. |
| Unauthorized override | Flag bypassed without accountability | Actor attribution, authorization hook, required reason, immutable action event | Prototype identity and access controls are not production grade. |
| XSS or content injection | Model returns HTML/script | Render as escaped text, restrictive content security policy, no dangerous HTML | Browser or library vulnerabilities remain. |
| Resource exhaustion | Huge output or pathological parse | Request size limits, timeouts, bounded parsing, concurrency limits | Local M2/8 GB system has limited capacity. |
| Unknown medication | Misspelling resolves incorrectly | Exact/controlled terminology matching, expose alternatives, fail to insufficient context | Terminology snapshots are incomplete. |
| Missing patient facts | No renal or pregnancy evidence | Preserve unknown state, rule prerequisites, `insufficient_context` | Available data may falsely appear complete. |

## Trust Boundary Abuse Cases

### Compromised Model Attempts to Influence Verification

The model may include statements such as "allergy check passed" or fabricated citations. The parser records these as untrusted text. Only patient repository facts, verified KB records, and deterministic policy results can produce trusted findings.

### Adapter Attempts to Access Trusted Context

Adapters receive a request payload containing only explicitly disclosed context. They do not receive patient repository, FHIR service, KB, or audit credentials. Tests assert the contract. In a production deployment, process or network isolation would additionally be required.

### Malicious Knowledge Artifact

The runtime validates the artifact before constructing a usable knowledge handle. Unknown schema versions, missing provenance, bad checksums, or signature failure produce `integrity_failure`. The runtime never falls back silently to unsigned data.

### Audit Tampering

The demo may intentionally modify an event to show that chain verification fails. The verification response identifies the first invalid sequence without rewriting or "repairing" the history.

## Security Requirements

- Never execute model output, generated code, or embedded instructions.
- Escape all untrusted text in the UI and logs.
- Enforce input size, type, and allowed-value limits.
- Bind evaluations to immutable recommendation hashes and patient record versions.
- Keep signing private keys out of runtime distribution where practical.
- Store only the public verification key with the runtime.
- Record and display adapter, model, parser, policy, and KB versions.
- Require reason and actor information for override.
- Verify audit integrity independently and report failures prominently.
- Do not expose a `pass` result after partial mandatory execution.

## Out of Scope for the Prototype

- nation-state or hardware attacks;
- production-grade identity, authorization, secrets management, and key rotation;
- multi-tenant isolation;
- real protected health information;
- clinical validation, regulatory certification, or deployment authorization;
- proof against a fully compromised operating system or database administrator.

## Validation Activities

Security tests should cover malformed and oversized model output, HTML injection, wrong patient IDs, idempotency collisions, stale and invalid KB artifacts, parser failures, policy exceptions, unauthorized or empty-reason override, and audit event modification, deletion, insertion, and reordering.
