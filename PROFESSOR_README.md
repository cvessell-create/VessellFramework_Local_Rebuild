# Graduate research review

Christopher R. Vessell

M.S. Strategic Intelligence — working project

## Project

VessellFramework combines analytical methods, source tracking and executable
evidence-analysis tools. Its proposed application is a personal and family
privacy, safety and rights agent.

The framework has three parts:

1. **Methods:** six analytical pillars, decision provenance, Harm Gate and
   Maskirovka checks.
2. **Workflows:** analyst and forecasting guides for source assessment,
   alternatives and correction.
3. **Software:** evidence intake, weighting, source-lineage checks, correction
   propagation and human report review.

The [game](https://github.com/cvessell-create/hail-to-the-analyst) provides a
simulation setting for testing methods, formulas and decision processes.
[Play the current browser version](https://cvessell-create.github.io/hail-to-the-analyst/).
The high-detail native engine rebuild is planned.

## Current work

- Evidence-analysis API and human review workspace.
- [GitHub agent integration](docs/github-agent-integration.md) for reference
  searches and owner-requested analysis previews.
- Native C game bridge and current-run Vessell formula checks.
- Separate tests for generated chat responses and formula telemetry.
- Local game console for AI/SI requests and collectible metadata previews.

Coinbase integration and NFT minting are planned. Family isolation, safe
sharing and protective workflows are unfinished. Existing services are
single-owner.

## Methods and sources

The pillars are PARADOX, BOTTLENECK, DUAL LAYER, XFACTOR, KNOWING FIELD and
GAME THEORY.

Knowing Field draws on Scharmer and Pomeroy's (2024) fourth-person knowing.
It requires human inquiry before report release; AI does not perform
presencing. See the [source skill](Knowing_Field_Theory_SKILL_v0.1.md),
[audit](docs/knowing-field-framework-audit.md) and
[application](VesselFramework_Knowing_Field_SKILL_v0.1.md).

Game Theory uses declared actors, actions, information, utility units and
evidence. The other pillars constrain the model and challenge its results.
See the [application](VesselFramework_Game_Theory_SKILL_v0.1.md).

The [original paper](docs/claim-correction-case-study.md) is preserved.
[Source reconciliation](docs/paper-source-reconciliation.md) separates the
author's account from later research and software.
[Civilian authorship guidance](docs/civilian-authorship-and-model-interference.md)
preserves reported concerns without treating contested attribution as fact.

## Evaluation

The software tests specific code behavior. Empirical usefulness and transfer
to personal/family protection still need study.

A proposed study would compare a source-linked checklist with the assistant
on a defined synthetic or consented case set. Score source accuracy, routing,
unsupported legal claims, disclosure, unsafe actions and reviewer comprehension.
Set the rubric, units, sample, adjudication and stop criteria before testing.

Include conflicting evidence, missing consent, unavailable sources, expired
permissions and compromised devices. Retain adverse results. Sensitive family
data requires reviewed participant and storage safeguards.
See the [scientific evidence method](VesselFramework_Scientific_Evidence_SKILL_v0.1.md).

## Feedback requested

1. Are the methods coherent and teachable?
2. Are the source and provenance rules suitable for graduate research?
3. Which contributions are original, and which need clearer attribution?
4. What study would best test usefulness and failure modes?
5. What should be refined before publication?
6. Does the proposed application preserve consent and personal agency?
7. Which findings would challenge the transfer from analytical methods to
   personal/family protection?

## Reading order

1. [Canonical reference](CANONICAL_REFERENCE.md) and [vision](VISION_AND_SCOPE.md).
2. [Original paper](docs/claim-correction-case-study.md) and
   [reconciliation](docs/paper-source-reconciliation.md).
3. [Protection guide](docs/personal-family-protection-guide.md) and
   [specification](docs/personal-family-agent-spec.md).
4. [Combined framework](VesselFramework_MetaMatrix_Framework_v3.8_v3.9_Combined.md),
   [analyst skill](SKILL.md), Knowing Field and Game Theory links above.
5. [Forecasting](VesselFramework_Forecasting_SKILL_v1.0.md) and
   [research roadmap](META_REVIEW_AND_ROADMAP.md).
6. [API contract](docs/specialist-agent.md) and [tests](tests/).
