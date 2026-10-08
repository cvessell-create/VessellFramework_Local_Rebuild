# Side log: originality search for “static reserve”

Search date: October 7, 2026 Pacific. Scope: Banzhaf-derived fixed influence, combinations with Shapley–Shubik, reward/credit assignment and game XP. This side log is separate from the main slideshow.

## Finding

**A first-ever claim is not established.** Prior work connects Banzhaf and Shapley measures to reward allocation and multiagent credit assignment. No exact match for this project's phrase “Banzhaf static reserve” or its complete encounter-lock/XP formula was located in the searches below. Failure to locate a match does not prove novelty.

The current contribution can be described as a documented game-specific implementation and interpretation: freeze the modeled power shares at combat lock, define R_i=C(B_i+φ_i)/2, then separate the base reserve from realized XP. The static invariant follows from fixed inputs; naming it does not establish a new Banzhaf theorem.

## Primary-source comparison

| Source | Established prior work | Boundary relative to Hail |
|---|---|---|
| Bachrach, Porat and Rosenschein (2013), *Sharing Rewards in Cooperative Connectivity Games* | Power indices help determine shares of network revenues and significant reliability points | Shows earlier reward-allocation use. Its network characteristic game differs from Hail's HP/level quota and encounter lock |
| Han, Lu, Michalak and Wooldridge (2022), *Multiagent Model-based Credit Assignment for Continuous Control* | A semivalue framework includes Shapley and Banzhaf to generate agent-specific credit in continuous control | Shows earlier Banzhaf credit assignment. It does not establish the same fixed game-XP reserve or its naming |
| Wang and Jia (2023), *Data Banzhaf* | Uses Banzhaf for robust data valuation and weighted-sample learning | Shows prior conversion of coalitional contributions into applied numerical values. It is not an encounter XP mechanism |

The word “Banzhaf” also appears as other authors' surname in gaming/RL papers. Such matches were not treated as evidence of the Banzhaf power index. Unrelated financial uses of “static reserve” were not treated as matches for this mechanism.

## Search record

Two search engines were used. Exact and broader queries included:

- `"Banzhaf" "static reserve"`
- `"Banzhaf" game reward credit assignment reinforcement learning`
- `"Banzhaf" "Shapley" average rewards game`
- `"Banzhaf" videogame experience points`
- `"Banzhaf" "Shapley" "convex combination"`
- `"Banzhaf" "experience points"`
- `"Multiagent Model-based Credit Assignment for Continuous Control" pdf`

Accessible primary abstracts and the Han et al. full paper were checked. This is a targeted literature search, not an exhaustive literature/systematic review or patent novelty determination. No priority, first use or patentability claim is made.

## Wording suitable for the presentation side log

“Vessell's Hail implementation interprets an encounter-fixed blend of normalized Banzhaf and Shapley–Shubik power as a static base influence reserve. This project documents the formula, proves its within-encounter invariant under fixed inputs, and traces its conversion into game XP. Prior research already applies coalitional power and semivalues to reward allocation and credit assignment. The originality of this exact game-specific combination remains unestablished.”

## Citations

Bachrach, Y., Porat, E., & Rosenschein, J. S. (2013). Sharing rewards in cooperative connectivity games. *Journal of Artificial Intelligence Research, 47*, 281–311. https://doi.org/10.1613/jair.3841 . Accessible author manuscript: https://arxiv.org/abs/1402.0572

Han, D., Lu, C. X., Michalak, T., & Wooldridge, M. (2022). Multiagent model-based credit assignment for continuous control. *Proceedings of the 21st International Conference on Autonomous Agents and Multiagent Systems*. Author manuscript submitted December 27, 2021: https://arxiv.org/abs/2112.13937 . Full text: https://arxiv.org/pdf/2112.13937

Wang, J. T., & Jia, R. (2023). Data Banzhaf: A robust data valuation framework for machine learning. *Proceedings of Machine Learning Research, 206*, 6388–6421. https://proceedings.mlr.press/v206/wang23e.html

For your own work, cite the dated project record as an unpublished software/design note until a persistent release is published. Do not present the existing upstream Banzhaf index as newly invented, or use this side log as evidence of first-ever priority.

Provisional self-citation: Vessell, C. R. (2026, October 7). *Hail to the Analyst: Static base influence reserve, source audit and execution log* [Unpublished software design note]. This package. The GitHub main commit records the pre-existing reward formula; the reserve interpretation and trace instrumentation belong to this continuation and have not been pushed to that remote.
