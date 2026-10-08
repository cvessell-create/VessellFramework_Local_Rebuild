# The Hybrid State Transition System: Discrete Event in Continuous Motion

Christopher R. Vessell — Hail to the Analyst

## Whole-state equation

The engine is a sampled hybrid system: continuous-valued positions, angles, health and timers evolve alongside discrete modes, shots, deaths, auctions and rewards. “Continuous motion” describes the modeled quantities; the implementation advances them in finite steps.

\[
 S_{k+1}=F(S_k,a_k,\Delta t_k,\tau_k,\xi_k),\qquad y_k=h(S_k).
\]

Here S includes the active mode, geometry, players, enemies, controls, timers, progression, economy, encounter model and subsystem state. a is an ordered external action; tau is wall-clock time; xi represents random draws wherever used. y is the player-facing observation. This is an operational model of the inspected implementation, rather than a single smooth differential equation.

## Motion from formula to code

For accepted forward f, strafe s and turn r, define n=max(1,sqrt(f²+s²)). Authoritative co-op motion updates rotation first:

\[
 \theta'=\operatorname{atan2}(\sin(\theta+2r\Delta t),\cos(\theta+2r\Delta t)),
\]
\[
 d_x=2.25\Delta t(f\cos\theta'-s\sin\theta')/n,\quad
 d_y=2.25\Delta t(f\sin\theta'+s\cos\theta')/n.
\]

Position is C_grid(x,y,d_x,d_y): the engine's bounded collision substeps and separate axis acceptance with radius 0.18. It is not simply unconstrained integration. engine/state-model.js calls the actual engine/core.js turn/move operations, preserving collision order. Co-op inputs expire after 250 ms. Campaign speed and turn constants differ and remain separate in index.html.

## Discrete events and reset equations

| State or event | Transition | Source |
|---|---|---|
| Cooldown | c'=max(0,c−dt); accepted player fire resets c to 0.3 | server/arena.js |
| Player shot | nearest visible live enemy within angle 0.1 and distance 12; damage=min(25+5 power,enemy HP) | server/arena.js |
| Enemy hit | subtract 5+enemy level from target HP through the damage handler; cooldown resets to 1.2 | server/arena.js |
| First shot | lock roster and store encounter weights, quota and power indices | server/arena.js, js/power-index.js |
| Victory/death | guards switch phase and realize eligible XP once | server/arena.js |
| Sealed bids | collect valid values, then allocation/payment reset; timeout cancels without transfer | server/arena.js, engine/fair-division.js |
| Campaign/tactical mode | title, briefing, tactical, play, pause, dead and victory control which update runs | index.html, js/tactical-ui.js |

Player update order, then enemy updates, then terminal guards is part of F. Reordering events can change results. Authoritative steps reject invalid dt; the fixture uses 1/60 second. Campaign fixed-step catch-up is bounded and can drop excess elapsed time.

## Static reserve as one state block

At encounter lock, w_i=ceil(maxHP_i/4)+2 level_i and the enemy-dependent quota define a weighted voting game. Its normalized Banzhaf B_i and Shapley–Shubik phi_i define

\[
 R_i=C(B_i+\phi_i)/2,\qquad R_{i,k+1}=R_{i,k}
\]

through that locked encounter. Thus reserve is a constant coordinate of S while health and position change. When both indices normalize to one, sum R_i=C. Realized XP applies survival, floor, critical bonus and per-player cap; it need not sum to C. Later XP can change level and later encounter weights. This proves the conditional invariant, not a measure of actual contribution.

## Whole state versus observations

The complete serialized co-op kernel is arena.exportState(), including accepted inputs, timestamps, sealed bids and session identity. Restoring it with the same clock and subsequent ordered actions reproduces the tested next transition. arena.dynamicState() is a privacy-safe projection: it removes bearer tokens and unsettled bids. It cannot by itself replay hidden actions.

The solo snapshot getter HailCampaignState captures campaign entities, map, doors, controls, progression, tactical battle and mission command log, seeded RNG, fixed-step accumulator and savings. HailCampaignLog stores up to 180 snapshots, once per second and on mode changes, plus current state. Gameplay randomness is now seeded and checkpointed. LOAD STATE restores gameplay, fixed-step clock and mission CPU command history; a tested FPS continuation matches. Sampled history alone is insufficient for action replay. DOM and audio resources are presentation infrastructure outside the gameplay-state projection. Separate workbench games are separate kernels, not automatically coupled campaign state.

## Backward analysis and verification

A finite abstraction can use V_terminal=reward and V_k(s)=max_a E[V_{k+1}(F(s,a,...))], with the appropriate acting player's utility. This does not prove an optimal policy for the entire live, continuous-state multiplayer game. That requires specified horizon, action set, opponent policy and randomness.

Verified here: motion matches the authoritative update; diagonal input does not increase free-space speed; public projections omit session tokens; a serialized state restores the same tested next state; locked reserves remain fixed despite injury. These are local invariants and reproducibility checks. Global stability, fairness and exhaustive reachability have not been proved.

See executed-state-log.json, static-reserve-proof.json, tests/state-model.test.js, the recovered branch records and the weighting ledger. Originality research remains in originality-side-log.md.

The subsequent savings extension is specified in sustainable-yield-policy.md. Its bank/yield/available balances are additional discrete state coordinates; it does not change locked power shares.
