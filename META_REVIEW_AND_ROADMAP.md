# Research Pivot Review and Roadmap

## Current identity

The proposed project direction is an organizational-psychology research
artifact focused on psychologically healthy workplaces, work-life support,
leadership, and employee stress. The candidate question is associational and
provisional. The repository does not yet contain an approved study or
organizational-psychology runtime.

The prior product was a broad evidence/provenance and operational software
framework covering intelligence analysis, cybersecurity, verification,
remediation, and experimental game integration. That code and its outputs
remain legacy material; passing tests establish software behavior against
legacy requirements, not evidence of workplace effects.

## Strengths to preserve carefully

- Research question and inference limits are stated explicitly.
- The initial bibliography includes peer-reviewed work and authoritative
  organizational guidance, with the scope of each source identified.
- Existing engineering strengths—traceability, reproducible processing,
  explicit unknowns, and clear test boundaries—may be useful if redesigned for
  the chosen research question.
- The plan does not assume that a correlational survey, workplace policy, or
  code feature establishes causality or effectiveness.

## Risks and unresolved design choices

1. The proposed population, setting, measures, and study type remain open.
2. “Work-life balance,” “stress,” and “supportive leadership” need specific,
   defensible operational definitions.
3. Participant research may introduce confidentiality, power-differential,
   consent, and institutional review obligations.
4. A broad healthy-workplace scope could exceed feasible sample sizes and
   dilute the central question.
5. Legacy cybersecurity and game materials can confuse faculty and readers
   unless clearly separated or archived.
6. Generic provenance tools can be mistaken for evidence quality; they do not
   establish reliability, construct validity, replication, or causal effect.

## Recommended sequence

1. Obtain advisor input on fit, scope, and whether an evidence review or
   participant study is appropriate.
2. Select one target population, primary predictor, primary outcome, and
   design; develop a literature review and measure-selection rationale.
3. Consult the institution's ethics office and relevant organizational
   stakeholders before recruitment or employee-data access.
4. Freeze the research protocol and analysis plan before implementing any
   domain-specific software. Do not add new dependencies or ingest real
   employee data until approved.
5. Audit the current package and decide which modules are generic,
   retainable infrastructure versus legacy domain functionality to archive or
   replace.
6. Define research-specific records, privacy controls, and tests only after
   study requirements are settled.
7. Evaluate software conformance separately from measurement properties,
   external replication, and workplace outcomes.

## Review prompts

- What population and organizational decision make the strongest feasible
  research contribution?
- Which construct should be primary, and which validated measure is suitable
  for that population?
- What design can support the intended interpretation?
- What privacy risks could arise if a supervisor learned an individual
  employee's response?
- Which results would falsify or materially qualify the expected account?
- Which parts of the previous software have genuine utility for this study,
  rather than merely sharing words such as “evidence” or “risk”?

This roadmap is a scoping aid, not an approved protocol or a claim that
Dr. Matthew J. Grawitch endorses this project.
