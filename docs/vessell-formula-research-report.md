# Vessell formula: verified properties and contribution

Research dates: 2026-10-14; corrected case-policy review 2026-10-15.
Status: assistant-authored research draft for owner review, not a released
framework report or legal opinion. Source:
[owner-edited Vessell formula](vessell-formula.md). The 2026-10-15 correction
checks the current string before correction, separates case bits from
compliance bits, and supplies a bounded stop condition. No owner-supplied
credential-shaped example, key or derived variant was searched or included.
The owner's formula and this commentary remain distinct. Historical
2026-10-14 measurements below retain their dates and do not certify new runs.

## Bottom line

**The Vessell formula's binary complement, conjunction and masked-transform
properties are mathematically verified under their stated assumptions.**
The owner's contribution is a composed method: character-state encoding,
neutral-state separation, positional policy, current-state compliance checking,
deterministic correction, verification and a current-run interpretation.
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
capability. The corrected initial gate detects mismatches; the final gate
checks the correction's postcondition. Neither gate checks conditions outside
the declared policy.

## Contribution and completed verification

| Claim | Evidence | Status |
|---|---|---|
| Binary complement correctly represents UP/NOT DOWN on the cased domain | Both truth-table cases and the derivation below | VERIFIED within that domain |
| Product gate equals all-required-checks conjunction | Conditional proof; all 510 binary vectors of lengths 1-8 checked | VERIFIED |
| Mask transform satisfies its assigned case policy | All 9,330 binary input/mask cases of lengths 1-5 checked | VERIFIED within the tested model |
| Unmasked states are preserved and the transform is idempotent | The same 9,330 cases; direct assignment reasoning | VERIFIED within the tested model, with general conditional derivation |
| The document composes these operations into a named method | Owner-source text and supplied conversation | DOCUMENTED owner-directed formulation; wording includes assistant formalization |
| A correctly applied post-transform compliance gate returns UP | Substitution proof below | VERIFIED; compliance, not independent authentication |
| Next development measurement | Separate generated-answer, telemetry and promotion-boundary checks | Owner-led build path |

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
| `[state(c_i) = M_i]` | Iverson bracket / indicator of a proposition | A compliance indicator, not the case bit itself. Knuth's 1992 paper explicitly promotes this convention and credits Iverson's earlier work [S1]. |
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

### Current-state checking and post-transform verification

Let `I` be the valid masked ASCII-letter positions. The corrected method defines:

```text
G_M(s) = product([state(c_i) = M_i], i in I)
G_M(s) = 1 iff all masked positions satisfy their required case
G_M(T_M(s)) = product([M_i = M_i], i in I) = 1
```

The initial gate can fail. In particular, uppercase at a required-lowercase
position has case bit 1 but compliance bit 0; lowercase there has case bit 0
but compliance bit 1. The owner correction makes the initial check part of the
method, not an optional commentary alternative.

The final gate passes after a correct transform for a fixed valid mask.
That verifies policy compliance, not identity, evidence truth or authority.
For an empty mask the product is 1; this mathematical identity is separate
from the runtime evidence gate's nonempty-required-check policy.

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

These remain evidence-gate requirements, separate from the corrected
case-policy transform. Subsequent runtime integration is dated in section 10.

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

Neither runtime evidence gate applies the character-casing transform or accepts
the owner's supplied string as an authentication factor. This section records
the earlier review; the 2026-10-15 callable case-policy helpers do not change
either evidence gate.

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

| Surface | New description | Measurement boundary |
|---|---|---|
| Phase 0 output | RESEARCH OBSERVATIONS / PENDING_HUMAN_REVIEW | Truth of fetched claims, approval or an anchor |
| Five-level output | RECORDED TRIAL RESULTS / PENDING_HUMAN_REVIEW | Check results, routing measurements and bottom-up dependencies are reported separately |
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

## 10. Subsequent owner-approved runtime integration

The owner selected strict checks, local receipts and a visible game/SI gate
without changes to gameplay progression. The implementation now provides
`vessell/formula.py`, strict overlays in Phase 0 and five-level reports, a
local receipt path enabled by `--phase1`, a sanitized `/formula` endpoint and
a matching `engine/vessell-formula.js` game module. The canonical game source
and both hosted copies are synchronized. Historical analysis above describes
the earlier revision and is not rewritten as if this implementation existed
then.

An actual `--no-llm --phase1` run on 2026-10-14 opened all eleven declared
sources and passed all four read-only probes: Base Sepolia chain ID 84532,
block 48121239, Bitcoin explorer tips [971463, 971463], and calendar GET 200.
Run ID: `c55fddc1fa23402897bb1436e5f828e2`.
The strict formula returned UP and the local phase state was
LOCAL_RECEIPT_VERIFIED. Both local HTTP endpoints returned that same run
and receipt ID after rechecking the saved receipt. No model generation,
wallet, transaction, public anchor or payment occurred in this run.

