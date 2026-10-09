# VessellFramework

VessellFramework is being developed as a **full-stack SI sub-agent**: a reusable,
provenance-aware analytical service that coordinating agents can invoke through
defined interfaces. Its implemented core is a **callable evidence specialist**
supported by a Python analysis runtime, authenticated task APIs, durable
evidence and review records, and bounded, explicitly authorized execution paths.
The framework's doctrine and skill artifacts govern evidence assessment, case
analysis, forecasting methods and approved-remediation workflows.

The **email-inspired intelligence workspace is the human-facing control plane,
not the primary product**. It supports inspection, information triage, persistent
filing and review without replacing the underlying sub-agent architecture.
That architecture maintains distinct boundaries among agent task intake,
bounded analysis, evidence and provenance history, human review and report
release, and execution authority. Folder membership, read/unread markers, flags
and category colors organize attention; they do not establish source truth,
increase confidence or authorize report release or external action.

[VISION_AND_SCOPE.md](VISION_AND_SCOPE.md) defines the architectural direction,
implementation scope and acceptance criteria. The SI designation expresses
the product vision; it is not a claim of demonstrated superintelligence,
independent field efficacy or production certification. The workspace does
not implement Outlook integration or email delivery.

Author: Christopher R. Vessell

Civilian-authored research/software: see the
[source-preservation and model-interference caveat](docs/civilian-authorship-and-model-interference.md).
It preserves the owner's account and research scope without asserting
unverified government involvement.

## Six-pillar inquiry architecture

The framework now combines **PARADOX, BOTTLENECK, DUAL LAYER, XFACTOR and
KNOWING FIELD**, now complemented by **GAME THEORY**. Follow the
[sixth-pillar theory skill](Game_Theory_Theory_SKILL_v0.1.md),
[strategic blind-spot audit](docs/game-theory-framework-audit.md) and
[combined application skill](VesselFramework_Game_Theory_SKILL_v0.1.md).
The case pipeline and specialist contract accept optional source-linked
matrix, tree, coalition and savings models. Exact conditional calculations
do not infer motives, raise confidence or authorize action.

The pillars are applied in a reciprocal full-circle cycle: evidence and
perspective checks shape any strategic model, then its declared assumptions and
conditional outputs are challenged against all five other pillars. A model is
optional; without adequate actor/evidence inputs report NOT_SUPPLIED. See the
[cross-pillar audit](docs/game-theory-framework-audit.md) and
[source-bounded scientific crosswalk](docs/pillar-scientific-foundations.md)
for the updated research basis and its limits.

For Knowing Field, follow the
[source-grounded theory skill](Knowing_Field_Theory_SKILL_v0.1.md),
[framework blind-spot audit](docs/knowing-field-framework-audit.md) and
[combined fifth-pillar skill](VesselFramework_Knowing_Field_SKILL_v0.1.md).
The full Scharmer and Pomeroy (2024) article informs the adaptation; the
mandatory gate is an owner-selected framework policy, not a claim from the paper.

The fifth pillar records observer participation, affected parties,
four perspective accounts/gaps, dissent, blind spots and
attention/intention/agency. **Every new report release requires human inquiry
completion**, including pending legacy jobs, followed by a separate release
decision. CLI analyses remain previews. Historical releases are retained
without retroactive certification. Software verifies records and permissions,
not embodied presencing, collective consciousness or improved field efficacy.

For a source-bounded overview of the owner's documented role and a
theory-informed sub-agent interpretation, see
[The owner within the human-agent field](docs/owner-fourth-person-perspective.md).
This interpretive document does not supersede the product vision or establish
facts about the owner's private experience.

For the code-by-code game breakdown and framework architecture adaptation,
see [GAME_DEVELOPMENT_SKILL.md](GAME_DEVELOPMENT_SKILL.md). The new
[bounded analyst workflow](vessell/workflow.py) reuses the existing gates,
pipeline and correction machinery; game development itself remains paused.

Package version: v3.12.0 with six-pillar inquiry, durable ambient review,
approved static artifact capture and game-pattern workflow adaptations.
The separate Hail game continuation is distinct from this framework runtime.

Run the supplied model example without external services:

```bash
python -m vessell.game_theory examples/game-theory-case.json
```

Source snapshots and archive fingerprints are preserved in
[the sixth-pillar source register](docs/game-theory/source-register.json).

## Scientific foundations and next-stage agent economy

