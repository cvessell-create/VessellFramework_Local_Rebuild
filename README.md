# VessellFramework

## Current research and development

Start with the [review packet](PROFESSOR_README.md) and
[original paper](docs/claim-correction-case-study.md).
This repository and the [game](https://github.com/cvessell-create/hail-to-the-analyst)
are public for review.

Current work: callable evidence analysis, human review, the corrected
[Vessell formula](docs/vessell-formula.md) and separate SI
generation/telemetry tests. The game campaign is human-controlled;
local AI/SI services are development tools, not campaign features.
See [game boundaries](docs/game-integration.md).

Use the current test run for validation; dated results are retained in the
[formula research report](docs/vessell-formula-research-report.md).
Superseded setup notes, demonstration skills and reports are in the
[archive](archive/README.md), not the active setup path.

[Protection guide](docs/personal-family-protection-guide.md) |
[Product specification](docs/personal-family-agent-spec.md) |
[Professor review packet](PROFESSOR_README.md) |
[Existing Claim Verifier](#run-the-claim-verifier-web-app) |
[Callable specialist](docs/specialist-agent.md) |
[GitHub agent integration](docs/github-agent-integration.md) |
[Review workspace](docs/ambient-workflows.md)

## Product focus: personal and family protection

VessellFramework is being developed as a **personal and family privacy,
safety and rights agent**. It will organize evidence, research options and
prepare responses for human review. Evidence analysis is its supporting engine.

The [protection guide](docs/personal-family-protection-guide.md) is a working
draft covering legal requirements, platform procedures and privacy commitments.
It offers no guarantee of a remedy.

**Current work: product design and GitHub agent integration.** The
[product specification](docs/personal-family-agent-spec.md) describes proposed
consent, safe communications, private-data lifecycle and protective workflows.
Family isolation, consent-based sharing and rights-response workflows are
unfinished. Keep private family cases out of public GitHub and research queries.
Current service credentials are single-owner.

The **full-stack SI sub-agent** combines an evidence-analysis API, source
history and a human review workspace. Intake, analysis, report release and
execution have separate permissions. SI is the development goal.
See [VISION_AND_SCOPE.md](VISION_AND_SCOPE.md).

### What exists and what remains proposed

| Surface | Role in the proposed product | Present boundary |
| --- | --- | --- |
| [Callable evidence specialist](docs/specialist-agent.md) | Supporting analysis engine | Existing task/preview/review contract; not a family case or consent service |
| [Local verifier](docs/claim-verifier.md) | Bounded assessment of supplied material | Analysis-only; it does not authenticate supplied sources or release a report |
| [GitHub agent integration](docs/github-agent-integration.md) | Public discovery, reference search and owner-authorized Actions analysis | Non-sensitive unreleased previews only; remote deployment/adoption not verified |
| [Human review workspace](docs/ambient-workflows.md) | Supporting control plane | Existing single-owner review, not demonstrated family isolation |
| [Protection guide](docs/personal-family-protection-guide.md) | Rights/process reference and response preparation | Owner-review draft; source access is not a legal eligibility finding |
| [Personal/family specification](docs/personal-family-agent-spec.md) | Proposed safety, permissions and lifecycle contract | No new runtime, account integration, monitoring or filing capability |

Author: Christopher R. Vessell

Current package version: **3.12.0**, as declared in [pyproject.toml](pyproject.toml).
Versioned v3.8.1 filenames remain historical compatibility artifacts.

Preserve civilian authorship and lawful research scope under the
[source-preservation caveat](docs/civilian-authorship-and-model-interference.md);
contested government-interference attribution is not verified.

## Six-pillar inquiry and review boundaries

The six pillars are PARADOX, BOTTLENECK, DUAL LAYER, XFACTOR, KNOWING FIELD
and GAME THEORY. Strategic models declare actors, actions, information,
utility units and evidence; missing inputs remain NOT_SUPPLIED.
Every report needs human Knowing Field completion against its sources and
preview, followed by a release decision. Filing metadata has its own history
and cannot change confidence or permissions. Test fixtures stay separate from
the original paper's incidents.

The [Search Gate](VesselFramework_Search_Gate_SKILL_v0.1.md) requires source
checks before claims; its effectiveness remains unvalidated.
Follow [agent instructions](.github/copilot-instructions.md).
See the bounded [state-law references](docs/state-law-protections.md) and
[platform-accountability index](docs/platform-accountability-laws.md) and
[trade-secret notice](docs/trade-secrets-notice.md); these do not create rights
or change the [Apache license](LICENSE).

See [KNOWING FIELD](VesselFramework_Knowing_Field_SKILL_v0.1.md),
[GAME THEORY](VesselFramework_Game_Theory_SKILL_v0.1.md), and the
[owner-paper reconciliation](docs/paper-source-reconciliation.md).
The [verifier guide](docs/claim-verifier.md) distinguishes both local interfaces.
After reviewing and staging source changes, use
[artifact synchronization](scripts/sync_repository_artifacts.py) to refresh
tracked file checksums.

For the complete skill, agent, executable-code, scanner, and authorized remediation map, start with [VesselFramework_Agent.md](VesselFramework_Agent.md). Historical artifacts retain their original `VesselFramework` names; the active Python namespace is `vessell`.

## Reviewer quick orientation

If you are reviewing this as an academic rough-working submission, read in this order:

1. [PROFESSOR_README.md](PROFESSOR_README.md): research purpose, contribution,
   current limits and requested critique.
2. [Vision and scope](VISION_AND_SCOPE.md), [protection guide](docs/personal-family-protection-guide.md)
   and [product specification](docs/personal-family-agent-spec.md): proposed application.
3. [Original paper](docs/claim-correction-case-study.md) and
   [source reconciliation](docs/paper-source-reconciliation.md): preserved authorship.
4. [Combined framework](VesselFramework_MetaMatrix_Framework_v3.8_v3.9_Combined.md),
   [analyst skill](SKILL.md) and [forecasting skill](VesselFramework_Forecasting_SKILL_v1.0.md):
   methods, with current six-pillar additions linked above.
5. [Specialist contract](docs/specialist-agent.md) and [tests](tests/):
   selected executable controls and their development tests.

For package boundaries and historical submission scope, see
[CANONICAL_REFERENCE.md](CANONICAL_REFERENCE.md).

## Governing doctrine

The [claim-correction case study](docs/claim-correction-case-study.md) remains
the governing author source for the correction playbook, not a substitute for
the current product scope or permission to retain private data indefinitely.
The personal/family application does not rewrite the paper or independently
verify its historical incidents. Its six-step playbook maps to selected
executable controls:

1. **Tag at intake** — every claim enters with source, tier, kind (ICD 203 report/assumption/judgment),
   uncertainty, and observation date (`vessell.provenance.intake_claim`; `vessell.validation.require_provenance_fields`).
2. **Corroborate before operationalizing** — consequential use passes through `gate_for_use` /
   `require_gate`; verification outcomes are intaked with their sightings as corroborations
   (`vessell.verify.verify_and_record`, `analyze_planted_news_and_record`, `detect_ghost_job_and_record`).
3. **Explicit waivers** — `record_waiver` (named, dated, reasoned); the remediation orchestrator's
   named approval + change ticket is the operational equivalent.
4. **Disavow by supersession, never erasure** — `disavow` keeps the original record and links the
   correction; corrections inherit kind, uncertainty, and revalidation schedule.
   This analytical lineage rule is not an indefinite private-data retention
   policy. Future deletion, backups and legal-hold behavior require separate design.
5. **Propagate, then verify the update landed** — `register_dependent` on every operational use;
   `confirm_dependent_update` / `pending_corrections` close the loop.
6. **Re-validate on schedule** — `valid_until` + `is_stale` + `revalidate_claim`; stale corroborated
   claims fail closed for consequential use.

Step-by-step traceability lives in [docs/traceability/doctrine_code_matrix.md](docs/traceability/doctrine_code_matrix.md).

## Foundations — works this builds on

The owner source remains distinct from later supporting literature. The
correction playbook draws on three published results. Full
citations are in [docs/references.md](docs/references.md):

- **Lamport (1978)** — the happens-before relation (*a → b*): every rule of
  the playbook is a rule about causal paths — which events may follow which,
  and what must travel the path between them.
- **Castello, Redmond & Kuper (2024)** — *Inductive diagrams for causal
  reasoning* (arXiv:2307.10484): causal relationships are *witnessed by the
  paths information follows* — happens-before as paths, mechanized in Agda.
  The spine of the case study's Section 4; correction records carry
  `causal_path`, dependents register *how* a claim reached them, and a
  negative finding's search history is its witnessed path.
- **Redmond, Shen, Vazou & Kuper (2022)** — *Verified causal broadcast with
  Liquid Haskell* (arXiv:2206.14767): the machine-checked guarantee that no
  message is delivered in an order violating causality. The dependents
  registry checks analogous local ordering with `CausalOrderingError`;
  these Python checks are not that paper's machine-checked guarantee.

## Quick start

### Run the Claim Verifier web app

Three ways to run it:

1. **In your browser** (nothing to install):
   [Browser verifier](docs/index.html) — `vessell/verify.py` executes via
   Pyodide. Runtime and module loading use the network; source URLs supplied
   for analysis are not authenticated. The loader repair was checked locally
   and pushed; deployment has not been checked.
   GitHub Pages is intended to publish **master /docs** using branch deployment;
   the dashboard workflow only tests dashboard code and does not replace that site.

2. **In the cloud** (no local setup):
   open this repo in [GitHub Codespaces](https://github.com/features/codespaces)
   (Code → Codespaces → Create codespace), then `python -m vessell.app` —
   the app port forwards automatically.

3. **As an installed package** (Python 3.13+):
   ```powershell
   pip install git+https://github.com/cvessell-create/VessellFramework_Local_Rebuild.git
   python -m vessell.app
   ```

Prefer a local clone? No install step, just Python 3.13+:

```powershell
python -m vessell.app
```

This starts the Claim Verifier at http://127.0.0.1:8765/ and opens your browser.
The web UI runs `vessell/verify.py`:

- **Verify a claim** — enter a claim plus its source sightings; get the
  tier-weighted, independence-discounted verdict (VERIFIED → CONTRADICTED)
  with the full audit trail.
- **Planted-news spread** — hunt synchronized bursts, text-clone armies,
  single-origin laundering, and orphaned circulation
  (AUTHENTIC → LIKELY_PLANTED).
- **Ghost-job filter** — paste job-posting sightings; get the ghost verdict
  with its signal details.

Each tab ships an illustrative fixture, not a verified event or job.
Tiers and official-record flags remain supplied assertions. Results are
analysis-only, not report release or authorization. The same engine is a JSON API
(`POST /api/verify`, `/api/planted-news`, `/api/ghost-job`) — see
`vessell/app/server.py` for the contract.

### Drive it programmatically

Standard-library HTTP client/server in the same process, on a background thread:

```python
from vessell.app.client import launch

with launch() as client:  # app runs in-process on an ephemeral port
    report = client.verify(
        claim="M4.2 earthquake near Wauna, WA",
        sightings=[
            {"source_name": "USGS", "tier": "SOURCE-ESTABLISHED",
             "is_official_record": True},
            {"source_name": "KOMO", "tier": "SOURCE-ESTABLISHED"},
        ],
    )
    print(report["verdict"])  # VERIFIED

    spread = client.planted_news(claim="...", sightings=[...])
    ghosts = client.ghost_job(postings=[...])
```

Against a running server (`python -m vessell.app`), use
`VerifierClient("http://127.0.0.1:8765")` instead — same three methods.
Raw HTTP works too: `POST` JSON to `/api/verify`, `/api/planted-news`,
or `/api/ghost-job`. Sightings and postings are plain dicts in the shape
documented in `vessell/app/server.py`; bad input returns HTTP 400 with an
`error` message, never a traceback.

### Developer setup

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

Current code lives in `vessell/`, contracts in `schemas/` and tests in `tests/`.
Optional dependencies are listed in `requirements/`.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright 2026 Christopher R. Vessell.
## Archive and maintenance

The [archive index](archive/README.md) records relocated material and its
original paths. It is reference history, not a list of current features.
The [maintenance guide](docs/repository-maintenance.md) covers validation,
discovery, packaged skill synchronization and checksums.

Working compatibility launchers, the installer, KEV intake and recognition
tools retain their entry points and tests. The original paper, source logs,
six-pillar skills and licences remain at their established paths.
Historical game experiments are described separately in
[game integration](docs/game-integration.md); they are not the live campaign.
