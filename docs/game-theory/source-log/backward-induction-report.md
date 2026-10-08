# Hail to the Analyst: backward induction and source audit

Christopher R. Vessell · Handshake continuation · October 7, 2026 Pacific

## Evidence boundary

The supplied `hail-to-the-analyst-0.2.0-source.zip` has SHA-256 `cff55d24dd90a48261c571a626c2d32401560c5866c27fb0caa459eb5175d380`. Every shared file matches GitHub `cvessell-create/hail-to-the-analyst` main commit `5d5c04b63a0048af3e9245a06a41890777271034`. The original archive has 91 entries. The audit inventory distinguishes first-party and vendored code. Archive correspondence was checked before changes.

The recovered `Hail-design-blueprint.md` version 3 and `Hail-algorithm-catalog.json` version 2 describe a separate, more extensive branch. Both are preserved verbatim under `recovered/`. Their file names, source hashes and test claims do not establish that those modules exist in this 0.2.0 checkout. No prior test count has been reused as a current result. No complete original chat transcript was available: `branch-log.md` preserves the recovered request history and explicitly labels its provenance.

## What backward induction means here

Two uses must remain distinct. **Mathematical backward induction** solves a finite sequential game from terminal payoffs. **Backward engineering traceability** starts with a desired outcome and identifies the preceding code, rules, inputs and evidence. Rendering, collision and apportionment are algorithms that constrain the game; they do not independently define a strategic equilibrium.

A strategic model requires actors, available actions, information, transition rules and utilities. For a terminal state, V(s)=R(s). At a maximizing decision, V(s)=max over a of V(T(s,a)). A zero-sum minimizing opponent uses min. Chance uses V(s)=Σ p(a)V(T(s,a)). General-sum decision trees retain both utilities and maximize the acting player's component. Cycles or an exhausted horizon invalidate an exact result in this implementation.

`engine/math.js::backwardInduction` supports max/min/chance nodes, JSON state memoization, horizon ≤64 and node budget ≤100,000. `engine/game-theory.js::solveTree` supports acting players 0/1 and chance, depth ≤32 and ≤10,000 nodes. Neither solves arbitrary infinite games, hidden-information games or imperfect-recall games. The scalar planner counts visits before cache lookup, so its node count includes repeated visits. Big-O below treats bounded scalar operations as unit cost unless stated otherwise.

## Executed worked example: ultra-boss

Desired terminal outcome: defeat the boss and award 500 XP once. Work backward:

1. `boss.check(team)` requires exposed stage and Jack's critical contribution in a winning coalition.
2. Exposure requires `boss.reform(team)`: Jack plus at least one ally, inclusion-minimal winning at threshold 6.
3. Jack begins with zero earned weight; each distinct boost adds 2, capped at 4. One boost permits weights [2,2,2] and the three-person team.
4. Reform removes the boss veto and changes the weighted game. It does not defeat the original veto game while holding rules constant.
5. The planner's terminal utility is 500−10×boosts. One boost gives 490. Two give 480. The returned optimal path is collect boost-1, reform [1,2,3], check [1,2,3].

The workbench UI additionally rolls a d20 before the coalition check. That random gate is absent from `backwardPlan`. Thus **490 is exact for the deterministic planning abstraction**, not an expected return for the whole live UI. A faithful stochastic version must declare retry costs and add a chance node. Without those costs, repeated retries do not have a well-defined finite planning tree.

## Matrix games and the information change

The supplied Chicken matrix has payoffs (Yield,Yield)=(0,0), (Yield,Charge)=(-1,1), (Charge,Yield)=(1,-1), (Charge,Charge)=(-10,-10). `analyze` detects pure Nash outcomes and a nondegenerate interior 2×2 mixed equilibrium. Each player yields with probability 0.9. Expected payoff is −0.1 each, up to floating-point representation.

Expected utility U_k=Σ_iΣ_j p_i q_j u_k(i,j). Pure Nash requires neither actor to improve by unilateral deviation. A weak dominance comparison requires all payoff differences ≥0 and at least one >0; strict requires all >0. Comparisons concern the supplied opponent actions, not every conceivable response. A strictly dominant action must strictly dominate every alternative.

`matrixTree` lets the NPC observe the first player's move. The resulting sequential game chooses Charge then Yield, with payoff (1,−1). It changes information structure; it does not solve the simultaneous matrix by backward induction. Minimax saddle points apply only to the code's constant-sum test. Degenerate or higher-dimensional mixed equilibria remain outside scope.

## Complete implemented math-to-code ledger

