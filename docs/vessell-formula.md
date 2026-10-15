# Vessell formula — corrected case-policy transform

Owner correction supplied 2026-10-15. Sections 1–7 record the corrected method;
the implementation notes and [research commentary](vessell-formula-research-report.md)
are separate. A required lowercase letter passes. A mismatch fails.

## 1. Character state

For a string \(s=c_1c_2\ldots c_n\), using ASCII letters:

\[
state(c_i)=
\begin{cases}
1 & \text{if uppercase}\\
0 & \text{if lowercase}\\
\bot & \text{otherwise}
\end{cases}
\]

For letters only:

\[
UP(c_i)=state(c_i),\qquad DOWN(c_i)=1-state(c_i)
\]

Thus \(UP(c_i)=1-DOWN(c_i)\). Neutral characters remain unchanged.

## 2. Required-case mask

Let \(I\) contain the chosen letter positions. Define:

\[
M_i\in\{0,1\}\qquad(i\in I)
\]

Here, \(1\) requires uppercase and \(0\) requires lowercase.

## 3. Check the current string

Define each compliance check:

\[
k_i(s)=[state(c_i)=M_i]
\]

Then:

\[
\boxed{G_M(s)=\prod_{i\in I}k_i(s)}
\]

Brackets equal 1 when true and 0 when false. Therefore:

\[
G_M(s)=
\begin{cases}
1 & \text{all masked positions comply: PASS}\\
0 & \text{at least one mismatch: FAIL}
\end{cases}
\]

**A required lowercase letter passes. A mismatch fails.**
With no masked positions, the empty product equals 1.

## 4. Correct the string

\[
T_M(s)_i=
\begin{cases}
uppercase(c_i) & i\in I,\ M_i=1\\
lowercase(c_i) & i\in I,\ M_i=0\\
c_i & i\notin I
\end{cases}
\]

## 5. Repeat and stop

Starting with \(s^{(0)}=s\):

\[
\boxed{
\begin{cases}
\text{STOP and return }s^{(t)} & G_M(s^{(t)})=1\\
s^{(t+1)}=T_M(s^{(t)}) & G_M(s^{(t)})=0
\end{cases}}
\]

For a fixed valid mask:

\[
G_M(T_M(s))=1,\qquad T_M(T_M(s))=T_M(s)
\]

The process therefore requires **at most one correction pass**, followed by
verification.

## 6. Example

With \(I=\{1\}\) and \(M_1=0\), this public, non-secret fixture illustrates
the same uppercase-to-required-lowercase correction:

```text
Initial:    Review    G = 0 → FAIL
Corrected:  review    G = 1 → PASS → STOP
```

Implementation note: the owner-supplied credential-shaped example is not
copied into source, tests or research queries. Positions are one-based.

## 7. Current-run interpretation

If retaining “NOW = UP,” define UP here as overall compliance:

\[
\boxed{NOW=UP\iff G_M(s^{(t)})=1}
\]

This uses only the current run's checks. It describes a deterministic
correction-and-verification process; it does not by itself establish a
cryptographic primitive.

---

## Implementation notes (assistant-authored)

The implementation accepts ASCII strings only and a fixed mask of one-based
letter positions mapped to integer 0 or 1. Invalid positions, neutral targets,
non-binary values and non-ASCII strings raise explicit errors. Unicode case
conversion is outside this contract. Unmasked positions, including digits and
symbols, are preserved. Masks are not mutated.

| Operation | Python: `vessell/formula.py` | JavaScript: `engine/vessell-formula.js` in the game repository |
|---|---|---|
| Character state | `case_state(character)` | `caseState(character)` |
| Current-string compliance | `case_gate(text, mask)` | `caseGate(text, mask)` |
| Case transform | `transform_case(text, mask)` | `transformCase(text, mask)` |
| Check → correct → verify → stop | `correct_case(text, mask)` | `correctCase(text, mask)` |

Python masks are mappings such as `{1: 0}`; JavaScript masks are
`new Map([[1, 0]])`. The correction result contains `text`, `initial_product`,
`product`, `state` (`PASS`), `mismatches_before` and `correction_passes` (0 or 1).
These are callable helpers, not a background loop or a player-game feature.

### Separate current-run evidence gate

The existing `evaluate(required, observations, run_id)` contract remains
`vessell-formula/v1`. Its `passed` values mean independently supplied check
compliance, **not character case**. A case bit of 0 can satisfy a lowercase
policy; an observation whose `passed` is false still fails the evidence gate.
Never case-correct evidence, model answers or failed observations into passes.

The empty case mask passes by the empty-product identity. The evidence gate
still requires nonempty, unique declared IDs, matching observations and the
same run ID. Empty, missing, duplicate, unknown or mixed-run records remain DOWN.
This distinction is intentional, not a contradiction.

L1–L5 posterior thresholds, bottom-up promotion, formula-answer routing,
receipts, human review and execution permission are unchanged. See
[the two judgments and answer routes](si-loop-development-judgments.md) and
[the Phase 0/1 instructions](phase0-restart-and-phase1-roadmap.md).

### Contribution and verification scope

The owner-directed contribution combines representation, policy, current-state
checking, correction and verification into an understandable procedure. Its
constituent operations are established mathematics. Under the stated domain,
the transform satisfies the policy, preserves unmasked characters and reaches
a fixed point after at most one correction pass. Broader novelty and
cryptographic security remain unestablished.

The Python and JavaScript regression suites enumerate 9,330 input/mask cases
of lengths 1–5, including required lowercase; they also test empty masks,
neutral characters, invalid inputs and all 510 nonempty binary evidence vectors
of lengths 1–8. See the [verification report](vessell-formula-research-report.md)
for the conditional derivations and primary-source comparisons. Historical
run outcomes are not rewritten by this correction.
