# Organizational Psychology Research Charter

## Direction and status

This is a supplemental research direction, not a replacement for the
repository's [callable-specialist product vision](../VISION_AND_SCOPE.md).
It focuses on organizational psychology and
psychologically healthy workplaces, workplace stress, work-life balance,
leadership, and evidence-based organizational decision making. The preliminary
research question is:

> Among employees in one defined work setting, how are perceived supervisor
> support for work-life needs and employee involvement associated with
> perceived stress and work–nonwork interference?

This is a provisional, observational question. Population, measurement,
sampling, and analysis remain undecided and require academic review. A
cross-sectional design can estimate associations, not causal effects.

## Conceptual scope

- Use psychologically healthy workplace practices as a literature-informed
  organizing frame; do not present the framework itself as validated theory.
- Treat leadership and work-life support as organizational conditions to
  measure, not as a claim that employees should individually “cope better.”
- Define the selected work–nonwork construct before choosing measures.
- Consider employee involvement only if scope and power permit it.
- Use evidence-based decision making to connect research findings, local
  organizational context, and affected stakeholders while recording
  uncertainty and contrary evidence.

## Human-participant and data boundary

No recruitment, intervention, employee-data ingestion, or collection of
identifiable/sensitive information is authorized by this repository. Obtain
institutional ethics guidance and required approvals before any human
participant work. Protect confidentiality from employer access, minimize
collected data, define access/retention/deletion rules, and plan how to report
small groups without re-identification. The responsible institution determines
the applicable review requirements.

## Evidence and inference rules

1. Distinguish published evidence, local observations, interpretation, and
   proposed hypotheses.
2. Record each source's population, design, measure, timeframe, limitations,
   and relevance to the target setting.
3. Do not equate source independence with study quality, construct validity, or
   replication.
4. Do not infer cause from cross-sectional association or equate a favorable
   organizational outcome with employee wellbeing.
5. Report null, mixed, adverse, and subgroup findings with the same care as
   favorable findings.
6. Software conformance and reproducibility are implementation evidence only;
   they are not evidence of workplace effectiveness.

## Repository migration boundary

The existing Python modules, schemas, tests, security and intelligence
workflows, and game integration remain framework software, not validated
organizational-psychology capabilities. Reuse in this supplemental research
track requires a new requirements trace,
construct-appropriate data contract, tests, and domain review. Do not silently
relabel existing security outputs, datasets, or fixtures as employee research.

The first research-aligned executable slice is an offline literature catalog:
`vessell.research_catalog`, `schemas/research-evidence-catalog.schema.json`,
and `examples/organizational_psychology_evidence_catalog.json`. It reuses the
legacy schema-validation mechanism while storing human-entered source and
appraisal notes. The tool does not verify sources, score study quality,
synthesize effects, or process participant data. Its output is software
formatting evidence only.

## Open design decisions

- Select the population, organization type, and unit of analysis.
- Decide whether this is an evidence review or a participant study.
- If a participant study, determine the primary predictor and outcome, select
  measures with evidence for the target population, and justify sample size.
- Decide on an observational, longitudinal, or intervention design only after
  feasibility and ethics review.
- Define whether/how existing software is retained, archived, or replaced.

This charter is a scope-control document, not an approved protocol, ethics
determination, or empirical conclusion.