| Mechanism | Formula or operational rule | Backward outcome trace | Code / evidence | Bounds and limits |
|---|---|---|---|---|
| Banzhaf power | Count losing coalitions made winning by player i. Absolute β_i=b_i/2^(n−1), normalized=b_i/Σb_j | XP reward requires survival, then criticality and recorded encounter model | `js/power-index.js::analyze,critical,reward`; engine math tests | Enumerates 2^n coalitions, n≤16. With veto checks inside each candidate test, conservative O(2^n(n+nv)) time, O(2^n+n) memory |
| Shapley–Shubik | φ_i=Σ swing S |S|!(n−|S|−1)!/n! | Reward uses mean of normalized Banzhaf and φ, with a critical bonus | Same module; exact pivot counts stored as strings | Counts exact via BigInt. Displayed shares floating point. Bit-cost grows with integer size |
| Minimal coalitions | Winning coalition loses if any member removed | Shield reform must contain Jack and meet this condition | `minimalWinning,bottomUp`; boss tests | Enumerative, exponential. Naive validation and subset/member scans add polynomial factors. “Minimum-cost” is scoped to inclusion-minimal teams containing seed |
| Encounter influence | w_i=ceil(maxHP/4)+2level; q=ceil(Σw[0.5+min(0.4,enemyHP/2000)]) | Encounter model freezes on first shot, victory rewards only once | `encounter,reward`; `server/arena.js::settleCombat` | Original balance formulas. XP cap 300, or 500 for boss model. These are not real-world social power or learning estimates |
| Dean allocation | Threshold 2k(k+1)/(2k+1); priority w(2k+1)/(2k(k+1)) | Placed sector resources require allocations, capacities and validated scene | `engine/math.js::round,apportion,environment` | O(Tn) priority comparisons, O(n+G) storage incl. map work. Positive weights start with one, zero excluded, lower-index tie |
| Hill allocation | Threshold sqrt(k(k+1)); priority squared w²/[k(k+1)] | NPC level budget must conserve total and stay ≤5 | `apportion,npcLevels` | n≤128, T≤10,000. BigInt cross multiplication orders priorities. Rejects insufficient budget and excessive levels |
| Rounded d20 skill | DC=10+rounded NPC level; natural 1 fails, natural 20 succeeds | UI boss check needs roll before coalition award | `skillCheck`; workbench boss handler | Constant bounded work. Rounding a raw skill value is an original game choice |
| SRD-style attack | modifier=floor((ability−10)/2); d20+modifier+proficiency vs AC | Kill outcome requires legal action, hit, strike damage and HP transition | `js/tactics.js::modifier,d20Attack,strike,attack` | Jack uses AC rolls. Others use terrain avoidance. These are alternatives, not two hit tests in succession |
| Advantage | Max of two d20; disadvantage min; both cancel | Conditions determine roll rule before attack | `d20Attack`, tactics tests | For base hit probability p, independent advantage gives 1−(1−p)², disadvantage p² where event definition is held fixed |
| Terrain strike | Chance=clamp(100−defense,0,100); strike resistance modifies damage | Terrain and conditions determine hit before HP updates | `hitChance,strike` | RNG is injectable in rules tests. Browser Math.random play is not a seeded replay guarantee |
| Hex geometry / routes | Odd-column neighbors, cube-distance metric; remaining movement decreases by terrain cost | Tactical victory needs reachable objective with Jack or enemy elimination | `neighbors,hexDistance,routes,move,outcome` | Routes repeatedly sort pending list. Conservative O(K² log K) queue work plus occupancy scans over visited cells. This is not a heap Dijkstra complexity claim |
| Zone of control / conditions | Enter hostile zone ends move except skirmisher; durations tick on turns | Legal movement and attack precede mission handoff | `enemyZoc,tickConditions,endTurn` | Explicit control rules. Fear prevents approaching its live source. Stun blocks actions. Bounded campaign map |
| Breach handoff | Survivors grant armor/ammo; losses add FPS enemies | FPS starts only after tactical win and valid handoff | `handoff`; `index.html`; FPS integration tests | Counts original squad IDs only. Retry preserves breach without stacking |
| Vickrey auction | Highest bid wins, pays second highest | Power effect requires precombat sealed round and complete bids | `engine/fair-division.js::vickrey`, arena bid settlement | O(n log n), n=2–8. Lower join index tie. Treasury receives game credits. Team externalities limit truthfulness claims |
| Knaster | entitlement=t_i/n; surplus=Σwon_i−Σt_i/n; cash_i=t_i/n+surplus/n−won_i | Victory cache requires one-use settlement and available bid liquidity | `knaster`, arena tests | O(nm) comparisons, exact rational cash, sum cash=0. Reported additive values, game money only |
| Adjusted Winner | Allocate high values, sort winner items by value ratios, transfer gap/(v_r+v_p) of split item | Victory cache with exactly two participants and equal positive point budgets | `adjustedWinner`; invariant tests | O(m log m) comparisons plus O(m) scans, BigInt arithmetic. Divisible bundles, at most one split. Reported envy-freedom/equity does not prove strategy-proofness |
| Rational arithmetic | gcd reduction; add by common denominator; compare cross products | Settlement invariant requires exact share and credit conservation | `fraction,add,compare` | BigInt bit-cost depends on operand size. Numeric `value` is display only |
| Ray casting / sightline | DDA steps grid boundaries; wall distance blocks actors and shots | Hit outcome needs visible target in angle/range envelope | `engine/core.js::castRay,lineOfSight`; arena step | O(D) cells per ray. Render O(RD), plus sprites. No universal frame-rate claim |
| Collision | Normalize inputs and subdivide movement, test body corners | Accepted position follows bounded server input, not client coordinates | `move,createWorld`; core and arena tests | O(S) substeps, rejects budget >4096. Grid validation/copy adds O(G) |
| Fixed timestep | Accumulate elapsed time, execute ≤8 catch-up steps at 60 Hz | Stable updates require bounded clock and recorded dropped ticks | `core.js::clock`; server loop and campaign integration | O(B×update cost); cap bounds callbacks, not arbitrary callback complexity |
| Multiplayer combat | Δshot=0.3s; damage=25+5power; max range 12, angle error <0.1 rad, LOS | Won phase requires all NPC HP≤0; loss requires all allied HP≤0 | `server/arena.js::step` | O(PN) target searches plus sorts/LOS and power enumeration on roster lock. P≤8,N=3 current |
| Scalar backward induction | terminal / max / min / weighted chance recurrence | Chosen action traces to terminal payoff under declared transitions | `backwardInduction`; executed boss fixture | O(b^h) visit bound before memo reuse, bounded nodes/horizon. Serialization/cache-key cost depends on state size |
| General-sum tree | acting player maximizes its own payoff component | Policy reports selected action and evaluated alternatives | `solveTree,matrixTree` | O(K) nodes excluding retained policy/path copying, which can add O(Kh). ≤10,000 nodes, depth≤32 |
| Mission processor | Original 6502 program verifies readiness bitmask 15 | Clearance and plan approval require acknowledged commands | `js/emulation-engine.js`; JSNES vendor; VM tests | ≤64 instructions per command. NES CPU execution is real; graphics and physics stay in browser JS |
| Serialization / provenance | Scene version migration, bounded JSON parsing, SHA-256 source manifest | Reproducibility needs preferred source, test fixtures and version identity | `engine/systems.js`, `scripts/package-source.js`, audit script | O(bytes) parsing/hashing. A hash does not establish truth, ownership or independent timestamp |

