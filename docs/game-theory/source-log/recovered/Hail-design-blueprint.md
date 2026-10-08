# Hail / Vessell engine 0.2 blueprint

Design draft for owner review. Original first-person missions and room geometry now run in Hail. Engine components remain separate and traceable: JSNES 2.1.0 runs the original mission CPU; source-built v86 JS/WASM runs original x86 reset firmware and exports ISO9660 mission data; selected TinyEMU MIT sources build an offline original RV32 readiness check. No third-party BIOS/OS or Capcom assets are included.

| Mechanic | Algorithm | Strategic role |
|---|---|---|
| Patrol | Euler circuit over a sorted-edge Hamiltonian ring | Predict and time encounters; interrupted combat can deviate from the route |
| Room planning | Kruskal minimum spanning tree | Connect core rooms cheaply; live maps retain a redundant escape corridor |
| Boss shield | CNF assignment verification | Solve a bounded control puzzle to arm an eight-second combat window |
| Power-up | Unit propagation | Sub-boss defeat unlocks forced-value assistance; assisted outcomes are recorded |
| Shot timing | Longest path through timing dependencies | Model cooldown separately from spatial impact |
| Hit/miss | Swept segment-circle intersection and wall DDA | Test crossing targets and blocking walls; current targets are stationary per step |
| Objectives | Ordered prerequisite list processing | Gate clearance, fresh sources, corrected records, review and boss completion |

The catalogue has 17 entries, including supporting rendering, collision, timing, serialization, source-lineage and emulator algorithms plus prospective repeated-game/Bayesian models. Each entry records definition, source hash, implementation status, inputs/outputs, tests, game conversion, blank utilities with rationales, worst-case costs and unresolved questions. Algorithms alone are not game-theory models; actors, strategies, information and payoff assumptions must also be specified.

General SAT is NP-complete. The current three-variable tutorial is intentionally easy and fully solvable by unit propagation; it does not demonstrate general NP-complete problem-solving or intelligence. Euler traversal and ordinary MST are efficiently solvable. The current sorted-edge tour is heuristic, not guaranteed optimal. Current equal-cost MST exercise checks connectivity rather than unequal-cost optimization. No human learning effects or skill weights are estimated.

Tests: 52 game checks; 18 standalone engine checks; framework 781 passed,4 skipped and1 deprecation warning. Desktop/mobile browser checks cover source inspection, JSON/ISO downloads, x86 homebrew execution and MST planning. SAT UI checks explicitly injected mission/sub-boss state for QA and are not a full player playthrough. Full build failures and corrections remain in the companion evidence.

Original modules retain requested Christopher R. Vessell attribution and Apache-2.0. Vendors retain their BSD/MIT/Apache notices. Combined Hail distribution remains GPLv3. Attribution does not establish legal copyrightability of assistant-generated material or exclusive rights to upstream code. See exact package manifests, source archives and notices.

Only course codes/titles from the uploaded transcript enter the staged theory seeds. Grades, identifiers and the full transcript are excluded. Suggested theories are not asserted as syllabus contents. Textbook/model assumptions, payoff units, harder puzzle design and efficacy comparators remain owner inputs.

Repository → game → session log → unsigned receipt → owner review → repository revision remains the feedback path. Multiplayer networking, chain anchoring, wallets and settlement are not implemented; monetary transactions remain zero and unset costs/utilities remain null. Hashing does not establish payment, ownership, truth or independent time.

Download packages include local branch bundles and patches for both repositories. GitHub write access was blocked earlier; no new remote branch or PR is claimed. The prototype is not yet a multiplayer contest submission or a finished general-purpose game engine.

Gale–Shapley deferred acceptance now plans a solo next-round focus and records every proposal/hold/rejection/displacement. The reusable matcher supports strict one-to-one incomplete preference lists; tests check displacement, unmatched acceptability and no blocking pairs. The next briefing displays the chosen focus. Multiplayer allocation is prospective, and no role-stat bonus is implied. Under standard constant-time ranking/queue lookup assumptions, proposals are bounded by listed proposer-role pairs: O(n²) for complete equal-sized sides. Stability is not fairness or maximum team utility. Owner counter point principle remains pending a precise definition.

## Analysis and cooperative governance extension
EDA class intervals, pairwise-complete Pearson correlation, nonextrapolating interpolation, declared discrete probability moments and seeded sampling are implemented in engine/eda.js. The sample is synthetic. Utility weights remain null pending calibration.

Cooperative sequential majority voting compares supplied coalition reports and agendas. A Condorcet-cycle test exposes agenda sensitivity. Gibbard–Satterthwaite is an individual strategy-proofness impossibility under specific assumptions; no group strategy-proof guarantee is claimed. Exact chair paradox reference is unresolved. See docs/cooperative-governance.md. Offline prototype; no authoritative multiplayer or payment settlement.

VS Code: Node24+, `node scripts/serve.cjs`, then localhost:8080/engine/eda-demo.html. Export: `node scripts/eda-log.cjs design/analysis-sample.json NEW_FOLDER`. Third-party components and their retained licences are included in the source packages.

Owner backbone: agenda control plus weak dominance of X over Y, scoped to supplied opponent payoff responses. May pairwise majority preserves ties; incumbent tie-breaking remains a separate mechanism. No manipulation-free multiplayer guarantee.
