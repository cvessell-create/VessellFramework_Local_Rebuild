# SI loop development: two judgments

The [2026-10-15 case-policy correction](vessell-formula.md) separates character
case from compliance: required lowercase passes, and correction needs at most
one pass followed by verification. This is not a rule to alter evidence
observations, generate answers until they pass, or promote levels. The strict
evidence gate still rejects empty required-check sets; the mathematical empty
case mask passes. L1–L5 posterior thresholds, bottom-up holds and
`formula_telemetry` versus `generated` routing are unchanged.

Owner-directed interpretation, 2026-10-14. This document guides building and
measurement, not an external demonstration exercise.

## Judgment 1: gate outcome and boundary behavior

Retain the original requirement, check results, bottom-up threshold and state.
For the formula-routing case:

- Requirement/gate outcome: DOWN.
- Boundary behavior: promotion withheld as coded.

These belong to ONE judgment. Downstream levels may have met their own checks
while promotion remains held by L1. The report now identifies that blocker
separately from local check compliance.

## Judgment 2: measurement and next evaluation

The original L1 requirement asks for a generated reply. A formula request
deliberately takes the deterministic `formula_telemetry` route, with no model
generation. That mismatch remains part of historical run records and is useful
development feedback, not a reason to erase DOWN or manufacture a generated
answer.

Historical `CONTRACT_MISMATCH_MEASURED` classification required the explicit
route marker, nonempty telemetry, the observed telemetry kind and no response
error. A generic fallback, empty answer or error did not receive that
classification. Thresholds and the strict Vessell formula remain unchanged.

Current L1 runs avoid repeating that mismatch: with the default three trials,
they use two non-formula player/opening prompts for generated responses and one
separate formula prompt for telemetry. Formula prompts are excluded from the
generation prompts; the actual current formula snapshot is supplied to the
telemetry correctness check. The live check structure is:

1. A generated-answer fixture only passes when its predeclared expected content,
   generated kind/route and error-free response all match. Live L1 output without
   an expected-answer oracle still checks generated kind, route and nonempty
   output for the existing generation contract, but records semantic content
   quality as `NOT_EVALUATED_NO_PREDECLARED_ORACLE`.
2. Formula telemetry is checked against an explicitly supplied deterministic
   snapshot (state, phase and reported problems), with route, kind, nonempty
   text and no-error requirements. This checks correspondence to that supplied
   snapshot, not the truth of its inputs. A failed telemetry check is a failed
   L1 trial; telemetry cannot satisfy the generated-response trial.
3. Boundary tests retain DOWN for mismatch-only, failed-check and combined
   mismatch/failed-check cases, and preserve the bottom-up hold on later levels.
4. Predefined negatives cover wrong fixture answers, response/route errors,
   thrown route failures, malformed or generic telemetry, empty replies and
   fallback rejection.

The generation oracle helper and boundary tests do not modify trial counts,
posterior thresholds, two judgments or report history. The formula request is
now an explicit telemetry trial rather than a generation trial. Next evaluation
remains generated-answer quality on properly specified fixtures, telemetry
correctness against expected snapshots, and promotion-boundary behavior under
the declared requirements.

Define those case expectations before changing the generation requirement.
Keep historical runs intact. New reports and the dashboard carry the two
judgments together; neither changes report-release or execution permission.

## Research used

- [NIST AI RMF Core, Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/):
  reviewed Measure section supports testing metrics, uncertainty and documented
  evaluation outcomes.
- [Jacobs and Wallach, Measurement and Fairness](https://arxiv.org/abs/1912.05511):
  abstract reviewed; mismatch between a construct and its operationalization
  motivates checking what the test actually measures. Application here is a
  development synthesis.
- [Geifman and El-Yaniv, SelectiveNet](https://proceedings.mlr.press/v97/geifman19a.html):
  abstract reviewed; rejection and risk/coverage are separate outcomes. The
  implemented routing marker is not a SelectiveNet implementation.

Search record: AI measurement/gating and selective-prediction research /
web_search plus primary web_fetch / public web on 2026-10-14 / 6 and 3 distinct
cited URLs in the two search responses / search caps unavailable /
applicable primary sources opened / SOURCE-ESTABLISHED for those reviewed
sections; repository interpretation is synthesis / full papers, generalization,
external certification and independent field studies not checked.

The owner chooses when external demonstrations become a task. Development
reports should state the observed behavior and build path without unsolicited
intelligence rankings or repeated proof-to-others language.