SEARCH RECORD: declared URLs and read-only probes / urllib /
11 primary URLs and 4 probes / 11 source opens and 4 successful probes /
response reads capped at 600,000 bytes, truncation not measured /
primary opened yes / SOURCE OPENED and OBSERVATION RECORDED /
page claims, provider security, economic outcomes and independent chain
corroboration not checked. Agreement of two Bitcoin explorers is consistency
about one chain, not two independent chains.

The game formula endpoint is local-only; its display is observational.
HMAC keys and research text are not sent through the game status route.
At that historical revision no mission rules, autopilot promotion or
owner-source dialogue were changed. The player-game automation and framework
dialogue were subsequently removed from the player entry; retaining a
development formula helper does not reintroduce them.
The strict mathematical domain remains distinct from empirical correctness.

Integration validation: 49 final focused framework tests passed, including
signed-snapshot binding, tampering, freshness and deterministic SI formula
answers. Both Python and JavaScript check all 510 binary vectors of lengths
1-8. The complete game suite passed 198 tests, including local-only proxy
access and unchanged dialogue/progression. A browser check showed
"Vessell formula UP | Phase 1 LOCAL_RECEIPT_VERIFIED | local only, unanchored"
in the actual game channel. The SI dashboard displayed the same current run.
The local model was not ready; formula answers used measured status without
model generation, while normal dialogue retained its owner-text fallback.

The full framework run before the final two focused tests returned 1,071
passed, one skipped and the same two KEV fixture failures described above.
The final focused run covers the subsequently added answer and receipt-binding
checks; the whole suite was not rerun after those additions. No full-suite
success is claimed. Lint passed for the new Python formula module and its
direct tests.

## 11. Owner correction: check, correct, verify and stop (2026-10-15)

The owner supplied the corrected seven-part formulation and a web comparison.
The corrected [owner formula](vessell-formula.md) is authoritative for the new
method; this section is assistant-authored mathematical commentary. The
credential-shaped example was replaced with a public synthetic fixture rather
than copied to the repository or sent to a search provider.

### Domain, equivalences and termination

Assume an ASCII string, one-based positions, a fixed mask targeting only
letters and required bits in `{0,1}`. All bits and counts are dimensionless.
Let `x_i` be current case, `b_i` indicate a masked position and `m_i` be the
required case where masked (its value elsewhere is irrelevant). For letters:

```text
y_i = (1 - b_i) x_i + b_i m_i
G_M(x) = AND over masked i of NOT(x_i XOR m_i)
C_M = {s : every masked position has its required case}
G_M(s) = 1 iff s is in C_M iff T_M(s) = s
E_M(s) = sum([state(c_i) != M_i], i in I)
G_M(s) = 1 iff E_M(s) = 0
E_M(T_M(s)) = 0
```

The selector expression retains the original bit when unmasked and selects the
required bit otherwise: the Boolean multiplexer pattern. The gate is AND of
XNOR comparisons. A neutral marker is outside the binary case operation; it
does not by itself define a three-valued logic.

Each masked output letter has its required case. Each unmasked character is
unchanged. Thus `T_M(s)` belongs to `C_M` and a second transform changes nothing.
If the initial gate passes, the procedure returns without correction. Otherwise
one correction reaches the compliant set, and verification passes. The bound is
zero or one correction pass, not an iterative model/research retry policy.

Every mismatching masked letter must change case in any compliant result.
This transform changes exactly those letters. It therefore minimizes the
number of case changes among strings preserving the underlying characters
and satisfying the mask. This is a conditional combinatorial result, not an
empirical performance measurement or an error detector outside the policy.

### Established structures and primary sources

| Component | Mathematical comparison | Source scope |
|---|---|---|
| Binary case bits / complement | Boolean encoding and NOT | Direct truth-table deduction; SMT-LIB defines bitwise NOT and AND [S7] |
| Positional policy | Coordinate constraints / masked assignment | Direct deduction from the defined mask |
| Compliance product | Conjunction of equality indicators / AND of XNOR | Direct deduction; standard bit-vector operators support this expression [S7] |
| Correction | Idempotent map onto the compliant set, fixing compliant strings | Set-level comparison with `f composed with f = f` [S5]; not necessarily linear projection |
| Guarded correction and stop | Guarded program and postcondition reasoning | Comparison to guarded commands and termination in Dijkstra [S6]; not an execution of his calculus or a machine-checked proof of this code |

