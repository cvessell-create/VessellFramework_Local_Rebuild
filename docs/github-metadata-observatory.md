# GitHub metadata observatory

Status: experimental, read-only, human-review preview. This is an R research
tool, not autonomous self-improvement or a released framework report.
An authorized human still completes source/preview-bound inquiry and a separate
release decision through the existing specialist workflow before report release.
Suggestions here are not submitted, approved or executed by that workflow.

## Run and inspect

From the repository root, with R 4.1+ and GitHub CLI:

```sh
Rscript r/setup.R
gh auth login
Rscript r/test_github_observatory.R
Rscript r/run_github_observatory.R
# Optional output root and pagination cap (1-100 pages per list):
Rscript r/run_github_observatory.R outputs/github-observatory 20
```

The repository is explicitly scoped to
`cvessell-create/VessellFramework_Local_Rebuild`. No other account is inspected.
Authentication stays with GitHub CLI or `GH_TOKEN`; do not place tokens in R
source, command arguments, snapshots or version control. All requests are GET.

Every run creates a new timestamp/PID directory under ignored `outputs/`.
It writes metadata-only `snapshot.rds` and `snapshot.json`, CSV tables,
`summary.json`, `learning.rds`, `learning.json`, optional held-out predictions,
`suggestions.json`, and `review-preview.md`. In R:

```r
snapshot <- readRDS("outputs/github-observatory/<run>/snapshot.rds")
runs <- read.csv("outputs/github-observatory/<run>/runs.csv")
learning <- readRDS("outputs/github-observatory/<run>/learning.rds")
```

Snapshots retain endpoint URLs, HTTP status, collection timestamps and rate
budget headers. They exclude issue/PR bodies and titles, commit messages,
author emails, code, workflow logs and credentials. Branch names, account
logins and URLs are still metadata: review them before sharing artifacts.
Returned metadata can change between pages; this is not an atomic historical
archive. Errors from required endpoints stop the run. Traffic 403/404 results
emit warnings and remain UNAVAILABLE, never a zero count. Other failures stop.

Pagination follows the presence of GitHub's `rel="next"` header with numbered
pages; reaching the configured cap records TRUNCATED. Learning refuses
truncated run collections. Commits cover the default branch only. The issues
endpoint includes PRs; the summary explicitly excludes them from issue counts.
Traffic covers the last 14 days and requires write access; the read-only
Actions token can therefore produce UNAVAILABLE traffic. Never add overlapping
unique-viewer or unique-cloner counts to estimate unique people.

## The math implemented

For workflow outcome learning, success is `y=0`; failure or timeout is `y=1`.
Other conclusions, incomplete runs and reruns (`run_attempt != 1`) are
excluded. A returned rerun can overwrite an earlier attempt's metadata;
excluding it avoids treating current attempt metadata as a first-run feature.
This is a conditional outcome model, not a predictor of every possible state.

Features available at run creation:

- push/PR event indicators and default-branch indicator;
- UTC hour sine/cosine and weekend indicator;
- workflow ID one-hot encoding, with vocabulary learned on training only and
  an explicit unknown-workflow indicator.

No outcome, log, duration, completion timestamp or human identity is a feature.
Missing branch means non-default; invalid timestamps/SHA/features cause errors.
Historical metadata is a reconstruction, not prospectively captured telemetry.

For feature row `x`, two hidden layers have widths 8 and 4:

```text
h1 = tanh([1, x] W1)
h2 = tanh([1, h1] W2)
p  = sigmoid([1, h2] W3)

L = mean(softplus(z) - y*z) + 0.01 * sum(non-bias weights squared)
softplus(z) = max(z, 0) + log(1 + exp(-abs(z)))
```

The stable softplus expression is binary cross-entropy. Analytic backpropagation
and base R `optim(method="BFGS")` fit the weights; seed 42 and fixed architecture
make each fit reproducible on the same input/environment. Optimization failure
stops explicitly. No pretrained model, external AI API or new neural-network
package is used. A zero-hidden-layer version supplies ridge logistic regression.

Chronological boundaries divide creation times approximately 60/20/20.
Ties stay on the later side of a boundary. Training outcomes must be recorded
before validation starts; validation outcomes before test starts. Commit SHAs
are purged across partitions, preferring the latest partition. Training is
never refit on validation/test. Fixed gates require:

