# Savings and sustainable harvesting inside the hybrid state

Christopher R. Vessell — The Hybrid State Transition System: Discrete Event in Continuous Motion

This is a new game design rule added in this continuation. The provisional parameters are a one-quarter savings rate and a protected target equal to half the modeled base reserve. They are explicit design choices, not fitted constants or an established ecological model.

For awarded influence XP A_k, savings bank K_k, available ledger U_k, and unharvested deposit budget Y_k:

\[
R_i=C(B_i+\phi_i)/2,\quad D_k=\lfloor A_k/4\rfloor,\quad L_k=\lfloor R_i/2\rfloor,
\]
\[
H_k=\min\{h_k,Y_k+D_k,\max(0,K_k+D_k-L_k)\},
\]
\[
K_{k+1}=K_k+D_k-H_k,\quad U_{k+1}=U_k+A_k-D_k+H_k,
\]
\[
Y_{k+1}=Y_k+D_k-H_k,\quad E_{k+1}=E_k+A_k.
\]

h is a nonnegative integer requested harvest. Awards and harvests are discrete events; these balances do not grow between events. No interest, biological replenishment or income is invented from R. The same module runs co-op and tactical influence awards. Ordinary combat XP remains progression XP; the savings/available split is a bookkeeping partition of influence XP, not an additional XP award or a credit conversion. No purchase/consumption mechanic for the available ledger is supplied.

## Proof and sustainable-yield meaning

Starting at zero, K+U=E by induction: deposit and harvest cancel in the sum. H<=Y+D ensures a harvest cannot use the same replenishment twice; summing yields total harvest <= total actual deposits. H<=max(0,K+D−L) protects the target when it has been reached; if savings start below L, harvesting is zero and deposits build toward it. A changed reserve can raise the target above existing savings; the rule cannot guarantee that a new target is already funded.

This is a discrete replenishment-budget policy analogous to sustainable harvesting. It does not establish an ecological maximum sustainable yield. Without XP awards there is no new harvest budget. The locked reserve remains unchanged by savings or harvesting.

## Worked trace: static reserve into code and back out

For R=150 and a first award A=175: D=43, L=75, bank=43, available=132, unharvested yield=43. An immediate harvest returns zero because the protected target is not funded.

A second equal award gives bank=86, available=264, yield=86. Requesting 100 harvests 11, leaving bank=75, available=275, yield=75 and total earned=350. Further requests return zero until deposits exceed the protected target. The policy permits accumulated unharvested deposits to be used later, subject to that target.

engine/harvest-policy.js returns the full receipt: previous balances can be paired with next balances, award, deposit, reserve, floor, request and harvest. Reverse checks recover A=E_next−E and H=K+D−K_next, and verify K_next+U_next=E_next. Recovering the original power game from R alone is not unique; the stored weights/quota and both power indices remain necessary provenance.

Co-op logs savings_updated and savings_harvested; tactical battle savingsLog records the same receipts. Host replay retains identity, XP, level, credits, inventory and savings, while starting a fresh encounter and later recomputing its locked model. A new independent room or new campaign starts a new bank.

## Deterministic execution

The policy uses bounded integer arithmetic and explicit inputs; identical state and actions give identical receipts. Campaign gameplay now uses a seeded 32-bit LCG, q_next=(1664525 q+1013904223) mod 2^32, draw=q_next/2^32. Its state and draw count are in checkpoints. Tactical UI passes this generator into attack/endTurn. Rendering no longer advances gameplay randomness. This generator is for reproducibility, not security.

Campaign STATE LOG downloads checkpoints; LOAD STATE restores the current checkpoint, including controls, RNG, fixed-step accumulator and mission CPU reconstructed from its command sequence. The tested FPS continuation matches after restoration. Tactical battle restoration reconnects Jack to the units array. Exact replay still requires identical ordered external actions and elapsed-time inputs; sampled history alone is not that action record. Cross-browser bitwise equality of floating trigonometry is not claimed.
