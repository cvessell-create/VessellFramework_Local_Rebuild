# Static Reserve Research Log

Author/project owner: Christopher R. Vessell

Recorded: October 7, 2026 Pacific

Status: owner-designated research focus. The owner confirmed strong interest in preserving the explanation and investigating its implications. This log records the interpretation and evidence without elevating it into an established novelty or empirical-performance claim.

## Owner-confirmed idea

A player's stored potential influence can be interpreted as a static base reserve. The encounter's weights, quota, Banzhaf and Shapley–Shubik values freeze at the first shot. Later damage does not recalculate those shares. Final payout reads the stored shares and applies current survival and coalition criticality.

## Full mathematical reconstruction

For players N and coalition S, define the weighted game

v(S) = 1 if sum of weights in S ≥ q and every required veto holder belongs to S, otherwise 0.

w_i = ceil(maxHP_i/4) + 2 level_i.

q = ceil(sum_i w_i × [0.5 + min(0.4, totalEnemyMaxHP/2000)]).

For S not containing i, marginal swing d_i(S)=v(S∪{i})−v(S). In this monotone game d_i(S) is either 0 or 1.

b_i = sum over S not containing i of d_i(S).

Absolute Banzhaf β_i = b_i / 2^(n−1).

The reward uses normalized Banzhaf B_i = b_i / sum_j b_j.

Shapley–Shubik φ_i = sum over S not containing i of [|S|!(n−|S|−1)!/n!] d_i(S).

Mean modeled power a_i = (B_i+φ_i)/2.

Static base reserve R_i = C a_i = C(B_i+φ_i)/2.

C=300 for an ordinary influence encounter. The reusable model allows C=500 for its boss flag.

Realized XP_i = 0 for a nonsurvivor. For a survivor, XP_i = min(C, floor(R_i)+25 critical_i), where critical_i=1 only if the final surviving coalition wins and removing i makes it lose.

New level = max(previousLevel, min(5, 1+floor(cumulativeXP/300))) in the co-op arena. The next encounter can derive different w_i from this changed level. The current encounter's reserve remains locked.

## The backward reconstruction

Given a realized XP award, locate the `xp_realized` event. Read survival, criticality, reserve and cap. Locate the earlier `reserve_locked` event. Read both normalized power indices and their coalition inputs. Read the initial participant maxHP and level. Re-evaluate the weight formula, quota, swing counts, factorial pivotal counts and base reserve.

This reconstructs the computation from its recorded inputs. XP alone cannot uniquely recover those inputs: floor, cap and survival mapping are many-to-one. The reverse trace requires provenance rather than an invented inverse function.

## Static proof

Fixed w, q, veto set and roster make every v(S) and d_i(S) fixed. Their sums, normalization and factorial averages are fixed. With fixed C, R_i(t)=R_i(t0) after encounter lock. Also sum_i B_i=1 and sum_i φ_i=1 for the nontrivial monotone game, giving sum_i R_i=C before rounding and payout adjustments.

This proves a modeled base reserve under the stated assumptions. It does not prove that the reserve equals actual physical contribution or intelligence. That additional relationship would require observed data and a defined comparator.

## Concrete execution

The actual arena locked weights [27,27] at quota 31 with C=300. Both normalized indices were [0.5,0.5]. Base reserves were [150,150]. After 120 simulation updates, health changed from [100,100] to [94,93], while the full stored influence model stayed identical.

A separate declared fixture at quota 30 gives two surviving critical players 175 XP each. These awards total 350, demonstrating that the normalized base reserve total of 300 is distinct from final XP with bonuses. When only A survives in that fixture, its base reserve stays 150, A receives 150, and the dead player receives 0.

## Code and game-wide logging

- `js/power-index.js`: `encounter`, `analyze`, `critical`, `reward` implement the existing math.
- `engine/static-reserve.js::fromModel`: exposes the reserve already implicit in the reward formula.
- `engine/weight-trace.js`: logs forward formulas and reverse dependencies without changing coefficients.
- `server/arena.js`: logs join, accepted inputs, reserve lock, health changes, hits, encounter outcome, realized XP and economy settlement.
- Hosted multiplayer UI shows each fixed base reserve after lock and offers `Download match log`.
- Server retains up to 1,000 events and reports dropped-event count. Browser observation history retains up to 3,000 snapshots. These bounded logs cover the encounter lifecycle but are not an unlimited record of every tick.
- Private sealed bid values stay hidden until settlement. Exported match logs contain no bearer session tokens.

## Verification and continuation

64 tests pass, including reserve invariance under injury, persistence restoration and the distinction between reserve and payout. `static-reserve-proof.json` stores the executed result. `static-reserve-proof.md` contains the formal conditional proof. `executed-weight-log.json` and `weighting-ledger.md` document weighting in both directions. `branch-log.md` preserves the recovered design history.

The originality side log contains prior-art citations and search scope. No “first ever” claim is established. A game-specific implementation, defined interpretation, proof and transparent provenance can be attributed to this project without claiming invention of Banzhaf or Shapley–Shubik power.

Research questions for later work: Does frozen modeled influence predict observed contribution? How does a dynamically recalculated model differ? Which treatment handles health loss and survivor eligibility coherently? What reward incentives arise from critical bonuses? Those remain questions, not results in this log.