`source-inventory.json` lists exact files, hashes and named functions, including vendor functions. Upstream JSNES CPU/PPU/audio implementations are retained vendor machinery, not newly authored Vessell theorems. Their source and licensing remain in the package.

## Earlier branch concepts and version gaps

The original catalog remains the authoritative record of what that earlier branch claimed. This audit records the claims and compares their paths against the supplied source.

| Earlier request / theory | Backward role in the design | Formula / assumptions | Status against uploaded 0.2.0 |
|---|---|---|---|
| Euler circuit / Hierholzer | Predict NPC patrol before crossing/attack | Connected nonisolated even-degree graph admits Euler tour; visits edges, unlike Hamiltonian vertices | `engine/graph-tactics.js` absent. Earlier catalog claims active NPC patrol |
| Sorted-edge / cheapest link | Select patrol links by cost | Degree≤2, prohibit premature subtours. Heuristic, no optimality guarantee | Same absent file. Distinct from Euler traversal |
| Kruskal MST | Connect rooms at minimum construction cost | Connected weighted undirected graph, add cheapest edge joining components, V−1 edges | Same absent file. Earlier equal-cost exercise checks connectivity |
| Cook / SAT verification | Correct control assignment opens boss vulnerability | CNF true iff all clauses satisfied; assignment verification O(total literals) | `engine/boss-constraints.js` absent. General SAT complexity does not make a fixed three-variable puzzle hard |
| Unit propagation | Defeated sub-boss unlocks forced-value assistance | Single unresolved literal in clause forces value; contradiction detects failure | Same absent file. Not a complete solver for arbitrary SAT |
| Critical path | Compute earliest legal shot readiness | DAG earliest finish=max predecessor finishes + task duration | `engine/timing-plan.js` absent. Timing and spatial collision are separate |
| Swept segment-circle | Determine target crossing during a shot step | Solve quadratic intersection along finite segment and check wall obstruction | Earlier hit module absent. Uploaded arena uses angle/range/LOS target selection |
| Ordered objectives | Extraction follows gate, freshness, corrections, review and boss prerequisites | Topological prerequisite evaluation, reject forward/duplicate dependencies | `engine/objectives.js` absent. Uploaded campaign has its own mission gates |
| Gale–Shapley | Assign next-round focus / prospective squad roles | Strict one-to-one preference lists, hold better proposal, requeue displaced proposer | `engine/round-matching.js` absent. Earlier catalog claims solo use; multiplayer assignment remains prospective |
| EDA class intervals | Review run measurements before adjusting balance | Bin counts with explicit boundaries and missing-value rules | `engine/eda.js` absent. Earlier prototype uses synthetic data |
| Interpolation | Estimate between observed settings | y=y0+(x−x0)(y1−y0)/(x1−x0); defined bracket, no extrapolation | Same absent file. No calibration inferred |
| Pearson association | Relate paired observations | r=Σ(x−x̄)(y−ȳ)/sqrt[Σ(x−x̄)²Σ(y−ȳ)²] | Same absent file. Constant variable gives undefined coefficient; association is not causality |
| Discrete moments / seeded sampling | Declare chance outcomes for expected utility | μ=Σpx, variance=Σp(x−μ)², σ=sqrt(variance), Σp=1 | Same absent file. Supplied gameplay uses ordinary random draws in several UI paths |
| Agenda control / chair paradox | Compare next-round options in sequential votes | Condorcet cycle can make ordering affect winner | `engine/coop-voting.js` absent. Exact intended chair paradox citation still unresolved |
| May pairwise majority | Audit two-option vote response | Two alternatives, unrestricted domain, anonymity, neutrality, positive responsiveness | Earlier branch claim, absent module. Incumbent tie-break is a separate mechanism |
| Gibbard–Satterthwaite | Set bounds on manipulation claims | Deterministic onto rule, unrestricted strict preferences, ≥3 outcomes, nondictatorship implies some individual manipulation | Earlier governance model only. The theorem neither supplies a general group-manipulation detector nor guarantees strategy-proof co-op |
| Counter point principle | Owner-defined criterion for contrasting preferences/priorities | Precise transition rule and objective still needed | Pending owner definition. No standard theorem inferred |
| Repeated / Bayesian models | Possible extension to beliefs and across-round incentives | Need information sets, update rules, discounting and calibrated utility | Prospective in recovered catalog. No hidden-belief solver claimed |
| x86 / RV32 / ISO9660 | Earlier branch execution and export experiments | Original firmware/readiness programs, serialized mission data | Those integrations absent here. Uploaded archive includes JSNES only |

