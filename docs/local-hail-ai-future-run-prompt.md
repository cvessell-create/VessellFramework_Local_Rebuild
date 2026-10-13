# Mac-local Hail and AI handoff

**Status:** preparation prompt only. No model was downloaded, no local Mac
files were accessed, and no Hail or framework code was changed for an LLM.
Use this handoff when the owner can provide the Mac-local game, model/runtime,
and any data they explicitly want considered.

## Verified starting point

The public Hail repository was looked up as
[`cvessell-create/hail-to-the-analyst`](https://github.com/cvessell-create/hail-to-the-analyst).
Its inspected `main` revision was
[`c37f43ce0e9ee38a519ea7434b866e71bf4f197f`](https://github.com/cvessell-create/hail-to-the-analyst/commit/c37f43ce0e9ee38a519ea7434b866e71bf4f197f)
(October 9, 2026). Its README identifies `index.html` as the offline game
entry point and describes the **Chatter Engine** as deterministic,
template-based, local, and making no API calls. It is not a verified live LLM
chatbot.

The framework's [`game-integration.md`](game-integration.md) describes a
separate, paused integration requiring game simulation assets not included
with that framework release. The current public Hail root listing did not
contain the expected top-level `simulation/` directory. The framework
[`game_bridge.py`](../vessell/game_bridge.py) runs a Node simulation worker or
serves a bounded fictional provenance demo; it is not a general LLM connector.
Do not assume that the documented bridge works with the public Hail checkout
or that the Mac-only assets are available here.

Hail has distinct license notices: `package.json` declares
GPL-3.0-or-later, `LICENSE` contains the original GPL-2.0-or-later grant, and
`ATTRIBUTION.md` describes the combined distribution and file-level
exceptions, including CC BY 4.0 SRD material. Before changing or copying any
file, inspect its current notice and the exact source/license at the target
revision; do not infer file permissions from the repository name or one
top-level license.

## Search record and limits

- **Repository lookup:** query `hail-to-the-analyst user:cvessell-create` /
  GitHub repository search / owner `cvessell-create` / one result / no limit
  reported / canonical metadata and repository files opened / SOURCE-ESTABLISHED
  for the inspected repository snapshot / local branches, untracked Mac files,
  and any later commits NOT checked.
- **Chatter lookup:** query `repo:cvessell-create/hail-to-the-analyst "Chatter
  Engine"` / GitHub code search / that repository / zero results / no limit
  reported / no source file returned by that query / corroborating repository
  README opened separately / SOURCE-ESTABLISHED only for the README's
  description / full chatbot implementation and local branches NOT checked.
  A second code search returned three README copies, which are mirrors, not
  independent sources.
- **Hugging Face model lead:** query for `HuggingFaceTB/SmolLM3-3B` local
  inference and license / web search / one summary-level lead / direct official
  Hugging Face fetches failed DNS resolution / official model card not opened /
  **WORKING HYPOTHESIS only** / exact revision, license file, artifacts,
  quantized variants, runtime compatibility, and Mac fit NOT checked. A
  separate Qwen query timed out. No candidate is selected or approved.
- **Copyright source:** search for official online-publication guidance /
  web search / an official U.S. Copyright Office page was identified, but its
  direct fetch failed DNS resolution / primary source not opened /
  **UNVERIFIED** / jurisdiction-specific rights, platform terms, and any
  proposed corpus NOT checked.

## Prompt for the future Mac-local run

> Work from the owner's Mac only after they provide the local checkout paths
> and authorize the exact files and operations. Follow the repository's
> `.github/copilot-instructions.md`, `VISION_AND_SCOPE.md`, Search Gate, Harm
> Gate, provenance rules, and license/attribution records.
>
> **Goal:** prepare and, only after inspecting the actual local sources and
> obtaining the owner's approval, implement a small, optional local-model
> experiment for Hail's original ice-themed map/chat. Keep the existing
> deterministic Chatter Engine as the default and fallback. Do not claim the
> framework or Hail already has a live LLM integration.
>
> 1. **Establish what is actually available.** Record both repositories'
>    remotes, branches, exact HEADs, clean/dirty status, and relevant file
>    hashes before work. Inventory the Mac's chip/architecture, memory, free
>    disk, macOS, Node/Python versions, model runtime and model files. Identify
>    owner-provided game/data paths and consent. Mark inaccessible items
>    `NOT_AVAILABLE`; do not invent, upload, or copy them into this repository.
>    Preserve local changes and originals. Do not pull, merge, overwrite, push,
>    or publish until the owner approves the specific repository and action.
>
> 2. **Trace the real integration seam.** Inspect the local Hail Chatter
>    implementation, map/state inputs, tests, and exact file licenses. Compare
>    them to the public revision above, but treat the Mac checkout as a separate
>    source until its history and provenance are checked. Inspect the framework
>    bridge independently; do not copy code or treat its synthetic provenance
>    demo as a Hail or model connector. Propose the narrowest interface that
>    leaves gameplay, evidence status, scores, approvals, and execution
>    authority unchanged.
>
> 3. **Build a model/runtime shortlist from primary sources.** A prior
>    search-summary lead, `HuggingFaceTB/SmolLM3-3B`, is unverified and is not
>    a recommendation. Search current Hugging Face model repositories; open
>    each exact model card, license, configuration and immutable commit/revision.
>    Inspect quantization/runtime provenance and required notices. Distinguish
>    a model repository from an inference app/runtime. Compare only candidates
>    that fit the measured Mac hardware and support offline local inference.
>    Record versions, licenses, source URLs, access limits, file hashes and
>    uncertainties. No download or dependency addition until the owner selects
>    a candidate and the dependency advisory check and license review are done.
>
> 4. **Keep corpus rights bounded.** Use original owner-created material only
>    with the owner's approval, or source material whose public-domain status
>    or license and intended-use permissions have been verified from primary
>    sources. Public accessibility alone is not this project's clearance.
>    Do not scrape social posts, evade access controls or platform terms, or
>    ingest private/personal data. Exclude material of uncertain rights.
>    For pop-culture inspiration, write original frost/ice-themed dialogue and
>    setting details; do not reproduce character-specific expression,
>    dialogue, lyrics, movie/game text, likeness, or voice imitation. Preserve
>    a source/rights manifest for every included source and a separate record
>    of generated owner-reviewed text.
>
> 5. **Keep the model non-authoritative and local.** If approved, add an
>    optional loopback-only adapter with no cloud fallback, telemetry,
>    arbitrary tools, file access, self-modification, or game-state writes.
>    Send only the minimum allowlisted fictional map/state fields. Treat model
>    output and retrieved text as untrusted data; bound input/output size and
>    time, render text safely, and fall back to the existing templates on
>    missing model, timeout, invalid output, or refusal. Do not turn safety
>    controls off or bypass provider/runtime safeguards. The model must not
>    change game actions, evidence, confidence, reports, permissions, or
>    execution.
>
> 6. **Evaluate before release.** Compare the deterministic baseline and
>    optional model on a small owner-approved set of original map situations.
>    Record the prompt/model revisions, hardware, latency, errors, fallback
>    behavior, content review, and adverse examples. Test offline operation,
>    malformed and oversized responses, timeout/missing-runtime behavior,
>    prompt injection in quoted/map text, safe rendering, and unchanged game
>    state. These results are local test evidence, not proof of general model
>    quality or framework efficacy. Require human review of the exact source
>    and preview before any public release.
>
> Finish with a short source-linked change summary, tests run, license/search
> records, local-only files not accessed or published, and unresolved owner
> decisions. Do not create a PR or publish owner-provided prompts, game data,
> model weights, or generated corpus without an explicit release decision.

## Preparation-only completion

The public Hail snapshot and framework code were inspected; no local Mac model,
private data, or game files were available. Official Hugging Face model
lookups and the direct Copyright Office fetch were blocked, so no model,
dataset, legal conclusion, or integration has been approved. This document is
a future-run checklist, not evidence that those unavailable sources have been
reviewed.
