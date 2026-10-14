# SI loop development: two judgments

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

The L1 requirement asks for a generated reply. A formula request deliberately
takes the deterministic `formula_telemetry` route, with no model generation.
The observed expected/generated versus actual/telemetry difference is recorded
as `CONTRACT_MISMATCH_MEASURED`. This is useful development feedback, not a
reason to erase DOWN or manufacture a generated answer.

The classification requires the explicit route marker, nonempty telemetry,
the observed telemetry kind and no response error. A generic fallback,
empty answer or error does not receive this classification. Trial counts,
thresholds and the strict Vessell formula remain unchanged.

Next evaluation:

1. Generated-answer quality on requests that actually require generation.
2. Telemetry correctness on requests assigned to deterministic state reporting.
3. Promotion-boundary behavior under the declared requirements.
4. Negative cases: wrong answers, route errors, crashes and unnecessary rejection.

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