- **S5 — agda-unimath, Idempotent maps:**
  [canonical page](https://unimath.github.io/agda-unimath/foundation.idempotent-maps.html)
  and [primary source](https://raw.githubusercontent.com/UniMath/agda-unimath/master/src/foundation/idempotent-maps.lagda.md).
  The Idea and definition sections were opened. The library uses homotopy
  notation `f composed with f ~ f` and explicitly relates it to the classical
  set-level concept. No claim is made that this repository has formalized its
  formula in Agda or that the higher-type coherence results apply here.
- **S6 — E. W. Dijkstra, EWD 472 (1975):**
  [Guarded commands, non-determinacy and formal derivation of programs](https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD472.html).
  The abstract, introduction and guarded-command/repetition definitions were
  opened. The comparison concerns Boolean guards, assignment and termination.
- **S7 — SMT-LIB, FixedSizeBitVectors:**
  [theory declaration](https://smt-lib.org/theories-FixedSizeBitVectors.shtml).
  The sort/operation declarations and semantic definitions of bitwise NOT,
  AND and OR were opened. The selector and XNOR equations above are deductions
  from the formula, not a quotation of an SMT-LIB theorem about this method.

SEARCH RECORD: owner-supplied idempotence, guarded-command and Boolean-operator
references / direct `web_fetch` lookups / three canonical resources plus one
primary source file / four distinct resources opened / bounded excerpts;
initial Agda HTML was navigation-heavy, so the primary source's definition was
opened; SMT-LIB continued through its semantic definitions / primary opened
yes / SOURCE-ESTABLISHED for the definitions only / no exhaustive novelty,
patent search, entire-library proof check or empirical improvement study.
The supplied web summary is not independent corroboration of its citations.

### Implementation and verification boundary

`vessell/formula.py` and the game's `engine/vessell-formula.js` now provide
matching ASCII helpers: classify, check, transform and bounded correction.
They reject invalid masks and non-ASCII strings explicitly. Python uses
integer-keyed mappings; JavaScript uses `Map`. They preserve unmasked and
neutral characters and do not mutate masks.

Both suites enumerate 9,330 actual input/mask cases, lengths 1–5. They check
initial compliance versus fixed points, final compliance, idempotence,
preservation, exact mismatch/change counts and zero/one correction passes.
Additional fixtures cover empty masks, required lowercase, digits/symbols,
invalid positions/values and Unicode rejection. Existing 510 binary
current-run conjunction vectors and missing/duplicate/mixed-run rejection
remain tested separately.

Validation on 2026-10-15:

- Focused framework formula, levels, chat and receipt tests: **75 passed**.
- Full game suite after hosted-copy synchronization: **236 passed**.
- Exact Python/JavaScript result comparison: **9,333 cases passed**, comprising
  the 9,330 enumerated cases plus empty, mixed-neutral and ASCII NUL fixtures.
- Python Ruff and mypy checks passed; Pylance reported no formula-module
  diagnostics. The edited JavaScript files had no editor diagnostics.
- Full framework suite: **1,115 passed, 1 skipped, 4 failed**. Two failures
  concern existing README/review-document wording assertions; two concern KEV
  fixture provenance rows and pipeline claim counts. Those documents, tests
  and the KEV implementation are unchanged by this correction. No clean-HEAD
  baseline run was performed; the full-suite result remains failing.

Follow-up on 2026-10-15: the owner approved updating the stale tests rather
than deleting active files. README/review assertions now check the current
wording for control-plane separation, human review, source preservation and
unfinished family workflows. The synthetic KEV integration fixture uses an
explicit 2026-09-30 evaluation date so its selection does not age out; provenance
and pipeline assertions remain intact. No runtime policy or source was deleted.
The follow-up focused suite passed **43 tests**; the full framework suite
passed **1,119 tests, with 1 skipped and no failures**. Ruff passed for both
edited test files. This later run does not rewrite the earlier failing result.

Archive cleanup on 2026-10-15 separated superseded setup, demonstration and
game handoffs from active guidance. See the [archive index](../archive/README.md)
and [maintenance guide](repository-maintenance.md). Seven framework records
were preserved byte-for-byte; active links, reference discovery and source
packaging were checked. Current skills and review guides distinguish the
human-controlled campaign from development services and preserved experiments.
No original paper, owner account, licence or source/audit log was changed.

The first archive full run found a cross-repository dependency on
`scripts/autonomous-interop.js`; the game now retains a compatibility entry
point to its archived development implementation. Its framework integration
test passed after restoration. Final framework suite: **1,140 passed, 1 skipped**.
Game cleanup validation: **242 passed**, plus the C slice checks, as reported
by the game cleanup worker. New framework archive tests and changed stale
tests passed Ruff; the archive test module had no Pylance diagnostics.
Neither native/WASM deployment nor remote CI was checked in this cleanup.

This adds deterministic helpers; it does not start a loop, load framework AI
into player gameplay, change L1–L5 thresholds, alter the bottom-up gate, mint
receipts, publish a report or rewrite past runs. Evidence observations must
not be corrected into passes. Broader novelty, cryptographic security and
empirical advantage remain unestablished.