- at least 200 eligible runs overall;
- at least 100 training runs, including 20 successes and 20 failures/timeouts;
- at least 30 validation and 30 test runs, each with 5 per class.

These are conservative engineering gates, **not proof of statistical power or
adequate sample size**. Failure yields INSUFFICIENT_DATA and descriptive
suggestions only. There is no invented data or synthetic-data production fit.

Held-out metrics:

```text
Brier = mean((p - y)^2)
LogLoss = -mean(y*log(p) + (1-y)*log(1-p))
```

Both validation and test compare neural predictions with logistic predictions
and the constant training failure fraction. The neural model must strictly
beat both baselines on both metrics in both partitions to receive
EXPERIMENTAL_BASELINE_WIN; otherwise it is BASELINE_NOT_BEATEN.
This one-window comparison does not establish calibration, significance,
generalization, independent observations or superiority to tree-based models.
Repeated daily evaluation reuses many of the same outcomes and is not repeated
independent corroboration. Workflow changes and shared commits cause dependence.

`summary.json` also computes weekly commit counts, weekly CI failure fractions,
language byte fractions, open issue count and median PR merge hours:

```text
language fraction = language bytes / total language bytes
failure fraction = (failures + timeouts) / evaluated runs
merge hours = (merged_at - created_at) in hours
```

Here the failure numerator is `(failures + timeouts)` and evaluated runs are
successes, failures and timeouts only. Counts are sample-bound when an endpoint
is truncated. The current week can be partial; compare matched windows.

## Suggestions and automation

Suggestions are deterministic, evidence-linked review prompts, not generated
causal diagnoses. A workflow with at least five evaluated runs and at least a
20% failure/timeout fraction gets a log-review suggestion. This threshold is an
attention rule, not a statistical significance test. Action-required runs get
a permission/approval review prompt, never a recommendation to remove gates.
Model status/metrics are a separate review prompt even if no model can train.

Daily local automation should run the command above at 09:00 local time,
summarize the newest preview and surface collection/training errors. It must
never edit source, commit/push, dispatch workflows, change permissions, release
reports or install packages without a separately authorized change.
The Agent Host must be available for its schedule. Saved local snapshots
accumulate; retention/deletion remains an operator decision.

[The manual Actions workflow](../.github/workflows/github-observatory.yml)
has read-only repository permissions and 30-day artifact retention. It has no
cron schedule, avoiding duplicate daily collection alongside local automation.
It becomes available only after the source is pushed to GitHub. Existing
control-panel allowlists remain unchanged. CI runs offline synthetic tests,
not network collection.

## Primary sources and bounded search record

Reviewed October 8, 2026:

- [GitHub pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api):
  page size, Link headers and next-page behavior.
- [Workflow runs](https://docs.github.com/en/rest/actions/workflow-runs):
  metadata fields and filtered-search limits.
- [Traffic](https://docs.github.com/en/rest/metrics/traffic):
  access requirements and 14-day window.
- [Google log-loss/regularization](https://developers.google.com/machine-learning/crash-course/logistic-regression/loss-regularization)
  and [backpropagation](https://developers.google.com/machine-learning/crash-course/neural-networks/backpropagation):
  mathematical training concepts; no upstream code copied.
- [Brier score definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html):
  binary probabilistic loss; no sklearn dependency introduced.
- [Grinsztajn, Oyallon and Varoquaux, tabular benchmark](https://arxiv.org/html/2207.08815v1):
  reviewed introduction reports tree-model advantages in that benchmark,
  motivating skepticism about neural superiority here. It is not a CI study.

SEARCH RECORD: GitHub metadata and neural tabular learning / web search,
official-document fetch and GitHub CLI / one repository and cited pages /
one canonical repository confirmed; math search returned five leads /
documentation extracts bounded/truncated; initial broad metadata search
returned no relevant results / primary sources opened: yes for citations above /
SOURCE-ESTABLISHED only for cited definitions and API contracts /
not checked: all literature, full benchmark methods, player behavior, private
logs, causal efficacy, model calibration or repositories outside this scope.
No third-party source code or dataset was imported.
The [R setup action](https://github.com/r-lib/actions/tree/v2/setup-r) was also
opened to confirm the `release` and `use-public-rspm` workflow inputs.
