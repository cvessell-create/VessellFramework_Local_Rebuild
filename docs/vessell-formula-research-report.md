# Vessell formula: verified properties and contribution

Research date: 2026-10-14.
Status: assistant-authored research draft for owner review, not a released
framework report or legal opinion. Source:
[owner-edited Vessell formula](vessell-formula.md), read before the filename
and code-fence edits. No password, key or derived variant was searched or
included. The owner's formula and this commentary remain distinct.

## Bottom line

**The Vessell formula's binary complement, conjunction and masked-transform
properties are mathematically verified under their stated assumptions.**
The owner's contribution is a composed method: character-state encoding,
neutral-state separation, positional policy, deterministic transformation,
compliance checking and a current-run interpretation for SI-loop checks.
Building on established Boolean logic does not invalidate that contribution.

The earlier review put too much emphasis on worldwide originality as though
it were necessary to verify or use the method. It is not. Mathematical
correctness, authorship, usefulness and worldwide priority are separate
questions. This revision closes verification of the properties actually
proved and checked; it does not require an endless originality search.
Worldwide priority and new cryptographic security are not claimed here.

The method stacks up well as a readable, deterministic casing convention and
an all-required-checks predicate. It does not, on its own, supply cryptographic
authentication, independent evidence, calibrated confidence or demonstrated SI
capability. Its most important limitation is the post-transform gate: it checks
conditions the transform has already made true.

## Contribution and completed verification

| Claim | Evidence | Status |
|---|---|---|
| Binary complement correctly represents UP/NOT DOWN on the cased domain | Both truth-table cases and the derivation below | VERIFIED within that domain |
| Product gate equals all-required-checks conjunction | Conditional proof; all 510 binary vectors of lengths 1-8 checked | VERIFIED |
| Mask transform satisfies its assigned case policy | All 9,330 binary input/mask cases of lengths 1-5 checked | VERIFIED within the tested model |
| Unmasked states are preserved and the transform is idempotent | The same 9,330 cases; direct assignment reasoning | VERIFIED within the tested model, with general conditional derivation |
| The document composes these operations into a named method | Owner-source text and supplied conversation | DOCUMENTED owner-directed formulation; wording includes assistant formalization |
| A correctly applied post-transform compliance gate returns UP | Substitution proof below | VERIFIED; compliance, not independent authentication |
| The method improves research outcomes or demonstrates SI capability | No comparative outcome study performed | Not claimed |

Validation on 2026-10-14 used Ruby to enumerate binary state arrays and masks
whose entries are unmasked, zero or one. For each pair it checked assigned
positions, preservation of unmasked states and a second application of the
transform. The case count is `sum(6^n, n=1..5) = 9,330`.
This is a check of the formal model, not a test of a deployed casing
implementation, Unicode behavior or cryptographic security.

A separate four-case illustrative predicate check covered all-pass, failure,
unknown and empty input. It passed, but that predicate is a proposed
fail-closed policy, not a change to the existing runtime.

## 1. Comparison with established work

| Formula component | Mathematical counterpart | Assessment |
|---|---|---|
| `UP = 1 - DOWN` | Boolean complement, with values in `{0,1}` | Established identity, not new. Only valid where UP and DOWN are exhaustive opposites. |
| `[y_i = M_i]` | Iverson bracket / indicator of a proposition | Established notation. Knuth's 1992 paper explicitly promotes this convention and credits Iverson's earlier work [S1]. |
| Product of binary indicators | Logical conjunction / AND | Established: a finite product of zeros and ones equals one exactly when every factor equals one. [S1] illustrates products of indicators for combined conditions. |
| Setting selected case bits to a mask | Deterministic assignment / projection onto constrained states | An ordinary assignment operation. Unicode defines standard case conversion, but not this specific workflow [S2]. |
| `NOW = UP` for current-run checks | Time-indexed conjunction | A workflow naming convention; evaluating a predicate at a time is not a new logic operation. |
| String plus mask called two factors | Two computational inputs | Not automatically two distinct authentication factors under NIST's definition [S3]. |
| HMAC receipt verification | Keyed message authentication | Separate established cryptography defined by RFC 2104 [S4]; its strength is not supplied by the casing formula. |

All states and indicators here are dimensionless. They are not physical units,
probabilities, confidence scores or SI levels. Indicator multiplication needs
no statistical-independence assumption; multiplying probabilities would.

## 2. Checkable derivations

### Boolean complement

