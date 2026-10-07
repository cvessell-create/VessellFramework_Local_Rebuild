# Research-to-Code Traceability Matrix (Initial)

This matrix makes the current transition status explicit. A documented
requirement is not an implemented feature. Legacy tests are not evidence of
organizational-psychology validity or workplace outcomes.

| Research requirement | Research document | Code / data artifact | Status |
|---|---|---|---|
| State a provisional, non-causal research question and open decisions | `docs/organizational-psychology-research-charter.md`; `docs/grad-school-prospectus.md` | None | Documented; advisor review needed |
| Define the target population and unit of analysis | Charter, “Open design decisions” | None | Unresolved |
| Select constructs and distinguish work-life conflict, enrichment, flexibility, boundary control, and perceived balance | Prospectus, “Candidate research question” | None | Unresolved |
| Justify population-appropriate measures and their measurement properties | Prospectus, “Proposed design and limits” | None | Unresolved |
| Specify sampling, sample-size rationale, confounders, missing-data handling, and analysis | Prospectus, “Proposed design and limits” | None | Unresolved |
| Establish privacy, consent, institutional review, access, retention, and reporting safeguards before participant work | Charter, “Human-participant and data boundary” | No participant-data handling code | Required before data collection |
| Distinguish implementation tests from construct validity and workplace effectiveness | `docs/evaluation-methods.md`; `SKILL.md` | Existing tests cover legacy software only | Documented; no organizational-psychology validation |
| Preserve source, design, population, measure, limitations, and applicability in any future evidence catalog | `docs/references.md`; charter | No research evidence schema | Proposed; requirements need review |
| Report uncertainty, null/mixed/adverse results, and limits on causal inference | Prospectus; `docs/evaluation-methods.md`; `SKILL.md` | No study analysis or reporting implementation | Documented only |
| Decide whether former cyber, intelligence, verification, and game modules are retained, archived, or replaced | `VesselFramework_Agent.md`; `CANONICAL_REFERENCE.md` | Existing modules remain unchanged | Open repository governance decision |

## Rules for future status promotion

1. Move a row from documented to implemented only when a corresponding
   research-specific contract, code path, and tests exist.
2. A passing unit or conformance test supports software behavior only.
3. Measurement validity requires appropriate evidence for the target
   population and use; repository schema validation is not psychometric
   validation.
4. Workplace effectiveness requires an appropriate study design, outcome
   evidence, and qualified review; it cannot be inferred from an executable
   workflow.
5. Do not use provenance independence as a proxy for study quality,
   replication, or causal identification.
