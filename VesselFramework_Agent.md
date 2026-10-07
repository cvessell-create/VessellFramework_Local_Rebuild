# Repository Scope Map

## Active research direction

The proposed focus is organizational psychology, psychologically healthy
workplaces, stress, work-life balance, leadership, and evidence-based
organizational decisions. Start with:

- [Research charter](docs/organizational-psychology-research-charter.md)
- [Research skill](SKILL.md)
- [Preliminary prospectus](docs/grad-school-prospectus.md)
- [Evaluation-method proposal and limits](docs/evaluation-methods.md)
- [Research-to-implementation traceability](docs/traceability/doctrine_code_matrix.md)

This is a research direction with one narrow executable support feature: an
offline human-authored literature catalog. The repository has no approved
protocol, participant data, organizational-psychology outcome analysis code,
or results.

## Existing software: legacy areas, not converted

| Existing area | Representative artifacts | Current status |
|---|---|---|
| Evidence, provenance, and case analysis | `vessell/provenance.py`, `vessell/app/pipeline.py`, `vessell/verify.py`, `vessell/workflow.py` | Legacy analytical/software functions; not employee-research constructs or findings |
| Cybersecurity and remediation | `vessell/app/`, `vessell/agentic_soc.py`, root `run_*.py`, `example_asset_inventory.json` | Legacy operational tooling; must not be relabeled as organizational psychology |
| Intelligence, forecasting, and verification skills | Root `VesselFramework_*SKILL*.md`, `Security_Control_Selection_Placement_Analyst_SKILL_v0.1.md`, `XP_Cyber_Range_*` | Historical/domain-specific skills; not active research guidance |
| Schemas, tests, fixtures, generated reports | `schemas/`, `tests/`, `outputs/`, `example_case.json` | Validate or demonstrate legacy contracts only |
| Game adaptation | `GAME_DEVELOPMENT_SKILL.md`, `docs/game-integration.md`, `vessell/game_*.py` | Separate legacy/experimental integration; not part of the proposed study |

## Research-aligned support already built

`vessell-research-catalog` uses the existing JSON Schema validation pattern to
check human-entered source records and render a deterministic review inventory.
Its schema records source type/check state, extraction basis, study context,
constructs, measures, outcomes, limitations, and applicability. It has no
quality score, automated synthesis, external-source verification, or
participant-data processing. See the
[catalog starter](examples/organizational_psychology_evidence_catalog.json).

These areas have not yet been deleted, moved, renamed, or recertified. They
remain to preserve compatibility and repository history while a deliberate
retain/archive/replace decision is made. Existing commands can still run their
original functions; their operation does not validate the proposed research.

## Boundary for future changes

Only add organizational-psychology measures or data processing after constructs,
population, design, privacy safeguards, and institutional review requirements
are specified. Any reuse of provenance, schemas, or evaluation machinery needs
domain-specific requirements and tests. Reproducibility does not establish
construct validity, causal identification, or intervention efficacy.
