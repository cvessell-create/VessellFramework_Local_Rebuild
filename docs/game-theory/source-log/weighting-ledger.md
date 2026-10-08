# Algorithm weighting in both directions

## The coded chain in this prototype

HP and level feed **integer coalition weights**. Enemy HP feeds a quota. Coalition enumeration turns these inputs into **normalized power indices**. The reward algorithm averages two indices, multiplies by an XP cap and adds a criticality bonus. Cumulative XP changes future level. Future encounters recompute weights from that changed level.

This is the concrete bidirectional relationship in the code: an upstream algorithm's result becomes a downstream input, while backward traceability explains what produced that result. It is not a unique inverse: XP rounding, caps, equal allocations and many-to-one mappings discard information.

| Stage | Input / origin | Exact code | Output and consumer | Backward dependency |
|---|---|---|---|---|
| Initially equal participants | maxHP=100 and level=1 for every new player | `server/arena.js::join` | Equal initial stats | Designer constants, not measured skill |
| Stats as voting weights | ceil(maxHP/4)+2×level | `js/power-index.js::encounter` | 27 per level-1 player with 100 maxHP | Recover stats and formula from log; output 27 alone is not a unique inverse |
| Threat as threshold | ceil(sum(weights)×[0.5+min(0.4,enemyHP/2000)]) | `encounter` | Winning quota | Enemy health, total allied weight and rounding |
| Weights into power | Enumerate winning/losing coalitions and pivotal permutations | `analyze` | Banzhaf absolute/normalized, Shapley–Shubik | Coalition rule, veto list, weights, quota |
| Power output as reward coefficient | meanPower=(Shapley–Shubik+BanzhafNormalized)/2 | `reward` | Scalar in [0,1] multiplied by cap | Both shares and normalization denominators |
| Coefficient into XP | alive ? min(cap,floor(cap×meanPower)+(critical?25:0)) : 0 | `reward` | Encounter XP | Survival, coalition criticality, cap, indices |
| XP into future level | max(oldLevel,min(5,1+floor(cumulativeXP/300))) | `server/arena.js::settleCombat` | Level 1–5 | Cumulative XP and prior level, including any auction level boost |
| Future level into new weights | Reapply ceil(maxHP/4)+2level in a later encounter | `encounter` | Changed integer weight | A new forward evaluation. Current encounter model freezes at first shot |
| Equal/unequal sector priorities | Designer-supplied [1,2,3,4], total 12 | `engine/math.js::environment,apportion` | Dean sector resource allocation | Sector weights, method, minimum unit, budget and tie-break |
| NPC difficulty shares | Equal [40,40,40], budget 5 | `server/arena.js` and `npcLevels` | Hill allocation [2,2,1] | Equal inputs can yield unequal integer outputs because budget indivisibility and tie-break matter |
| Power into rounded skill bonus | rawBonus=1+4×JackShapleyShubik | `engine/workbench.js` boss-check | Hill-rounded bonus, then d20 check | Power model followed by explicit nonlinear rounding |
| Utility into selected action | Terminal payoff or supplied matrix payoff | `backwardInduction,solveTree,analyze` | Policy or equilibrium | Declared actor, information structure, transition and utility |
| Reported values into distribution | Sealed valuations, equal AW point budget or game credits | `fair-division.js`; arena `bid` | Resource shares, transfers or auction winner | Values are bids, not measured merit or voting power |

## Worked weight log

With two level-1 players, 100 maxHP each, one 100 maxHP enemy, the weights are [27,27], threat fraction 0.55 and quota ceil(54×0.55)=30. Each player has Shapley–Shubik=0.5 and normalized Banzhaf=0.5. With both surviving, each is critical: floor(300×0.5)+25=175 XP.

By contrast, two level-1 participants in the actual three-enemy arena face its different enemy-health quota. The general fixture above proves the formula's behavior under declared inputs; it is not a captured match.

