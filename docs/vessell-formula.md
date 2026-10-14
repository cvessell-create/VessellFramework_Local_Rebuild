# Vessell formula

## Verification and contribution

**MATHEMATICALLY VERIFIED WITHIN THE DECLARED BINARY DOMAIN.**
This status concerns the equations and properties below, not worldwide
priority, cryptographic security or the truth of research inputs.

The owner's contribution builds on Boolean logic by composing:

1. A character-state representation with an explicit neutral state.
2. A positional mask expressing the desired case policy.
3. A deterministic transform applying that policy.
4. A product of requirement comparisons checking output compliance.
5. A current-run interpretation of the same conjunction for SI-loop checks.

The contribution is the organized method and its intended application, not
a claim to have invented Boolean complement or conjunction. The casing
compliance gate and the independently observed research gate are distinct.

For binary case states and a valid mask, the transform satisfies the mask,
preserves unmasked positions, and is idempotent. These properties were checked
across **9,330 input/mask cases** covering all binary inputs and all
unmasked/0/1 mask assignments of lengths 1-5. Complement cases and **510 binary
check vectors** of lengths 1-8 were also checked. General conditional proofs
and the validation scope appear in the
[verification report](vessell-formula-research-report.md).

Verification is complete for those stated properties. Further originality
searches are not a prerequisite for using or documenting this method.
No runtime loop or authorization policy is changed by this document.

## Owner-source formula

The following wording preserves the owner's edited source. Review commentary
is separate; an apparent factual claim in the source is not automatically
certified by the mathematical verification above.

Owner-supplied method, written as a general formula. No password, string or
key is stored here. This is a non-cryptographic casing and gating rule for crytography.

## 1. State of each character

For a string `s = c₁ c₂ … cₙ`:

```text
state(cᵢ) =  1   if cᵢ is uppercase      (UP)
             0   if cᵢ is lowercase      (DOWN)
             ⊥   if cᵢ is digit/symbol   (neutral, unchanged)
```

## 2. Rule

```text
UP(cᵢ) = 1 − DOWN(cᵢ)          (UP = NOT DOWN)
```

Neutral characters are skipped.

## 3. Mask (second factor)

`M` assigns a required state to chosen letter positions:

```text
Mᵢ ∈ {1, 0}    for each masked letter position i
```

Factor 1 is the base string; factor 2 is the mask. Neither alone gives the result.

## 4. Transform

```text
yᵢ = Mᵢ          if i is masked
yᵢ = state(cᵢ)   otherwise
```

Apply case from `yᵢ` (1 → uppercase, 0 → lowercase); leave `⊥` unchanged.

## 5. Gate

```text
G = ∏ [ yᵢ = Mᵢ ]   over every masked i

G = 1 → UP        G = 0 → DOWN
```

The product makes a single DOWN anywhere fail the whole gate.

## 6. Applied to SI loops (NOW = UP)

Replace characters with the checks `k₁ … kₘ` of the current run only:

```text
NOW = UP  ⇔  G = ∏ UP(kⱼ) = 1
```

- Phase 0 gate: checks are R1–R11 (sources re-opened) and T1–T4 (read-only
  chain touch). On 2026-10-14 all 15 were UP, so G = 1.
- Phase 1 receipts: `vessell.receipts.gate(problems)` returns UP only when the
  verifier reports zero problems (tag, key, root, duplicates, files).

Passing a gate records integrity of this run.

---

## Research commentary (assistant-authored; not part of the owner formula)

The sections above preserve the owner's edited wording, apart from the
requested title and code-block formatting changes. The mathematics and its
limits are assessed separately in the
[verification and mathematical review](vessell-formula-research-report.md).
That review does not certify a new cryptographic primitive, multi-factor
authentication, evidence truth or permission to proceed to another phase.
