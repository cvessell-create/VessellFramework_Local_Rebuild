# VessellFramework

[Run the Claim Verifier](#run-the-claim-verifier-web-app) |
[Callable specialist](docs/specialist-agent.md) |
[Review workspace](docs/ambient-workflows.md)

VessellFramework is being developed as a **full-stack SI sub-agent**. Its
implemented core is a callable, provenance-aware evidence specialist, supported
by a Python runtime, authenticated task intake, durable evidence/review history,
and separate human release and explicitly authorized execution boundaries.
The email-inspired workspace is its **human-facing control plane**, not the
primary product. Filing, flags and category colors do not change evidence,
confidence, report release or execution authority.

[VISION_AND_SCOPE.md](VISION_AND_SCOPE.md) defines the product direction and
implementation limits. SI is a product vision, not a claim of demonstrated
superintelligence, production certification or independent field efficacy.

Author: Christopher R. Vessell

Current package version: **3.12.0**, as declared in [pyproject.toml](pyproject.toml).
Versioned v3.8.1 filenames remain historical compatibility artifacts.

Civilian-authored research/software: see the
[source-preservation and model-interference caveat](docs/civilian-authorship-and-model-interference.md).
Preserve the owner's account and lawful research scope without asserting
unverified government involvement.

## Six-pillar inquiry and review boundaries

The analytical architecture combines **PARADOX, BOTTLENECK, DUAL LAYER,
XFACTOR, KNOWING FIELD and GAME THEORY**. Follow the
[fifth-pillar skill](VesselFramework_Knowing_Field_SKILL_v0.1.md),
[sixth-pillar skill](VesselFramework_Game_Theory_SKILL_v0.1.md) and
[Game Theory theory skill](Game_Theory_Theory_SKILL_v0.1.md).
Strategic models are optional: without declared actors, actions, information,
utility units and source-linked evidence, report `NOT_SUPPLIED`.
Conditional calculations do not infer motives, raise confidence or authorize action.

Every new report release requires human inquiry completion against the exact
source and preview, followed by a separate release decision. CLI analyses remain
previews; historical releases are not retroactively certified. Record validation
does not demonstrate embodied knowing or improved human outcomes. See the
[Knowing Field audit](docs/knowing-field-framework-audit.md),
[Game Theory audit](docs/game-theory-framework-audit.md) and
[scientific foundations crosswalk](docs/pillar-scientific-foundations.md).

For the complete skill, agent, executable-code, scanner, and authorized remediation map, start with [VesselFramework_Agent.md](VesselFramework_Agent.md). Historical artifacts retain their original `VesselFramework` names; the active Python namespace is `vessell`.

## Reviewer quick orientation

If you are reviewing this as an academic rough-working submission, read in this order:

1. `PROFESSOR_README.md` (purpose, contribution, current limits, and requested feedback)
2. `VesselFramework_MetaMatrix_Framework_v3.8_v3.9_Combined.md` (integrated doctrine and methods)
3. `SKILL.md` (operational analyst execution layer)
4. `VesselFramework_Forecasting_SKILL_v1.0.md` (forecasting controls and calibration form)
5. `vesselframework_reference_v1.1_provenance_firewall.py` + `tests/` (executable reference and regression checks)

For package boundaries and canonical scope, see `CANONICAL_REFERENCE.md`.

## Governing doctrine

The claim-correction case study ([docs/claim-correction-case-study.md](docs/claim-correction-case-study.md))
is a governing requirement source. Its six-step playbook has executable local
mechanisms; external integration and field validation remain separate work.
The canonical paper preserves the author's supplied text. The
[source reconciliation](docs/paper-source-reconciliation.md) distinguishes that
paper from later implementation literature and measured software outcomes.

1. **Tag at intake** — every claim enters with source, tier, kind (ICD 203 report/assumption/judgment),
   uncertainty, and observation date (`vessell.provenance.intake_claim`; `vessell.validation.require_provenance_fields`).
2. **Corroborate before operationalizing** — consequential use passes through `gate_for_use` /
   `require_gate`; verification outcomes are intaked with their sightings as corroborations
   (`vessell.verify.verify_and_record`, `analyze_planted_news_and_record`, `detect_ghost_job_and_record`).
3. **Explicit waivers** — `record_waiver` (named, dated, reasoned); the remediation orchestrator's
   named approval + change ticket is the operational equivalent.
4. **Disavow by supersession, never erasure** — `disavow` keeps the original record and links the
   correction; corrections inherit kind, uncertainty, and revalidation schedule.
5. **Propagate, then verify the update landed** — supported adapters call
   `register_dependent`; the managed case-study adapter writes and reads back
   local JSON consumers before `confirm_dependent_update`. Registry
   acknowledgment alone does not verify arbitrary external systems, and
   unregistered consumers are not automatically discovered or corrected.
6. **Re-validate on schedule** — `valid_until` + `is_stale` + `revalidate_claim`; stale corroborated
   claims fail closed for consequential use.

Step-by-step traceability lives in [docs/traceability/doctrine_code_matrix.md](docs/traceability/doctrine_code_matrix.md).

## Foundations — works this builds on

The author's paper draws on provenance, automation misuse, data cascades,
truth maintenance and ICD 203. Its references and separately identified later
implementation literature are in [docs/references.md](docs/references.md).
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

## Search Gate

The [Search Gate](VesselFramework_Search_Gate_SKILL_v0.1.md) is NEW /
PROSPECTIVE / NOT VALIDATED and subordinate to Evidence Assurance and the Harm
Gate. It requires scoped search and opened primary sources before claims.
Search summaries remain hypotheses; inaccessible content stays unverified.
The offline checker evaluates supplied records, not source truth. Follow
[`.github/copilot-instructions.md`](.github/copilot-instructions.md), including
licence checks, attribution and search records before third-party imports.

## Quick start

### Run the Claim Verifier web app

From a checkout with Python **3.13+**:

```powershell
python -m vessell.app
```

This starts the Claim Verifier at <http://127.0.0.1:8765/> and opens your browser.
It is the real `vessell/verify.py` doctrine behind a web UI, not a mock:

- **Verify a claim** — enter a claim plus its source sightings; get the
  tier-weighted, independence-discounted verdict (VERIFIED → CONTRADICTED)
  with the full audit trail.
- **Planted-news spread** — hunt synchronized bursts, text-clone armies,
  single-origin laundering, and orphaned circulation
  (AUTHENTIC → LIKELY_PLANTED).
- **Ghost-job filter** — paste job-posting sightings; get the ghost verdict
  with its signal details.

Each tab includes an illustrative example, not a verified current event or
employer finding. Submitted tiers, timestamps and official-record flags remain
supplied assertions; URLs are not fetched or authenticated. Results do not
complete human review or release a report. The same engine is also a JSON API
(`POST /api/verify`, `/api/planted-news`, `/api/ghost-job`) — see
`vessell/app/server.py` for the contract.

### Drive it programmatically

Standard-library transport: `launch()` starts a loopback HTTP server in a
background thread within your process and shuts it down on context exit.

```python
from vessell.app.client import launch

with launch() as client:  # app runs in-process on an ephemeral port
    report = client.verify(
        claim="Illustrative event reported",
        sightings=[
            {"source_name": "Illustrative supplied record", "tier": "SOURCE-ESTABLISHED",
             "is_official_record": True},
        ],
    )
    print(report["verdict"])  # Classification of supplied assertions only.
    print(report["source_access"])  # NOT_PERFORMED
```

Against a running server (`python -m vessell.app`), use
`VerifierClient("http://127.0.0.1:8765")` instead — same three methods.
Raw HTTP works too: `POST` JSON to `/api/verify`, `/api/planted-news`,
or `/api/ghost-job`. Sightings and postings are plain dicts in the shape
documented in `vessell/app/server.py`; bad input returns HTTP 400 with an
`error` message, never a traceback.

### Developer setup

The optional FastAPI JSON-input UI remains available separately:
For the local browser verifier, run `python -m pip install -e ".[verifier]"`
then `vessell-verify-ui`. See [claim-verifier usage and limits](docs/claim-verifier.md).
It analyzes supplied records; it does not fetch sources or release reports.

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

1. `python -m vessell.app` — supplied-record claim/spread/job analysis in your browser.
2. `python -m pytest tests/ -q` — regression suite covering evidence, provenance, review boundaries, integrations and synthetic benchmarks. Use current runner output for counts.
3. `python vesselframework_case_runner.py example_case.json` — structured case intake and preview.
4. `python VesselFramework_SingleFile_EvilTwin_v0.2.py selftest` — identity/recognition provenance gate.
5. `python -m pytest tests/test_weights.py tests/test_weighter.py -q` — evidence-weighting checks.
6. `python -m pytest tests/test_verify.py -q` — claim, spread and ghost-pattern checks with supplied records.

Engineering signals: typed Python, mypy + ruff gates, JSON schemas for machine-readable contracts, SHA-256 integrity manifest (`python verify_manifest.py`), CI on Python 3.13, Apache-2.0 licensed.

Missing Harm Gate answers remain UNKNOWN and require review. A completed intake
gate is not execution permission. Synthetic convergence tests establish behavior
on supplied provenance graphs, not empirical cross-domain accuracy. Preview
snapshots compare outputs after normalizing random claim IDs, not released
reports or byte-identical raw files.

## Services, research and supporting tools

These references retain the boundaries and usage details for the supporting
services; a source link is not evidence of a deployed external integration.

- [Specialist callable contract](docs/specialist-agent.md) and
  [ambient deployment and review](docs/ambient-workflows.md).
- [GitHub control panel](docs/github-control-panel.md) and
  [read-only Display Mode](dashboard/README.md).
- [Approved offline artifact capture](docs/static-artifact-capture.md);
  capture and report release require separate human decisions.
- [Claim lifecycle](docs/claim-lifecycle.md),
  [operational case studies](docs/operational-case-studies.md) and
  [isolated replay lab](docs/replay-lab.md).
- [Evaluation methods](docs/evaluation-methods.md) and
  [free method courses](docs/free-method-courses.md); comparative field efficacy
  remains unverified, and software tests do not validate the whole theory.
- [Tool integrations](docs/tool-integrations.md),
  [memory store](docs/memory-store.md) and
  [organizational research charter](docs/organizational-psychology-research-charter.md).
- [Game development adaptation](GAME_DEVELOPMENT_SKILL.md) and
  [separate paused game integration](docs/game-integration.md).
- [Owner perspective interpretation](docs/owner-fourth-person-perspective.md),
  [Scientific Evidence skill](VesselFramework_Scientific_Evidence_SKILL_v0.1.md)
  and [prospective blockchain roadmap](docs/blockchain-agent-economy-roadmap.md).
  Hashing alone earns no crypto; payments, anchors and miners are not implemented.
- [Read-only R GitHub observatory](docs/github-metadata-observatory.md) and
  [Python metadata interface](docs/python-metadata-observatory.md).
- [Private R statistics workflow](.github/skills/r-inferential-workflow/SKILL.md);
  coursework and workbooks belong outside the public repository.
- [SQL quick reference](SQL_QUICK_REFERENCE.md) and point-in-time
  [SQLite catalog](data/sql_reference.sqlite).
- [Prompt steering audit](docs/prompt-steering-and-reasoning-audit.md) and
  [owner-provided handoff](data/prompt_session_handoff.json). These cover supplied
  visible records, not hidden reasoning or inaccessible account history.
- [Posture Agent skill](VesselFramework_Posture_Agent_SKILL_v0.1.md);
  keyword verdicts are not arbitrary claim verification or action clearance.
- [State electronic-transactions reference](docs/washington-rcw-19.74.md) and
  [trade-secret notice](docs/trade-secrets-notice.md); informational references
  do not amend the Apache license or create automatic legal protection.

## Keeping repository artifacts synchronized

After reviewing and staging intended source changes, run
`python scripts/sync_repository_artifacts.py --apply`, then
`python verify_manifest.py` and the regression checks. The refresh copies the
canonical skill into its tracked packaged mirror and hashes tracked source
files, excluding the manifest itself. Stage the refreshed manifest and mirror
before committing. Historical runtime-status metadata is retained; refreshed
hashes establish byte consistency, not research validity or historical truth.
Do not purge authored research, historical evidence or private application data
to repair a mirror or hash. Generated build directories are not source.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright 2026 Christopher R. Vessell.

See [SECURITY.md](SECURITY.md) for supported versions and private vulnerability
reporting guidance.