`engine/weight-trace.js::trace` calls the same existing `encounter` and `reward` functions. It logs both `forward` and `reverse` dependencies without modifying live balance. `apportionTrace` records supplied weights, allocation and the nonunique reverse boundary. `executed-weight-log.json` includes the exact fixture outputs. Browser match log exports add actual encounter observations, while clearly identifying fixture calculations.

## Unweighted algorithms becoming weights

“Unweighted” can refer to topology without edge costs, equal actor inputs, or an algorithm without a utility coefficient. These are different cases. A graph traversal returns a walk, a SAT verifier returns a Boolean, matching returns assignments, and majority voting returns an alternative. None automatically becomes a cardinal weight.

A proposed adapter must log `rawOutput`, `measure`, `units`, `direction`, `normalization`, `coefficient`, `consumer`, `sourceVersion` and `calibrationStatus`. For example, a valid SAT solution can be a Boolean eligibility gate; treating true=1 and false=0 as reward weight is an additional explicit design rule. An MST total can measure corridor cost; changing cost into an influence score requires a declared transformation and units. Gale–Shapley preferences are ordinal, so rank positions do not automatically equal cardinal utility.

| Blueprint algorithm | Raw output | Potential role as weighting input | Current code status |
|---|---|---|---|
| Euler / sorted-edge | Traversal, edges, route cost | Travel exposure or timing measure after explicit definition | Earlier branch record; no adapter in uploaded source |
| MST | Connected tree and total construction cost | Resource-budget constraint or cost penalty | No automatic weight conversion present |
| SAT / propagation | Accepted assignment, forced literals, assistance flag | Eligibility gate; separate assistance indicator | No automatic utility conversion present |
| Critical path | Earliest finish / bottleneck task | Cooldown timing or declared time cost | Earlier branch record; no adapter here |
| Objective list | Locked/pending/complete | Prerequisite gate or completion proportion after declaration | No calibrated weight present |
| Gale–Shapley | Match, unmatched IDs, proposal history | Role eligibility and assignment, not inherently numerical merit | Earlier branch record; ranks remain ordinal |
| EDA / Pearson | Counts, associations, interpolated values | Inspect candidate coefficients with validation | Earlier prototype, utility weights null |
| Discrete moments | Mean, variance, standard deviation | Expected payoff / risk penalty only if model declares units | Earlier prototype, risk coefficient null |
| Agenda / chair | Winner changes across agendas | Sensitivity diagnostic or explicit cost of instability | Governance weighting null in recovered catalog |
| Weak dominance | All payoff comparisons under supplied response set | Prune or compare strategies under that payoff model | Implemented matrix comparisons here; does not establish global manipulability |
| May majority | Pairwise count and tie | Democratic decision rule under its assumptions | Earlier branch record, not an algorithm weighting theorem |
| Gibbard–Satterthwaite | Impossibility condition | Guardrail on strategy-proofness claims | Theoretical boundary, not a numeric weight generator |

## Paradox and blueprint interpretation

The chair/agenda example motivates a governance experiment: fix player preferences, vary agenda, observe the winner, then compare declared utility outcomes. A weak-dominance test compares supplied action payoffs. May analyzes a two-alternative decision rule under its assumptions. Gibbard–Satterthwaite limits a different class of rules with at least three outcomes. Their scopes do not cancel each other.

The broader Vessell pillars PARADOX, BOTTLENECK, DUAL LAYER and XFACTOR provide an organizing interpretation. They are not numerical coefficients imported into this source. Each proposed connection must pass WHAT, WHY, WHERE, DEPENDENCIES, FAILURE, EVIDENCE and DECISION. Teacher/course-facing theory and the Mother's cross-domain framework remain separate in this audit. No framework production package was imported or its thresholds asserted.

## Reciprocal feedback schema

`theory → mechanic → algorithm → raw result → declared adapter → weight → decision → observed outcome → review → revised version`.

Each update stores previous value, new value, rationale, source and test evidence. The uploaded code has XP/level progression, not automatic statistical coefficient training. Reverse lookup answers “what caused this weight/decision?” It does not infer unique input weights from a rounded XP reward or prove the blueprint's human-learning effectiveness. Null coefficients stay null until an explicit, versioned model defines them.