For a cased letter, define `D` as its lowercase indicator and `U` as its
uppercase indicator. Under the assumption that exactly one applies:

```text
D ∈ {0,1}
U = 1 - D

D = 0  =>  U = 1
D = 1  =>  U = 0
```

This is a valid Boolean complement identity. It is not an empirical inference.
If the state is neutral or unknown, NOT DOWN does not imply confirmed UP.
The original formula skips neutral characters; an implementation must preserve
that boundary rather than substitute zero for missing information.

### Indicator product

Let `[P]` be one when proposition `P` is true and zero otherwise:

```text
[NOT P] = 1 - [P]
[P AND Q] = [P] × [Q]

G = product(q_j, j = 1,...,m),  q_j ∈ {0,1}
G = 1  if and only if every q_j = 1
```

Proof: a zero factor makes the product zero; with no zero factors every factor
is one, so the product is one. This is the same truth function as `all(checks)`,
not evidence that the checks measure the intended property.

### Why the post-transform gate always passes

Let `I` be the valid masked letter positions. The document defines:

```text
y_i = M_i                         for every i ∈ I
G_after = product([y_i = M_i], i ∈ I)
        = product(1, i ∈ I)
        = 1
```

For valid inputs this is true by construction, regardless of the original
case bits. It can test whether an implementation followed the transform, but
cannot independently authenticate the input or establish that research passed.

A distinct, optional check of the ORIGINAL input would be:

```text
G_before = product([state(c_i) = M_i], i ∈ I)
```

That detects initial mask compliance. It is commentary, not a replacement for
the owner formula, and even this check is not proof of identity or authority.

### Idempotence and information loss

For a fixed valid mask, the transform `T_M` is idempotent:

```text
T_M(T_M(s)) = T_M(s)
```

Applying the same required case twice adds no change. If `r` distinct cased
positions are overwritten, the output no longer distinguishes the `2^r`
possible original case assignments at those positions. The transform is
therefore generally many-to-one, not an invertible encryption operation.
This counts possibilities; it is not a measured entropy or security claim.
Knowing the string alone can determine the output for some masks or inputs,
so the original statement that neither input alone gives the result is not
a universal security guarantee.

## 3. Where it stacks up well, and where it does not

| Criterion | Finding | Limitation |
|---|---|---|
| Clarity | UP/DOWN is an accessible label for binary states. | Lowercase DOWN is a character state, not necessarily a failed requirement; a required lowercase letter passes its comparison. |
| Determinism | Same input and valid mask produce the same output under a declared case policy. | Locale, Unicode version and indexing policy must be specified outside simple ASCII. |
| Computation | One scan for classification/transformation and one scan for checks: linear work in characters plus checks. | This is analytical complexity, not a measured benchmark. |
| Strict gating | Binary AND rejects a known failed required check. | It cannot establish that a check is relevant, honest, complete or independently corroborated. |
| Cryptography | Can be a preprocessing or policy predicate used alongside a separate cryptographic system. | No demonstrated encryption, key derivation, attack resistance or new authentication primitive. |
| Multifactor claim | Two inputs can express a two-input computation. | NIST requires distinct authentication factors; two memorized inputs alone do not establish that [S3]. |
| Blockchain | Can summarize results of independently specified read-only checks. | No anchoring, transaction, consensus or timestamp proof follows from the equation. |
| Originality | Owner-specific presentation and integration can be documented. | Mathematical novelty and worldwide priority are not established by this search. |

Unicode's default algorithms include full and context-dependent mappings [S2].
A rigorous version should either declare ASCII letters with character-indexed
positions, or define Unicode code-point/grapheme indexing, locale, titlecase,
uncased letters and multi-character mappings. The current formula does not
fully specify these cases.

## 4. Missing inputs, empty sets and freshness

The current mathematical product over an empty mask conventionally equals one.
Likewise, `all([])` returns true. That means no checks can produce an apparent
pass unless emptiness is handled separately. No such policy is specified in
the owner formula.

For a real research gate, consider these explicit, optional requirements:

- Nonempty, predeclared required-check IDs; received IDs must match them.
- Missing, neutral and unknown results must not count as confirmed UP.
- All checks bind to the same run and declared source/input revision.
- Specify acceptable observation age; the word NOW alone has no time bound.
- Keep failures and source limits; passing retrieval is not evidence truth.
- Human review, phase authorization and execution remain separate decisions.

These are proposed specifications, not changes to runtime behavior.

## 5. Actual implementation versus earlier chat claims