The [scientific foundations crosswalk](docs/pillar-scientific-foundations.md)
maps reviewed sources to models, assumptions, limits and falsifiable tests.
The [Scientific Evidence skill](VesselFramework_Scientific_Evidence_SKILL_v0.1.md)
expands the analyst, Knowing Field, forecasting and Skill Creator methods.
Digital records support specific integrity/existence claims; they do not prove
the whole theory. Comparative human-outcome studies remain prospective.

The [blockchain roadmap](docs/blockchain-agent-economy-roadmap.md) compares
paid-agent APIs/marketplaces, scored AI work, hardware/storage mining and
existence services. Recommended sequence: useful x402-paid asynchronous jobs,
separate OpenTimestamps receipts, then conditional Olas/Virtuals adapters.
**Hashing alone earns no crypto.** Wallets, payments, universal signed receipts,
anchors and miners are not implemented or started by this research update.

## Pull it into another agent

Install this repository with the `ambient` extra and use the
[specialist client and task contract](docs/specialist-agent.md).
The task API accepts bounded evidence, deduplicates a caller's replay and returns
a structured preview. A separate human reviewer releases the durable result.
Calling agents receive submission/read credentials, never reviewer authority.

## Sign in from HTML and run the repository

The [GitHub control panel](docs/github-control-panel.md) at
http://localhost:3000/github uses a GitHub App installed only on this repository.
It starts selected tasks on GitHub Actions and links to their logs/artifacts.
App credentials and installation are required; no shared master passwords or
browser-stored GitHub tokens are used. GitHub Pages remains the public read-only
entry point and links to the server-backed control panel.

## Ambient event review: full-stack local deployment

The [ambient stack](docs/ambient-workflows.md) adds a Next.js review dashboard,
authenticated FastAPI GitHub/GitLab and provider-neutral ingress, durable
SQLite analysis/approval state, verified history, restart recovery and SSE.
It releases **local analysis only**: no arbitrary execution, repository
changes or paid model calls. History is preserved by default.

After exporting distinct private admin/ingest tokens as documented:

```sh
docker compose -f compose.ambient.yml up --build
```

Open http://localhost:3000. See the [deployment and evidence boundaries](docs/ambient-workflows.md)
before enabling webhook routes or pruning data. Local adapter support does
not automatically configure live GitHub/GitLab webhook delivery.
The workspace supports numbered intelligence folders, automatic read-on-open,
manual read/unread, flags and category colors. Filing has its own optimistic
revision and audit trail; it never changes the evidence or releases a report.
Executable
workflows, source contracts, persistent study receipts and regression checks
are available; independent field efficacy is not claimed.

