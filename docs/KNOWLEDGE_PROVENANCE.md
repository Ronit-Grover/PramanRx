# Knowledge Provenance

## Purpose

PramanRx relies on a local, compiled knowledge artifact so runtime evaluation is reproducible and does not depend on live medical APIs. Provenance must make every normalized record and policy finding traceable to a source snapshot, transformation, and version.

Provenance supports inspection and reproducibility. It does not prove that a source or transformation is clinically complete or correct.

## Source Package Intake

Before any supplied knowledge source is used:

1. Read `SOURCE_MANIFEST.md` in the supplied source package.
2. Verify every packaged file against `SHA256SUMS.txt`.
3. Stop the build if a file is missing, unexpected, or has a mismatched hash.
4. Record package location, verification time, verifier version, and result.
5. Copy source material into the project only as an immutable snapshot, preserving license and notice files.

The expected research package includes selected RxTerms 202610, RxNorm and RxClass snapshots, 222,383 DDInter rows as declared by the package, and selected openFDA label snapshots. These are package expectations, not runtime claims; the compiler must independently report observed files and row counts.

## Knowledge Layers

### Layer 1: Immutable Source Snapshots

Source snapshots are never modified in place. Each source entry records:

- source name and publisher;
- original file and record identifier;
- source release or snapshot version;
- retrieval date and retrieval method;
- original SHA-256 checksum;
- license, attribution, and use restrictions;
- package-manifest verification result;
- known source limitations.

### Layer 2: Normalized Records

The compiler parses source-specific formats into a common schema for terminology, ingredients, classes, interactions, label statements, and evidence references. Each output record carries its lineage.

```json
{
  "record_id": "interaction:...",
  "record_type": "drug_drug_interaction",
  "normalized_subjects": [],
  "severity": "source_or_curated_value",
  "evidence_excerpt": "bounded source-derived text or structured summary",
  "source": {
    "name": "DDInter",
    "snapshot_version": "...",
    "file": "...",
    "record_identifier": "...",
    "retrieved_at": "...",
    "sha256": "..."
  },
  "transformation": {
    "compiler_version": "kb-compiler/1.0.0",
    "mapping_rule": "...",
    "transformed_at": "..."
  }
}
```

Transformations must not invent certainty. Source text, source-coded severity, project-curated severity, and policy severity are separate fields.

### Layer 3: Curated Policies

Policies turn normalized knowledge and patient/recommendation facts into deterministic findings. Every policy records:

- stable rule ID and semantic version;
- author and review status;
- creation and update dates;
- rationale and intended scope;
- required fields and knowledge record types;
- severity and verdict effect;
- evidence template and recommended reviewer action;
- tests and expected scenarios;
- superseded policy versions.

A project-authored rule must be labeled as such. It must not be represented as a direct rule issued by openFDA, NLM, DDInter, or any other publisher.

### Layer 4: Signed Compiled Artifact

The final read-only artifact contains normalized records, indexes, policy metadata or pinned policy references, and a manifest. The manifest includes:

- artifact and schema versions;
- build timestamp and compiler version;
- source snapshot IDs and checksums;
- output file checksums and record counts;
- required runtime compatibility;
- signing algorithm and key ID;
- Ed25519 signature over canonical manifest content.

The build environment signs the artifact. The runtime should contain only the public verification key. A demo-only key is not a production key-management design.

## Source Roles and Limitations

### RxNorm and RxTerms

Use for normalized drug concepts, names, ingredients, and identifiers within the licensed snapshot. Terminology resolution does not establish that a dose is appropriate or that a medication is safe for a patient.

### RxClass

Use selected class relationships for explicitly reviewed policies such as duplication or class-level allergy matching. Class relationships have different sources and relationship types; the compiler must retain these distinctions rather than flattening them into a universal equivalence.

### DDInter

Use selected interaction records as evidence for deterministic drug-drug interaction policies. Preserve the exact source record identifier, snapshot details, and CC BY-NC-SA attribution. The stated 222,383-row count must be confirmed during build. Severity and clinical management implications require careful mapping and must not be overstated.

### openFDA Label Snapshots

Use only the selected downloaded snapshots, never a live runtime request. Preserve application/product identifiers, section origin, retrieval date, and raw snapshot checksum. openFDA data can be incomplete, reformatted, delayed, or unsuitable as a sole source of prescribing information. A label text match is evidence for review, not a complete clinical rule by itself.

### DailyMed-Derived References

If curated DailyMed references are included, preserve set IDs, version dates, section references, and retrieval metadata. Do not claim DailyMed coverage where no snapshot exists in the verified source package.

## Build Pipeline

```text
Verify source package hashes
        |
        v
Parse source-specific records with strict schemas
        |
        v
Normalize identifiers while retaining original values
        |
        v
Apply explicit, versioned transformations
        |
        v
Validate required provenance and referential integrity
        |
        v
Build deterministic indexes and record-count report
        |
        v
Generate manifest and output checksums
        |
        v
Sign canonical manifest with Ed25519
        |
        v
Independently verify artifact before installation
```

Builds from the same source bytes, compiler version, configuration, and deterministic ordering should produce the same logical records. Timestamps or signatures that prevent byte-for-byte reproducibility must be isolated and documented.

## Runtime Verification

The runtime validates:

1. strict manifest schema;
2. supported schema and artifact versions;
3. required source and transformation provenance;
4. each output file's SHA-256 checksum;
5. Ed25519 signature and expected key ID;
6. internal record/index consistency;
7. configured review or staleness status.

Any required failure produces `integrity_failure`. The runtime must not silently use an older, unsigned, partially loaded, or fallback knowledge file.

## Finding-Level Traceability

Every finding must answer:

- Which recommendation fact triggered the rule?
- Which authoritative patient fact was used, if any?
- Which rule ID and version ran?
- Which knowledge record and source snapshot supported the match?
- Which transformation produced that record?
- What was the active artifact version and integrity state?
- What uncertainty or missing context remains?

The evidence UI may show a concise excerpt, but it must retain a stable reference to the complete local source record and attribution.

## Updates and Deprecation

Knowledge updates create a new artifact version; they never mutate an installed version used by an existing evaluation. Before promotion, a new artifact requires hash verification, schema validation, provenance validation, regression tests, scenario comparison, review of changed or removed records, and a fresh signature.

Existing evaluations remain pinned to their original versions. Re-evaluation with a newer artifact creates a new evaluation linked to the prior one.

## Licensing and Distribution

The compiler and inspector must preserve source notices. DDInter-derived content in the supplied package is subject to CC BY-NC-SA attribution and use restrictions. NLM/RxNorm and openFDA materials carry their own terms and disclaimers. Before publishing compiled artifacts, review whether transformation, redistribution, and intended use comply with every source license. This document does not provide legal advice.

## Provenance Gaps

If a record lacks a required source identifier, checksum, retrieval date, transformation version, or policy ownership field, it is not eligible for the trusted compiled artifact. It may be retained in a quarantine report for investigation, but the runtime cannot treat it as verified knowledge.
