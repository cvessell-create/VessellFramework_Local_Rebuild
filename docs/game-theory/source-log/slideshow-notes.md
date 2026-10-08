## Slide 1: The Hybrid State Transition System: Discrete Event in Continuous Motion

**Backward induction, algorithm provenance and weighting**

Christopher R. Vessell
Source: GitHub main 5d5c04b and matching uploaded 0.2.0 archive

## Slide 2: The evidence boundary

**Two source records remain distinct**

The upload matches main. The earlier blueprint describes additional modules absent here. The recovered catalog and request log remain included.

## Slide 3: Backward induction

**Terminal utility determines earlier choices**

Terminal: V(s)=R(s)
Decision: V(s)=max V(T(s,a))
Chance: V(s)=sum p(a)V(T(s,a))
General-sum: the acting player maximizes their own utility.

## Slide 4: The boss plan

**One boost produces deterministic value 490**

500 reward minus 10 boost cost
Collect boost-1, reform Jack + Reader + Medic, then check
The planner excludes the UI d20 retry gate.

## Slide 5: Banzhaf enters through coalition swings

**B_i = swings_i / total swings**

A swing changes a losing coalition to winning when player i joins. Absolute Banzhaf uses 2^(n−1) as denominator. Your reward uses normalized Banzhaf.

## Slide 6: The reward formula

**XP = min(C, floor(C(φ_i+B_i)/2) + 25 critical)**

φ_i is Shapley–Shubik power. C=300 ordinarily. Death gives zero. Two equal critical survivors in the declared fixture receive 175 XP each.

## Slide 7: The first weights

**w_i = ceil(maxHP_i/4) + 2 level_i**

Equal 100 HP, level-1 players each start at weight 27. Enemy HP sets the quota. Stats are designer inputs. Power shares are computed outputs.

## Slide 8: The feedback direction

**XP changes later levels and later weights**

level = max(oldLevel, min(5, 1 + floor(totalXP/300)))
A later encounter recomputes weights. The current model freezes at first shot. This dependency has no unique inverse.

## Slide 9: Unweighted output needs an adapter

**Algorithm output does not define a utility coefficient**

A Boolean SAT answer can gate eligibility. A route can measure distance. A match assigns a role. Numeric weights require declared units and transformations. Uncalibrated fields stay null.

## Slide 10: Allocation uses supplied priorities

**Dean and Hill conserve an integer budget**

Dean uses a harmonic threshold. Hill uses a geometric threshold. Equal NPC weights [40,40,40] and budget 5 produce [2,2,1] under lower-index ties.

## Slide 11: The strategic information matters

**Simultaneous and sequential Chicken differ**

Mixed simultaneous play yields with probability 0.9 and expected payoff −0.1 each. The observing sequential NPC gives outcome (1,−1).

## Slide 12: Fair division

**Bids feed a different class of weights**

Vickrey charges second bid. Knaster conserves cash transfers. Adjusted Winner splits divisible bundles. Bids are reported values, not voting power or measured skill.

## Slide 13: Paradox and governance

**Agenda sensitivity motivates comparison**

Keep chair agenda ordering, weak dominance, May two-option voting and Gibbard–Satterthwaite assumptions separate. The earlier governance module is absent in the uploaded version.

## Slide 14: The earlier blueprint

**Graph, SAT, matching and EDA records remain preserved**

Earlier catalog claims Euler/sorted-edge patrol, MST, SAT, timing, Gale–Shapley, EDA and agenda prototypes. Their paths and source hashes are compared in the reconciled catalog.

## Slide 15: Logging in both directions

**Every value carries its origin and consumer**

Input, algorithm, formula, output, units, normalization, source version, downstream consumer and reverse dependencies. No automatic learning coefficient is inferred.

## Slide 16: The Handshake continuation

**The game and audit remain separately testable**

Room-code co-op, durable snapshots, shared battle and host replay. Source audit includes 64 passing tests. Remote GitHub branch creation is blocked by integration permissions. Final contest submission remains separate.
## Slide 17: Whole-state transition

S_next = F(S, ordered action, dt, wall clock, random draws). Continuous-valued motion and discrete event guards share one hybrid state.

## Slide 18: A constant coordinate

The locked reserve is constant while position, health and cooldown evolve. Full kernel restoration is tested; public logs omit tokens and sealed bids. Seeded checkpoints reproduce the tested continuation with the same actions.

## Slide 19: Savings and harvesting

D=floor(A/4); protected target L=floor(R/2); H=min(request,remaining deposit budget,max(0,bank+D−L)). Savings plus available ledger equals total earned influence XP. No income is generated from reserve itself.