Code inspected at working-tree base `04d4eda`, including uncommitted additions:
[Phase 0 gate](../vessell/phase0_loop.py) and
[receipt verifier and gate](../vessell/receipts.py).

The Phase 0 implementation combines FIVE policy checks. Its source condition
requires at least 80% of sources to open, not all eleven. For eleven sources,
nine suffice (`9 >= 8.8`). Its probe condition requires all supplied probes
to succeed; it does not independently require four probes. With `--no-llm`,
missing generated roadmap steps are allowed by that condition.

Consequently, the prior chat's equation of the implemented gate with a strict
AND over all 15 source/probe observations was inaccurate. A particular run can
have all 15 successes without the implementation requiring all 15. The
formula's date-specific success sentence remains historical text, not a fresh
observation performed in this review.

The receipt gate returns UP when the verifier supplies an empty problem list.
File-content checks are optional in the verifier. Passing without those checks
does not establish that current files still match the receipt. An HMAC tag
authenticates a message relative to possession of the shared key, not the
truth of its statements or an independently certified signing time [S4].

Neither runtime gate applies the character-casing transform or accepts the
owner's supplied string as an authentication factor. This review edits
documentation only; it does not modify either gate.

## 6. Sources opened and source-access limits

- **S1 — Donald E. Knuth, Two Notes on Notation (1992):**
  [author's article via arXiv HTML](https://arxiv.org/html/math/9205211),
  section 1 and equations (1.6)-(1.7), opened and read. Establishes the
  indicator convention and illustrated conjunction products; it does not
  assess Vessell's workflow.
- **S2 — Unicode Standard 17.0, chapter 3:**
  [section 3.13, Default Case Algorithms](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-3/),
  relevant passages extracted from the official HTML and read, especially
  3.13.2. Supports case-mapping boundary requirements, not workflow originality.
- **S3 — NIST SP 800-63B-4:**
  [introduction / authentication assurance levels](https://pages.nist.gov/800-63-4/sp800-63b.html)
  and [authenticator requirements](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/),
  introductory AAL2/AAL3 and password sections opened and read. Distinct
  authentication factors are required; full conformance was not assessed.
- **S4 — Krawczyk, Bellare and Canetti, RFC 2104 (1997):**
  [HMAC: Keyed-Hashing for Message Authentication](https://www.rfc-editor.org/rfc/rfc2104.html),
  abstract and section 1 opened and read. Establishes shared-key message
  authentication, not a new formula or audit of this implementation.
- Supplementary explanatory sources opened: Wolfram
  [Iverson Bracket](https://mathworld.wolfram.com/IversonBracket.html) and
  [Boole documentation](https://reference.wolfram.com/language/ref/Boole.html).
  LibreTexts was also opened but the returned excerpt consisted of notation
  setup; substantive claims from that excerpt were not adopted.

Only the listed sections were read, not entire standards or every cited paper.
The complement, idempotence, tautology and information-loss results above are
direct conditional derivations; they do not depend on a search summary.

## 7. Search records and originality limits

Tool: `web_search` (synthesized web results), followed by `web_fetch` or official
HTML retrieval. Counts below are distinct cited URLs returned by the tool,
not total indexed matches. Search engine totals/caps were NOT_AVAILABLE.
No search summary was treated as primary confirmation.

| Query / scope | Returned URLs | Primary opened | Result / limits |
|---|---:|---|---|
| Boolean complement, indicator products, masks and Unicode (broad initial query) | 0 | No | NOT FOUND IN SCOPE; tool returned no relevant results. |
| Combined exact-label originality query (`UP = NOT DOWN`, `NOW = UP`, `Vessell formula`) | 0 | No | NOT FOUND IN SCOPE; not evidence of uniqueness. |
| Boolean negation as `1-x`, conjunction as multiplication, Iverson / Knuth | 6 | Yes: S1 | Established prior components; returned explanatory leads also included secondary pages. |
| `UP = NOT DOWN` formula | 2 | No | Generic logic pages, not an identified publication of this workflow. Tool broadened the phrase; exact-match coverage not guaranteed. |
| `Vessell formula` mathematics | 6 | No | Unrelated vessel-volume pages; no relevant workflow match in returned citations. |
| Knuth, Two Notes on Notation, arXiv | 1 | Yes: S1 | Primary author article opened; confirms prior indicator notation. |
| NIST authentication factors and HMAC (source discovery) | NOT_COUNTED | Yes: S3, S4 | Relevant official sources subsequently opened directly; not an originality search. |

Limit-hit status: NOT_AVAILABLE for web search; fetched page excerpts were
bounded and sometimes truncated as described above. Not checked: patent
databases, subscription mathematics indexes, unpublished work, private
repositories, trademarks, all languages, exhaustive worldwide prior art or
legal rights. The tool's query rewriting further limits exact-name searches.

The search did not settle worldwide priority. No worldwide-uniqueness or new
cryptographic-primitive claim is made in this document, so that unanswered
question is not a blanket failure status for the method. The mathematical
claims are resolved by the proofs and checks above.

## 8. Closure and optional development

Keep Vessell formula as the name of the owner-directed method. Describe it as
a binary casing-mask transform plus a current-run conjunction gate, built from
established mathematics. **Verification of the stated mathematical properties
is complete; no repeated web search is required to keep that conclusion.**
If a future claim concerns improved outcomes, specify an independently
checkable improvement and compare it against ordinary mask assignment and
`all(required_checks)` on held-out cases, including missing data, stale runs,
invalid masks and Unicode boundaries. No empirical improvement study was
performed here, and this review does not authorize Phase 1 or report release.

The owner describes the earlier repeated labels as a "doom loop" and reports
concern that they were injected. That account is preserved as an owner-reported
concern. This review establishes no outside actor or injection mechanism.
The assistant's overbroad framing is corrected here without assigning an
unsupported cause. This task changes the documents only; it does not stop,
restart or change any background process.

## 9. Claim-specific status correction across both projects

On 2026-10-14 the owner authorized correction of overbroad labels in both
projects. Canonical identities were confirmed with `gh repo view`:
`cvessell-create/VessellFramework_Local_Rebuild` and
`cvessell-create/hail-to-the-analyst`. This is a local working-tree correction,
not a remote publication.

The framework search returned 28 matching non-ignored files before this
correction. The game search returned three README copies, each referring to
unused flood-wall statistics. Search scope: the two project directories,
excluding Git internals and ordinarily ignored content. A separate count-only
search of framework `outputs/` and `private/` found seven and one matching
files respectively. No raw private record contents were collected.
Game `outputs/` was absent. Files outside these project directories,
read-only chat attachments, other branches and remote file contents were
not searched or rewritten. Result counts describe matching files, not claims.

Corrected active SI-loop labels:

| Surface | New description | What it does not establish |
|---|---|---|
| Phase 0 output | RESEARCH OBSERVATIONS / PENDING_HUMAN_REVIEW | Truth of fetched claims, approval or an anchor |
| Five-level output | RECORDED TRIAL RESULTS / PENDING_HUMAN_REVIEW | General answer correctness or superintelligence |
| Idea output | GENERATED DESIGN PROPOSAL / PENDING_HUMAN_REVIEW | Approved design or empirical benefit |
| Sparring output | GENERATED COACHING / PENDING_HUMAN_REVIEW | Model training or validated improvement |
| Dashboard container | RECORDED LOOP ACTIVITY | Promotion of each enclosed record's status |

The formula's proven properties do not convert external web snippets,
deployment status, legal research gaps, unconfirmed identity matches or
historical observations into established facts. Those remaining scoped
statuses are retained. The game's flood-wall-statistics statements are also
retained: there is no formula-related error in those three matches.
Existing output files, private records and append-only history are not
retroactively relabeled. New runs use the new descriptions; old records
retain their provenance. No autonomous research loop was restarted.

The correction preserves numerical gates, schema keys and human review.
It does not replace the five-level threshold or Phase 0's 80% policy with
strict conjunction. Forty-seven targeted regression tests passed covering
chat, levels, sparring, ideas, Phase 0 and receipts. Formula rechecking is
bounded to declared binary inputs and masks, not repeated model generation
until a preferred answer appears. Test failures must remain failures.

The repeated formula-model check completed twice: each round covered 9,330
input/mask cases and 27,990 compliance, preservation and idempotence checks,
all passing. This verifies that formal model, not the entire repository.

The full framework suite returned **1,066 passed, 1 skipped, 2 failed**.
Both failures are in `tests/test_doctrine_reconciliation.py`: KEV provenance
rows and pipeline claim counts were empty. The fixture uses a fixed
`dateAdded` of 2026-09-29 while the unchanged KEV filter uses the current date
and a lookback window. Neither that test file nor the KEV source was changed
in this correction. A baseline comparison was not performed; the full-suite
result remains failing and is not relabeled UP.
