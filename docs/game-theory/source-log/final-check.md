# Final campaign and model checks

The Hybrid State Transition System: Discrete Event in Continuous Motion

- 64 automated tests pass: campaign/tactical handoff and mission gates, collision/line of sight, clocks, CPU program, allocation, payoff calculations, authoritative input validation, saved co-op restoration, static reserve invariance, seeded campaign continuation and sustainable harvesting.
- Campaign checkpoint restoration includes gameplay RNG, accepted controls, fixed-step clock and replayed mission commands. Tested subsequent FPS state is identical under the same actions and steps.
- Savings and available influence-XP ledger conserve earned awards. Harvest cannot exceed unused actual deposits or the excess above its protected target. Co-op replay carries savings and progression into the next encounter.
- Static reserve injury fixture: HP [100,100] becomes [94,93]; weights, quota and power shares remain unchanged; reserves remain [150,150].
- Source syntax and git whitespace checks pass. The hosted production build is checked separately during publication.

Limits: these tests do not exhaust every possible game state or certify browser/device behavior. Browser visual/touch QA was unavailable because the managed preview failed. The recovered blueprint describes modules absent from the inspected 0.2.0 source; they are preserved as historical claims rather than marked complete. Sampled/retained logs are bounded and report their limits. Available savings XP is an accounting ledger, not a new purchase system. Cross-browser bitwise floating-point determinism is not certified. GitHub remote branch creation is blocked by integration permissions; the local branch and bundle contain the changes. The published site remains owner-private; Handshake submission has not been performed.