The [game integration](docs/game-integration.md) connects the rebuild to
[Hail to the Analyst](https://github.com/cvessell-create/hail-to-the-analyst):
autonomous FPS playback, a real Python provenance coach and the experimental
*Signal Recall* sequel. This separate paused game integration does not control
external accounts or real-world action systems.

Start with [operational case studies](docs/operational-case-studies.md):

```sh
python -m pip install .
vessell-study --spec case_studies/claim_correction/spec.json --output-dir outputs/study-001
vessell-study --verify-only --output-dir outputs/study-001/framework
```

This writes actual managed local consumer files and compares their correction
outcomes against an explicit snapshot-only baseline. Authorization, fail-closed
gates and provenance controls remain enforced. External systems are not modified.

For the complete skill, agent, executable-code, scanner, and authorized remediation map, start with [VesselFramework_Agent.md](VesselFramework_Agent.md). Historical artifacts retain their original `VesselFramework` names; the active Python namespace is `vessell`.

## Reviewer quick orientation

If you are reviewing this as an academic rough-working submission, read in this order:

1. `PROFESSOR_README.md` (purpose, contribution, current limits, and requested feedback)
2. `VesselFramework_MetaMatrix_Framework_v3.8_v3.9_Combined.md` (integrated doctrine and methods)
3. `SKILL.md` (operational analyst execution layer)
4. `VesselFramework_Forecasting_SKILL_v1.0.md` (forecasting controls and calibration form)
5. `vesselframework_reference_v1.1_provenance_firewall.py` + `tests/` (executable reference and regression checks)

For package boundaries and canonical scope, see `CANONICAL_REFERENCE.md`.
The claim lifecycle API and its limits are documented in
[docs/claim-lifecycle.md](docs/claim-lifecycle.md).
Optional decoding, cryptography, file-inspection, and OSINT integrations are
cataloged in [docs/tool-integrations.md](docs/tool-integrations.md).

## Governing doctrine

The claim-correction case study ([docs/claim-correction-case-study.md](docs/claim-correction-case-study.md))
is a governing requirement source. Its six-step playbook has executable local
mechanisms; external integration and field validation remain separate work:

The canonical paper preserves the author's supplied text. The
[source reconciliation](docs/paper-source-reconciliation.md) explains why the
LLM-expanded version was superseded, records source hashes, and separates the
paper's narrative from measured software outcomes and later extensions.

1. **Tag at intake** — every claim enters with source, tier, kind (ICD 203 report/assumption/judgment),
   uncertainty, and observation date (`vessell.provenance.intake_claim`; `vessell.validation.require_provenance_fields`).
2. **Corroborate before operationalizing** — consequential use passes through `gate_for_use` /
   `require_gate`; verification outcomes are intaked with their sightings as corroborations
   (`vessell.verify.verify_and_record`, `analyze_planted_news_and_record`, `detect_ghost_job_and_record`).
3. **Explicit waivers** — `record_waiver` (named, dated, reasoned); the remediation orchestrator's
   named approval + change ticket is the operational equivalent.
4. **Disavow by supersession, never erasure** — `disavow` keeps the original record and links the
   correction; corrections inherit kind, uncertainty, and revalidation schedule.
5. **Propagate, then verify the update landed** — supported operational-use adapters call `register_dependent`;
   the managed case-study adapter writes and reads back JSON consumers before
   calling `confirm_dependent_update`. Registry acknowledgment alone does not
   verify arbitrary external systems.
   Unregistered consumers are not automatically discovered or corrected.
6. **Re-validate on schedule** — `valid_until` + `is_stale` + `revalidate_claim`; stale corroborated
   claims fail closed for consequential use.

Step-by-step traceability lives in [docs/traceability/doctrine_code_matrix.md](docs/traceability/doctrine_code_matrix.md).

## Search Gate

[Search Gate doctrine](VesselFramework_Search_Gate_SKILL_v0.1.md) is NEW /
PROSPECTIVE / NOT VALIDATED and subordinate to Evidence Assurance and the Harm
Gate. It requires scoped search and opened primary confirmation before claims;
summaries remain hypotheses, inaccessible content stays unverified, and unknown
or incompatible licences block imports. Agents follow
[`.github/copilot-instructions.md`](.github/copilot-instructions.md).

The deterministic offline checker evaluates supplied records, not source truth:

```sh
vf-search-gate check-license CC-BY-4.0 --json
vf-search-gate check-import code GPL-2.0+ Apache-2.0 --json
vf-search-gate evaluate code/safety-check /tmp/search-records.json --json
```

`evaluate` accepts a JSON array for one exact claim, following
`vessell/schemas/search.record.schema.json`. Each record requires `query`, `tool`,
`scope`, `result_count`, `limit_hit`, `primary_source_opened`, `status` and
`what_was_not_checked`; add `primary_source` for clearance and `corrected_name`
when needed. Evidence statuses are `WORKING HYPOTHESIS`, `SOURCE-ESTABLISHED` and
`UNVERIFIED`. Exit codes: 0 cleared, 1 not cleared, 2 invalid input.
Licence classification alone does not authorize an import: first open the
applicable primary licence, check compatibility, preserve attribution and record
any owner-approved relicensing decision. Include SEARCH RECORDs for external
facts/imports in PR descriptions. No third-party material is imported by this gate.

## Foundations — works this builds on

The author's paper draws on provenance, automation misuse, data cascades,
truth maintenance and ICD 203. Its references and the separately identified
later implementation literature are in [docs/references.md](docs/references.md).
The following causal-order works inform implementation extensions; they are
not citations or historical incidents in the author's supplied paper:

- **Lamport (1978)** — the happens-before relation (*a → b*): every rule of
  the playbook is a rule about causal paths — which events may follow which,
  and what must travel the path between them.
- **Castello, Redmond & Kuper (2024)** — *Inductive diagrams for causal
  reasoning* (arXiv:2307.10484): causal relationships are *witnessed by the
  paths information follows* — happens-before as paths, mechanized in Agda.
  A later implementation analogy, not the paper's Section 4; correction records carry
  `causal_path`, dependents register *how* a claim reached them, and a
  negative finding's search history is its witnessed path.
- **Redmond, Shen, Vazou & Kuper (2022)** — *Verified causal broadcast with
  Liquid Haskell* (arXiv:2206.14767): the machine-checked guarantee that no
  message is delivered in an order violating causality. The dependents
  registry checks analogous local ordering using `CausalOrderingError`; these
  Python checks are not that paper's machine-checked guarantee.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements\dev.txt -r requirements\core.txt
```

Run the assurance gate:

```powershell
ruff check vessell tests
mypy vessell
pytest
```

Validate a case record:

```powershell
python -m vessell.cli example_case.json --schema case.schema.json
```

Run the Identity & Recognition Provenance Gate:

```powershell
python VesselFramework_SingleFile_EvilTwin_v0.2.py selftest
python VesselFramework_SingleFile_EvilTwin_v0.2.py recognition --subject "Alex Cvessell" --evidence example_recognition_evidence.json
```

Discover optional local analysis tools:

```sh
vessell-tools list
vessell-tools doctor
vessell-tools inspect exiftool ./artifact.bin
```

The recognition gate quarantines name-only matches, classifies recognition
stages, and counts independent provenance roots rather than search-result
quantity.

Use it as a library:

```python
from vessell import (
    EvidenceItem,
    EvidenceSet,
    ProvenanceRegistry,
    SourceStatus,
    WeightingEngine,
)

items = [
    EvidenceItem(source_id="cisa-kev", description="CISA KEV entry",
                 status=SourceStatus.SOURCE_ESTABLISHED),
    EvidenceItem(source_id="vendor-blog", description="Vendor write-up",
                 status=SourceStatus.WORKING_HYPOTHESIS),
]
registry = ProvenanceRegistry()
registry.register_many(items)

engine = WeightingEngine(registry)  # add CalibratedLlamaWeighter for live LLM scoring
weighted = engine.weight_set(EvidenceSet(registry, items))
for record in weighted.records:
    print(record.source_id, round(record.normalized_weight, 3))
```

The original flat launchers and doctrine files remain the compatibility layer for version 3.8.1. New executable functionality belongs in `vessell/`, machine-readable contracts belong in `schemas/`, and regression tests belong in `tests/`. Optional integrations are separated into `requirements/agent.txt`, `documents.txt`, and `research.txt`.

## Executable workflows and regression coverage

Five-minute tour (see `VessellFramework_Portfolio_Showcase_SKILL_v1.0.md` for the guided version):

1. `python -m pytest tests/ -q` — regression suite: provenance, validation, scanner adapters, malware triage, defense planning, remediation orchestration, agentic SOC, EvilTwin gate, Llama evidence weighting, planted-news verification, hostile-spread intel, ghost-job filtering, and the claim-correction doctrine reconciliation (`tests/test_doctrine_reconciliation.py`).
2. `python vesselframework_case_runner.py example_case.json` — structured case intake: provenance firewall, deception (maskirovka) checks, harm gate, analyst-ready report.
3. `python run_live_kev_case.py` — live CISA Known Exploited Vulnerabilities intake through the same pipeline.
4. `python VesselFramework_SingleFile_EvilTwin_v0.2.py selftest` — identity/recognition provenance gate.
5. `python -m pytest tests/test_weights.py tests/test_weighter.py -q` — Llama-calibrated evidence weighting with per-weight provenance.
6. `python -m pytest tests/test_verify.py -q` — planted-news corroboration checks, hostile-spread intel (burst/clone-army/laundering detection), and ghost-job filtering, each verdict shipping its audit record.

Engineering signals: typed Python, mypy + ruff gates, JSON schemas for machine-readable contracts, SHA-256 integrity manifest (`python verify_manifest.py`), CI on Python 3.13, Apache-2.0 licensed.

### Measured evaluation and remaining limits

Both case runners now share the Harm Gate assessment in `vessell/harm_gate.py`.
All seven risk/reversibility/proportionality fields must be explicit booleans
before clearance. Missing fields produce UNKNOWN exposure and review required;
invalid types fail validation. Existing partial cases intentionally require
review instead of treating omitted answers as no risk. Clearance is an intake
result, not permission to act or proof of control efficacy.

Run the reproducible external-data evaluator with an attributed CDC download
directory containing the source files and `download_manifest.json`:

```bash
python -m vessell.evaluation --data-dir /path/to/public_evaluation_data --output-dir outputs/evaluation
```

It verifies source SHA-256 values, rejects conflicting duplicate keys and malformed numeric
values, joins state ensemble incident-death forecasts to observations, and
reports exact duplicate exclusions, MAE, a prior-observation persistence comparison, 95% interval scores,
coverage, per-horizon results, and explicit exclusion counts. Paired JSON and
Markdown reports are read back and checked for exact synchronization. These
are exploratory scores of **CDC forecasts**, not proof that VessellFramework
improves forecasting. Revised archive observations do not establish the data
available at issue time. No independent external framework validation or
controlled control-efficacy study is claimed.

See [evaluation methods by framework aspect](docs/evaluation-methods.md) and
[free university/Khan Academy/YouTube method courses](docs/free-method-courses.md).

Use the [isolated replay lab](docs/replay-lab.md) to test public-data handling,
missing-intake safeguards, corrupted-source rejection and parallel consistency
without contacting real targets.

The path synchronizer verifies the post-write hash against expected content,
not merely that a hash can be read. Tests cover corrupted writes and byte-level
agreement of the packaged skill copy; this does not attest to other machines
or a private runtime that was not inspected.
## Posture Agent

The [VesselFramework Posture Agent skill](VesselFramework_Posture_Agent_SKILL_v0.1.md)
checks positioning claims for AI, SI, and human audiences. The Closer deliberately
overclaims (always labelled **do not ship**); the Advocate makes the defensible
pitch, and the Posture Corrector issues the verdict. These are theatrical
personas, not the operator's voice.

```powershell
vf-posture-agent --claim "VesselFramework predicts threats" --audience AI
vf-posture-agent --claim "VesselFramework predicts threats" --audience SI --format json
```

The offline, deterministic keyword policy returns `OVERCLAIM`, `CALIBRATED`,
`UNDERSOLD`, or `UNSUPPORTED` with an evidence status, ship line, and upgrade path.
Mixed claims use the least-established matching area; AI and SI share verdict
rules. It is NEW / PROSPECTIVE / NOT VALIDATED: it creates no evidence, does not
verify arbitrary natural-language claims, and grants no action clearance.
Check board freshness against the repository before relying on a pitch; stale
evidence requires `FRAMEWORK STATE: DEGRADED — VERSION / RUNTIME DRIFT`.
The Harm Gate and Forward-Posture remain authoritative.

## Hockey scoring-chance heat map

`vf-hockey-heatmap` projects expected goals (xG) by rink zone from public NHL
play-by-play at `api-web.nhle.com`. Install with `python -m pip install -e .`,
then run:

```sh
vf-hockey-heatmap --team STL --opponent COL --date 2026-10-03 --fetch --games 20 --observed 2026020032 --format html -o outputs/hockey/stl_col_2026-10-03.html
```

This fetches each team's last 20 completed regular-season games before the
cutoff date and adds observed maps for the supplied game ID, if available.
The example is not a claim that the game has been played or its result verified.
Only unblocked attempts are counted; shootouts and empty-net attempts are
excluded. Shot quality combines a distance-based logistic prior with zone
conversion rates; the matchup adjusts attempts by the opponent's attempts allowed.
Lineups, goalies, injuries and score effects are not modelled.

For offline use, pass play-by-play JSON files or directories instead of
`--fetch`, and a local file to `--observed`. Downloads are cached in
`--cache-dir`. Formats: HTML, terminal text, CSV and JSON. Tests use synthetic
game data only; no fabricated real-game data is included.

## R inferential statistics workflows

### GitHub metadata observatory

The [read-only R observatory](docs/github-metadata-observatory.md) downloads
paginated repository metadata, saves CSV/JSON/RDS snapshots and creates
source-linked improvement suggestions for human review. Its experimental
two-hidden-layer neural network learns CI outcome patterns only when the
chronological, commit-separated data meets explicit sample/class gates. It
compares held-out performance against logistic and historical-rate baselines.
It never rewrites code, releases framework reports or treats a model as causal
evidence. No paid model service is used.

```sh
gh auth login
Rscript r/run_github_observatory.R
Rscript r/test_github_observatory.R
```

Run from the repository root after `Rscript r/setup.R`. Outputs are kept in
ignored, independently timestamped `outputs/github-observatory/` directories.
The manual GitHub Actions workflow uploads review artifacts; daily local runs
can be configured in the Agent Host. Neither workflow enables the other, and
the existing GitHub control panel's dispatch allowlist is unchanged.

The [Python metadata interface](docs/python-metadata-observatory.md) also
records current-environment package versions, dependency compatibility,
tracked Python source metadata and optional pytest outcomes/timings. It reuses
the same R GitHub learning engine rather than claiming independent model evidence:

```sh
.venv/bin/python -m vessell.metadata_observatory --run-tests --github
```

Local environment metadata remains descriptive until a suitable labeled
history exists. Raw logs, source text and credentials are not saved in datasets.

The [R workflow skill](.github/skills/r-inferential-workflow/SKILL.md) guides
Excel import, paired and independent comparisons, categorical association,
correlation, assumption checks, effect sizes, and private RMarkdown reporting.
Run `Rscript r/setup.R`, then `Rscript r/test_statistics_environment.R`.
The Copilot setup workflow installs Pandoc for rendering; local RStudio
supplies its own Pandoc. Smoke checks use synthetic data, not student results.

Keep coursework and workbooks in a private course folder outside this public
repository. Local `private-projects/` and `Final Project/` directories are also
ignored as a safeguard. Do not publish completed assignments or use RPubs.

## Keeping repository artifacts synchronized

After reviewing and staging source changes, run
`python scripts/sync_repository_artifacts.py --apply`, then
`python verify_manifest.py` and the regression checks. The refresh copies the
canonical skill into its tracked packaged mirror and hashes tracked source
files, excluding the manifest itself. It preserves historical runtime-status
metadata; refreshed hashes establish byte consistency, not research validity.
Stage the refreshed mirror and manifest before committing.

Generated `build/` and `dist/` directories are ignored, not repository source.
Do not purge authored research, historical evidence, or application data simply
because a mirror or hash needs refreshing.

## SQL quick reference and repository usage map

See the [SQL quick reference](SQL_QUICK_REFERENCE.md) for retrieval, joins,
filtering, aggregation, window functions, data changes, schema objects, stored
procedures and SQL Server/SQLite differences. The generated
[SQLite catalog](data/sql_reference.sqlite) indexes these concepts, reusable
safe prompt patterns paired for SQL Server and SQLite, engine syntax examples,
and source-line examples of SQL used in this repository.
The catalog and handoff are point-in-time records, not a continuously updated
index or current runtime attestation. Regenerate into a new output with
`python scripts/build_sql_reference_db.py --output /path/to/new-catalog.sqlite`;
it stores no private conversation transcripts. To retain the selected audit
summaries when rebuilding, supply the original `--prompt-audit-zip` input.
Rebuilding without that input creates an empty audit-case table; do not
overwrite the historical catalog merely to refresh repository metadata.

For a bounded comparison of explicit prompt steering, visible assistant
outputs and verified outcomes—without attempting to reconstruct private
chain-of-thought—see the [prompt steering and reasoning audit](docs/prompt-steering-and-reasoning-audit.md).
The owner-provided [GitHub agent session handoff](data/prompt_session_handoff.json)
contains summarized historical goals, visible rationale summaries, and
verifiable work, with unavailable history and private reasoning explicitly
marked. Validate and render it with
`python -m vessell.agent_handoff`; then ask the GitHub coding agent to continue
the `github_agent_task` in that JSON. Review the data before publishing it.
Build/import the supplied, selected audit summaries with
`python scripts/build_sql_reference_db.py --prompt-audit-zip /path/to/Prompt_Usage_Audit.zip`,
then summarize with `python -m vessell.prompt_audit` or
`Rscript r/prompt_audit.R`. These tools do not call an LLM.
The same catalog inventories repository Markdown/RST/TXT prompt, skill, and
documentation sources by path, hash, and counts without copying their text;
the Python report shows source counts by category.

## Public Display Mode and supplemental research tools

The [approved static artifact capture](docs/static-artifact-capture.md) records
offline screenshots, deterministic checks and logs beside source in the
ambient review workflow. Captures and report releases require separate human
decisions; no model verdict or automatic execution endpoint is installed.

The separate [phone-friendly Display Mode](dashboard/README.md) is a read-only
GitHub status page, not the authenticated local ambient review console.
The inherited [memory store](docs/memory-store.md) and
[research charter](docs/organizational-psychology-research-charter.md) are
supplemental capabilities; they do not retire this project's executable
framework or replace the author's canonical claim-correction paper.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright 2026 Christopher R. Vessell.

See [SECURITY.md](SECURITY.md) for supported versions and private vulnerability
reporting guidance.
