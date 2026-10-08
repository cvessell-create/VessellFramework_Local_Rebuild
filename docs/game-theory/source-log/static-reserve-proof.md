# Static reserve: a conditional mathematical proof and executable check

Christopher R. Vessell's interpretation: stored potential influence acts as a static reserve within an encounter.

## Definition

Let w be the fixed participant weight vector, q the winning quota, v the veto set and C the encounter's base XP scale. Let B_i be normalized Banzhaf power and φ_i Shapley–Shubik power. Define the player's **base influence reserve** as

R_i = C(B_i + φ_i)/2.

This term names a quantity already implicit in the reward formula. It is an operational definition, not a claim that “static reserve” is the standard textbook name for Banzhaf power. It has units of base XP under this reward conversion. Banzhaf alone describes normalized pivotal potential, before the XP conversion.

## Proposition 1: static within an encounter

Assume the roster, w, q, v and C remain fixed after combat lock, and server-owned encounter state is not externally modified. Then R_i(t)=R_i(t0) for every later time in that encounter.

Proof: for each player i and coalition S not containing i, define swing indicator d_i(S)=1 when S loses and S∪{i} wins, otherwise 0. This indicator depends only on w, q and v. Therefore b_i=Σ_S d_i(S) is fixed. Total swings and normalized B_i=b_i/Σ_j b_j are fixed. The Shapley–Shubik factorial coefficients depend only on coalition size and roster size, so φ_i is also fixed. Multiplication by fixed C preserves constancy. Current health, damage and elapsed time do not enter these formulas. QED.

Source bridge: `server/arena.js::step` assigns `influenceModel = Power.encounter(allies(), enemies)` only when the first shot changes `locked` from false to true. Later steps do not rebuild it. `encounter` reads maxHP and level, not current HP. Joining and precombat power auctions are blocked after lock. `settleCombat` reads that stored model to award XP. Rehydration preserves the same model.

## Proposition 2: normalized base total

For the nontrivial attainable monotone weighted game used by the code, Σ_i B_i=1 by normalization and Σ_i φ_i=1 because each permutation has exactly one pivotal player. Therefore

Σ_i R_i = C/2 × (1+1) = C.

This is a conserved total of **defined base reserves**, prior to eligibility, rounding and bonuses. The implementation displays floating-point shares, so general numeric checks should use a tolerance. Integer coalition counts and pivotal-permutation numerators remain exact in the model.

## Realized payout is a separate quantity

XP_i = 0 if dead, otherwise min(C, floor(R_i) + 25×critical_i).

Thus reserve constancy does not imply total XP conservation. With two equal critical survivors, each base reserve is 150 but payout is 175, totaling 350. If only A survives in a fixture with weights [27,27] and quota 30, its stored B_i and φ_i remain 0.5, its reserve remains 150, and it is no longer critical because its one-person coalition loses. It receives 150 and the dead player receives zero.

This example also shows that modeled coalition winning and actual combat victory are distinct. The quota is a designer-defined influence model. Physical combat can produce outcomes that this coalition game does not classify as a winning coalition.

## Executed evidence

`node scripts/prove-static-reserve.js` ran the actual authoritative arena with two equal players and three enemies.

| Quantity | At lock | After 120 updates |
|---|---|---|
| Weights | [27,27] | [27,27] |
| Quota | 31 | 31 |
| Health | [100,100] | [94,93] |
| Normalized Banzhaf | [0.5,0.5] | [0.5,0.5] |
| Shapley–Shubik | [0.5,0.5] | [0.5,0.5] |
| Base reserve | [150,150] | [150,150] |

The before/after stored influence models compare identically. Tests independently verify constancy after injury and persistence reconstruction, then verify that changing survival affects payout without changing the stored normalized indices. Total suite: 58 passing tests.

The derivation proves the invariant under stated assumptions. The tests provide implementation evidence. Neither establishes that the static reserve predicts human skill, real combat contribution, fairness, or a statistical correlation in observed play. Those are separate hypotheses requiring measurements and comparison models.

## Falsification conditions

The claim fails if the game recalculates w/q after injury, changes roster or voting rules after lock, spends or transfers the stored power shares, or trains a new coefficient during the encounter. Such a revision must produce a new source version and update this log. The current implementation does none of those operations. Across encounters, XP and level changes can alter a newly calculated reserve.
