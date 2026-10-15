# Hail game and framework integration

The game and framework are separate products with separate repositories.
Current framework direction is in [vision and scope](../VISION_AND_SCOPE.md).
The browser campaign is in the
[game repository](https://github.com/cvessell-create/hail-to-the-analyst).

## Current boundaries

- The campaign is human-controlled. It does not load the framework chatbot,
  source corpus, formula service or automation driver.
- Framework chat, SI-level measurements and case-policy formula helpers are
  development/research tools, not player progression or report-release gates.
- The selected native direct-game rebuild is future work, not the existing
  browser engine. Use the game's current engine guide for its implementation.
- Source inspection, simulation, human review and authorized external actions
  remain separate.

The [corrected formula](vessell-formula.md) checks a fixed ASCII case policy,
corrects at most once and verifies. It does not repair failed evidence checks,
promote SI levels or automate game controls.

## Preserved development interfaces

`vessell.game_bridge` remains available for existing local experiments and tests.
It is not needed to play the campaign. It includes synthetic provenance
sessions, paired simulation and a native C slice adapter; each requires its
matching game-side assets. Do not infer that an arbitrary checkout provides
those historical assets.

Inspect the supported options without starting a server:

```sh
.venv/bin/python -m vessell.game_bridge --help
```

Existing bridge operations stay loopback-only and require explicit local paths.
Do not expose this development service publicly or turn fictional game claims
into real-world evidence. It is retained for compatibility and reproducibility,
not reinstated as player automation.

## History

The [archive](../archive/README.md) holds the earlier
[v3.9.1 integration guide](../archive/game/game-integration-v3.9.1.md) and
[Mac-local AI preparation prompt](../archive/game/local-hail-ai-future-run-prompt.md).
Their pause states, commands, missing-asset observations and measured results
describe their original snapshots, not the current campaign.

The [architecture adaptation skill](../GAME_DEVELOPMENT_SKILL.md) and component
map preserve the original game reconstruction and Signal Recall research.
Their pinned-source ledger remains available; it is not the current game
manual. Owner sources and audit records are not purged.