## Backward plan to a contest-ready result

Terminal goal: a reviewer can open the public URL, create a room, join from a second device, play the same encounter, and replay. Predecessors: public access, deployed persistent room server, tested authoritative transitions, room-code UI, synchronized snapshots and retry/error behavior. A downloadable prototype alone does not fulfill the mission's live multiplayer requirement.

The continuation adds durable room snapshots, optimistic version checks against simultaneous updates, random room codes, multi-device input polling and host replay. Database state, rather than browser storage, owns each room. It retains the existing arena's battle and economy rules. Input validation rejects client-set position/damage, expired tokens and replayed sequence numbers. Polling is network synchronization, not proof of low-latency esports quality. Long inactive intervals cap catch-up to two seconds; this is a disclosed performance policy, not strict wall-clock simulation. Offline campaign and labs remain separate from shared co-op.

The original local arena had no persistent state. New persistence tests reconstruct independent arena instances and verify sealed bids, exact credit conservation, position, sequence and combat lock. Failure discovered during development: restore referenced enemies before initialization. Corrected by restoring after enemy construction. `test-results.txt` records the final run. Production deployment and public access are separate gates, reported in the final handoff rather than asserted by this design document.

Official entry fields: project title, project cover image, project description and project URL. Official rules deadline: October 30, 2026, 11:59 p.m. Pacific. The mission page says October 31; use the official rules' earlier deadline. $1,000 is a judged prize for each of the top three winners, not guaranteed payment. A final Handshake account submission is not claimed in this audit.

Sources: uploaded source, matching GitHub commit, recovered blueprint/catalog and current official challenge documents. Full external theorem sources remain separately identified in the recovered catalog. Its previous “opened” labels reflect that earlier record, not new verification in this continuation.
