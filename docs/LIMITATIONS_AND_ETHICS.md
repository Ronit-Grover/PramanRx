# Limitations and Ethics

## Research Use Only

PramanRx is a research prototype. It is not clinically validated, not a medical device, not approved by a regulator, and not suitable for diagnosis, prescribing, treatment, or real patient care. It must not be used to automate or authorize clinical action.

## Meaning of a Verdict

A verdict describes the outcome of configured software checks for a specific frozen recommendation, patient-record version, knowledge artifact, parser, and policy set.

- `pass` does not mean safe, correct, complete, recommended, or approved.
- `caution` and `critical_flag` do not replace clinical assessment.
- `insufficient_context` identifies missing or unresolved prerequisites; it is not a risk estimate.
- `integrity_failure` describes a broken trust assumption, not a clinical conclusion.

False negatives and false positives are expected. No finite rule set or knowledge snapshot can cover all medication risks, patient circumstances, or clinical nuance.

## Synthetic Data Only

The prototype uses Synthea-generated synthetic patient records and clearly labeled synthetic fixtures. Synthetic data does not represent real people and should not be treated as clinically representative. It can contain unrealistic combinations, incomplete longitudinal context, or distributions that differ from real populations.

The supplied Synthea archive is expected to contain 1,171 synthetic patients, but the importer must verify and report actual counts before the UI or documentation presents them as successfully loaded.

No real protected health information should be entered into the prototype. Even though the primary demo withholds the authoritative FHIR record from the model, a user could manually paste sensitive information into request text; operational safeguards and training would be required in any future deployment.

## Knowledge Limitations

The local knowledge base is a selected, transformed subset of source snapshots. It may be incomplete, stale, incorrectly transformed, or inappropriate for a specific population. RxNorm and RxTerms primarily support terminology normalization, not complete prescribing guidance. RxClass relationships require careful interpretation. openFDA labels are not a complete or authoritative substitute for current approved labeling or clinical guidance. DDInter records have their own scope, evidence, and licensing constraints.

Knowledge signatures and hashes establish artifact integrity under the signing model. They do not establish medical truth, completeness, currentness, or regulatory authority.

## Model Limitations

The default local model, `llama3.2:3b`, is a small general-purpose model. It may hallucinate, misunderstand requests, omit critical facts, or produce malformed output. Running locally improves data locality but does not make the model clinically reliable or trusted.

PramanRx also cannot fully repair an ambiguous proposal. When a medication, dose, route, or frequency cannot be resolved confidently, the correct result is to retain the original text and surface uncertainty.

## Rule and Explanation Limitations

Deterministic rules improve reproducibility, but rule authors can encode mistakes or oversimplify clinical judgment. Dose and contraindication rules often depend on indication, age, weight, route, formulation, organ function, laboratory timing, genetics, and other context that may be absent.

Explanations are evidence summaries for software findings. They are not personalized medical advice. Recommended actions should be phrased as reviewer prompts, such as "review" or "verify," rather than treatment directives.

## Bias and Fairness

Bias can enter through synthetic data generation, source knowledge coverage, terminology normalization, policy authoring, missingness patterns, and UI presentation. Performance should be evaluated across demographic and clinical subgroups before any broader claim. Unknown, intersex, nonbinary, and other demographic values must not be forced into unsupported binary assumptions.

Pregnancy and renal policies deserve particular caution: absence of evidence is not evidence of absence, and demographic attributes alone are insufficient to infer clinical status.

## Human Factors

An assurance UI can create automation bias. Prominent colors, a `pass` label, or a detailed explanation may cause users to overestimate certainty. The interface should always show:

- that the AI output is untrusted;
- what context the AI received;
- what authoritative facts PramanRx used;
- missing and unknown context;
- exact KB and policy versions;
- the limited meaning of the verdict;
- whether integrity checks succeeded.

Override should require a reason and remain visible. It should not erase findings or change the original verdict.

## Security and Privacy Limitations

The prototype does not provide production-grade authentication, authorization, key management, network isolation, monitoring, backup, disaster recovery, or multi-tenant controls. A local hash chain is tamper evident under limited assumptions; it is not immutable against a privileged attacker who can replace the database and trusted checkpoints.

The system should minimize stored free text and avoid logging secrets or unnecessary patient data. Future work with real data would require formal privacy, security, legal, and institutional review.

## Licensing and Attribution

Each knowledge source must retain its license and attribution. In particular, DDInter-derived content is subject to CC BY-NC-SA terms in the supplied research package and may restrict commercial use or redistribution. NLM/RxNorm and openFDA materials have source-specific notices and limitations that must be preserved. This repository's documentation is not legal advice; license suitability must be reviewed before distribution or commercial use.

## Ethical Demonstration Rules

- Use only synthetic records and clearly label them.
- Never present scenario output as advice for a real person.
- Do not hide malformed input, missing context, stale data, or integrity failures.
- Do not claim comprehensive interaction, allergy, dose, renal, or pregnancy coverage.
- Do not benchmark the prototype as clinically accurate without an approved study design.
- Do not use an override to make a failed recommendation appear verified.
- Publish negative results and known failure modes alongside successful scenarios.

## Requirements Before Any Clinical Evaluation

Any move beyond research would require, at minimum, clinical governance, validated data mappings, expert-reviewed and maintained policies, formal quality management, security engineering, access control, key management, usability and human-factors studies, bias analysis, prospective validation, incident response, legal and regulatory assessment, and clear organizational accountability.
