# References — works VessellFramework builds on

The [author's supplied paper](claim-correction-case-study.md) is the governing
source for its six-step correction playbook. The
[source reconciliation](paper-source-reconciliation.md) distinguishes that
paper from an LLM-expanded version and later implementation literature.

## Works cited in the author's supplied paper

- Office of the Director of National Intelligence. (2015). *Intelligence
  Community Directive 203: Analytic Standards.*
  https://www.dni.gov/files/documents/ICD/ICD-203.pdf
- Doyle, J. (1979). *A Truth Maintenance System.* Artificial Intelligence,
  12(3), 231-272.
- de Kleer, J. (1986). *An Assumption-Based Truth Maintenance System.*
  Artificial Intelligence, 28, 127-162.
- Parasuraman, R., & Riley, V. (1997). *Humans and Automation: Use, Misuse,
  Disuse, Abuse.* Human Factors, 39(2), 230-253.
  https://journals.sagepub.com/doi/10.1518/001872097778543886
- Sambasivan, N., Kapania, S., Highfill, H., Akrong, D., Paritosh, P., &
  Aroyo, L. M. (2021). *"Everyone wants to do the model work, not the data work":
  Data Cascades in High-Stakes AI.* Proceedings of CHI 2021.
  https://dl.acm.org/doi/abs/10.1145/3411764.3445518

These are the author's citations, not a new independent bibliographic audit.

## Additional implementation literature (not citations in the supplied paper)

**Lamport, L. (1978).** *Time, clocks, and the ordering of events in a
distributed system.* Communications of the ACM, 21(7), 558–565.
https://doi.org/10.1145/359545.359563

*What the framework takes from it:* the happens-before relation (*a → b*).
Every rule of the correction playbook is a rule about causal paths — which
events may follow which, and what must travel the path between them. Claim
versions and status timestamps reify a claim's causal history as data, the
same move as Lamport's logical clocks. The hash-chained claim-event log
(`record_event` / `verify_event_chain`) makes that reification
tamper-evident: each event's SHA-256 commits to its predecessor's hash.

**Castello, J., Redmond, P., & Kuper, L. (2024).** *Inductive diagrams for
causal reasoning.* arXiv:2307.10484 [cs.PL]. Submitted July 19, 2023;
v2 May 14, 2024. https://arxiv.org/abs/2307.10484

*What the framework takes from it:* causal relationships are *witnessed by
the paths information follows* — happens-before modeled as paths between
events (mechanized in Agda). The framework's correction records carry
`causal_path` (the witnessed path from originating claim to correction),
dependents register *how* a claim reached them (`via`), and a negative
finding's search history is its witnessed path. This is a later software
extension, not a source for Section 4 of the author's supplied paper.

**Redmond, P., Shen, G., Vazou, N., & Kuper, L. (2022).** *Verified causal
broadcast with Liquid Haskell.* arXiv:2206.14767 [cs.PL].
https://arxiv.org/abs/2206.14767

*What the framework takes from it:* the machine-checked guarantee that
messages are never delivered in an order violating causality. The
dependents registry (`register_dependent` / `deliver_correction` /
`confirm_dependent_update`, with `CausalOrderingError` on ordering
violations) checks analogous local ordering: no dependent applies a
correction for a claim it never received, and no dependent is silently
marked corrected out of order. These tests do not reproduce the cited
machine-checked proof or establish distributed delivery guarantees.

## Intelligence tradecraft implementation context

**Office of the Director of National Intelligence. (2015).**
*Intelligence Community Directive 203: Analytic standards.*
https://donohueintellaw.ll.georgetown.edu/sites/default/files/assets/ICD%20203%20Analytic%20Standards.pdf

*What the framework takes from it:* the IC's codified analytic tradecraft
— properly describe the quality and credibility of underlying sources;
properly express and explain uncertainties. The corroboration gate
(`verify_claim`'s tier-weighted, independence-discounted root counting
with the official-record rule; verdicts as the expressed uncertainty) is
that standard as code.

**Office of the Director of National Intelligence. (2020).**
*Intelligence Community policy memorandum 2020-200-01: Standards and
procedures for revised or recalled intelligence products.*
https://www.dni.gov/files/documents/ICPM/ICPM-2020-200-01-Redacted.pdf

*What the framework takes from it:* a revision/recall notice must go to
*all recipients of the original product*. The dependents registry is the
recipient list; `deliver_correction` / `propagate_correction(...,
correction_id=)` delivering in causal order is the notice.
This memorandum is additional implementation context, not a citation in the
author's supplied paper. Coverage is limited to registered dependents.

## The framework's own paper

**Vessell, C. R. (2026).** *How an unverified sentence became system
behavior — and how to stop it.* Claim-correction case study, governing
spec for this codebase: [docs/claim-correction-case-study.md](claim-correction-case-study.md).

*What it is:* the author-reported incident (September 2026), six-step playbook,
and six mechanisms in Section 3. The supplied paper has five numbered
sections and references. It contains no Section 6, citation-verification
incident, AI-to-SI framing, or causal-order literature rewrite.
