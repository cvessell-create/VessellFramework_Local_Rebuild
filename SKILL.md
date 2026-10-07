# Organizational Psychology Research Skill

## Status and scope

This repository is being re-oriented toward organizational psychology and
psychologically healthy workplaces. This skill defines a proposed research
workflow; it is not an approved study protocol, ethics determination,
diagnostic tool, or validated workplace intervention.

The candidate question and unresolved design decisions are in
[the research charter](docs/organizational-psychology-research-charter.md).
The repository currently has no organizational-psychology study data, chosen
measures, analysis implementation, or empirical results.

## Literature review support

Use the offline catalog to keep reviewer-entered source and study-context
notes structured before synthesis:

```sh
vessell-research-catalog examples/organizational_psychology_evidence_catalog.json \
  --output /tmp/organizational-psychology-literature-catalog.md
```

The command validates metadata and formats a record inventory. It does not
verify the cited source or notes, judge study quality, synthesize results, or
accept participant data. Do not place identifiable or sensitive information in
catalog notes.

## Research workflow

Use:

`SCOPE → LITERATURE → CONSTRUCTS → DESIGN → ETHICS → DATA → ANALYSIS → INTERPRETATION → REPORT`

1. **Scope:** Identify a defined workforce, organizational context, decision,
   and primary research question. Keep the study feasible and relevant to
   psychologically healthy work.
2. **Literature:** Search and appraise peer-reviewed and authoritative
   evidence. Record the study population, design, measures, limitations, and
   applicability. Avoid treating a short bibliography as a systematic review.
3. **Constructs:** Define each construct before selecting instruments.
   Distinguish work-life conflict, enrichment, flexibility, boundary control,
   and perceived balance rather than using the terms interchangeably.
4. **Design:** State whether evidence can support description, association,
   temporal ordering, or causal inference. Specify sampling, power, analysis,
   missing-data handling, clustering, and planned subgroup analyses.
5. **Ethics:** Before participant recruitment or employee-data access, obtain
   guidance and required approval from the responsible institution. Minimize
   data, protect confidentiality from employer/supervisor access, and set
   access, retention, deletion, and adverse-result reporting rules.
6. **Data:** Preserve source and measurement context without exposing
   identifiable employee responses. A provenance chain records lineage; it
   does not establish measurement quality or participant truthfulness.
7. **Analysis:** Separate prespecified and exploratory work, report
   uncertainty and missingness, and retain unfavorable, null, mixed, and
   discrepant results.
8. **Interpretation:** Do not infer causality from cross-sectional associations.
   Explain alternative interpretations, generalizability limits, and the
   difference between employee wellbeing and organizational performance.
9. **Report:** Make clear what is published evidence, local observation,
   analysis, interpretation, and recommendation. Do not promise that a
   workplace practice is effective without appropriate evidence.

## Evidence and inference guardrails

- A psychologically healthy workplace framework is a literature-informed
  organizing aid, not a substitute for theory selection or measurement
  validation.
- Published guidelines can inform candidate practices; local context and
  affected workers' perspectives also matter.
- Reliability, construct validity, source lineage, replication, and causal
  identification are distinct questions.
- Software tests demonstrate conformance to code specifications, not validity
  of constructs, representativeness of samples, or efficacy of interventions.
- Unknown, missing, or withheld participant information must not be
  transformed into a favorable finding.
- This repository is not a clinical or employee diagnosis service. Individual
  mental-health decisions belong with appropriate qualified professionals.

## Legacy repository boundary

The Python package and existing examples primarily implement intelligence,
cybersecurity, verification, remediation, and game workflows. Do not use those
outputs as organizational-psychology findings or advertise the runtime as
research-ready. See [the scope map](VesselFramework_Agent.md) for retained
legacy areas and the [traceability matrix](docs/traceability/doctrine_code_matrix.md)
for what is and is not currently implemented.
