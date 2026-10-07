# VessellFramework — Organizational Psychology Research Direction

This repository is being re-scoped toward organizational psychology, with a
provisional focus on psychologically healthy workplaces, workplace stress,
work-life balance, leadership, and evidence-based organizational decisions.
This is a research direction, not a claim that the current software measures
employee well-being or that any workplace intervention is effective.

## Proposed research question

In a clearly defined employee population, how are perceived supervisor support
for work-life needs and employee involvement associated with perceived stress
and work–nonwork interference?

This is a candidate correlational question, not a finalized protocol. The
population, constructs, measures, sampling plan, and analysis require advisor
review. Cross-sectional associations must not be described as causal effects.
No participant recruitment, employee-data collection, or intervention is
authorized by this repository. Obtain institutional human-subjects/ethics
guidance before any such activity.

## Start here

1. [Research charter](docs/organizational-psychology-research-charter.md):
   boundaries, proposed constructs, status, and decisions still open.
2. [Prospectus](docs/grad-school-prospectus.md): preliminary question and
   research design considerations.
3. [Research references](docs/references.md#organizational-psychology-research-direction):
   initial sources and their intended use.
4. [Evaluation methods](docs/evaluation-methods.md): separates software
   checks from evidence about workplace outcomes.

## Literature catalog slice

The first research-aligned executable feature is an offline catalog for
human-entered literature-review notes. It validates the record contract and
renders a deterministic Markdown inventory:

```sh
vessell-research-catalog examples/organizational_psychology_evidence_catalog.json
```

The schema captures citation locator, source type/check status, extraction
basis, population and setting, design, constructs, measures, outcomes,
limitations, applicability, and optional reviewer-described appraisal method.
It does not authenticate citations, rate study quality, synthesize findings,
make policy recommendations, or ingest employee/participant data. The blank
starter file is not evidence for the research question.

## Local reviewed-memory store

The `vessell-memory` command is an application-owned SQLite feature for storing
short facts with explicit scope and citations. Records start pending; users can
approve, reject, or correct them. Retrieval is scoped and includes only approved,
unexpired records with citation provenance:

```sh
vessell-memory add memory.json
vessell-memory review MEMORY_ID approve
vessell-memory retrieve "Python compatibility" --scope repository
```

This is not connected to Copilot memory and does not verify cited sources or
establish that stored statements are true. See the
[memory-store guide](docs/memory-store.md) for review and correction behavior.

## Repository status and legacy software

The existing Python package, schemas, fixtures, tests, cybersecurity workflows,
intelligence-analysis skills, and game integration have **not** been converted
into organizational-psychology research software. They remain legacy technical
artifacts until each is deliberately retained, archived, or replaced. Their
presence and passing tests do not establish psychological construct validity,
research ethics, or workplace effectiveness. See the
[scope map](VesselFramework_Agent.md) and
[canonical reference](CANONICAL_REFERENCE.md).

General software practices worth carrying forward include reproducible
processing, explicit missing-data states, source traceability, and separation
of implementation checks from empirical validation. Provenance records do not
substitute for reliable measurement, valid constructs, representative sampling,
or replication.

## Development status

There is not yet an approved research protocol, organizational-psychology
dataset, validated measure selection, participant-data handling, or outcome
analysis. The literature catalog is a documentation/review aid, not an
evidence synthesis or study runtime. Other existing package commands and
dependencies continue to serve the legacy implementation. Do not interpret
existing examples or generated outputs as organizational-psychology findings.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright 2026 Christopher R. Vessell.
