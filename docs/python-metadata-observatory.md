# Python metadata and shared learning

The Python observatory extends the [GitHub/R observatory](github-metadata-observatory.md)
without duplicating its collector or neural math. It prepares human-review
previews only, not autonomous fixes or framework report releases.

## Run

From this source checkout, using its project virtual environment:

```sh
.venv/bin/python -m vessell.metadata_observatory
# Add an explicitly requested test run and shared GitHub/R learning:
.venv/bin/python -m vessell.metadata_observatory --run-tests --github
```

`vessell-observatory` is also registered as a Python console entry point;
installation refresh is required to make a new entry point available.
For an installed package, explicitly pass `--repository-root /path/to/checkout`.
The shared GitHub engine requires the source checkout, R/jsonlite and GitHub
CLI authentication. Neither entry point silently installs dependencies.

Each run writes a new ignored directory in `outputs/python-observatory/`:

- `python.json`: runtime, package versions, `pip check` outcome, tracked-source
  hashes/counts and optional test outcomes/timings.
- `suggestions.json` and `review-preview.md`: explicit human-review suggestions.
- With `--github`, a nested `github/` directory holds the existing R snapshots,
  model weights, held-out metrics and GitHub evidence-linked preview.
- If collection fails, `error.json` records COLLECTION_FAILED and the command
  exits nonzero. A failed dependency check or test run also exits nonzero,
  while preserving observations and marking the actual failure.

Collection covers the **current interpreter's environment**, tracked Python
files in this repository and the same single authorized GitHub repository.
It does not inspect all installed interpreters, unrelated repositories,
private sessions, user directories, player data or arbitrary accounts.

## Data boundaries

Persisted package data contains only distribution names/versions. No package
author emails, install paths, index/direct URLs or credentials are stored.
Runtime fields are Python version/implementation, OS family and machine type;
environment variables, hostname and user IDs are not collected.

Tracked source is parsed locally into metadata: relative path, SHA-256, bytes,
physical line count, function/class counts and counts of selected AST decision
nodes (`if`, loops, conditional expressions and exception handlers). These
counts are **not a control-flow-derived cyclomatic complexity metric** and do
not establish maintainability, correctness or code quality. Source text is
not persisted. Untracked/ignored files and symlinks are not analyzed.
Revision plus dirty-tree status distinguishes committed history from a local
working copy; per-file SHA-256 binds the actual Python bytes inspected.

With `--run-tests`, pytest executes repository test code using the current
interpreter, with its usual configured test behavior. This is authorized local
test execution, not a claim that tests are side-effect-free or sandboxed.
JUnit XML is temporary and deleted after extraction. Persistent records retain
only SHA-256 test identifiers, outcome and duration, not assertion messages,
captured stdout/stderr or raw parametrized test names. Failed subprocess output
is surfaced on the console for diagnosis, not stored in the dataset.
Hashed identifiers can be matched against known test names; they are not a
guarantee of anonymity. Preserve private outputs and review before publishing.

## Math and interpretation

For evaluated tests, excluding skips:

```text
test failure fraction = (failed + error) / (passed + failed + error)
```

An empty denominator is missing (`null`), never zero. Median and linearly
interpolated 95th-percentile testcase duration describe that invocation.
The percentile interpolates sorted durations at index `0.95*(n-1)`.
JUnit testcase duration includes pytest's configured timing scope; wall time
also includes collection/process overhead. A single test failure does not
establish flakiness. Repeated runs on identical source are dependent observations.
Tests with high observed durations get a profiling suggestion, not an automatic
optimization or a causal diagnosis.

The neural architecture, loss, sample/class gates, SHA-separated chronological
evaluation and baseline comparisons are exactly the shared R implementation.
The Python interface does not claim a second independently validated model.
Local package/source metadata is **NOT_MODELED_LOCAL_METADATA**: one environment
snapshot cannot support a labeled local-environment predictor. Variation,
temporally available inputs, sufficient outcomes and leakage-aware evaluation
would be prerequisites for adding that separate model.

Daily local automation can use the combined command at 09:00. It runs the GitHub
engine once, not separately in both languages. Local snapshots accumulate
without automatic deletion; collection, permissions, retention and any source
change remain operator decisions. The manual GitHub workflow remains R-only.

## Source record

Primary documentation opened October 8, 2026:

- [Python distribution metadata](https://docs.python.org/3/library/importlib.metadata.html):
  installed distributions are distinct from import-package names.
- [pip check](https://pip.pypa.io/en/stable/cli/pip_check/):
  dependency compatibility check and exit codes, not a vulnerability audit.
- [pytest output/JUnit](https://docs.pytest.org/en/stable/how-to/output.html):
  test-output documentation; extract only testcase observations.

SEARCH RECORD: Python metadata, test results and dependency checks / local
scoped source search and official-document fetch / current repository and
three official pages / one existing source-reader match, three primary pages
opened / bounded excerpts, not exhaustive / primary source opened: yes /
SOURCE-ESTABLISHED for documented interfaces only / not checked: all Python
environments, security advisories, package provenance, player telemetry,
prospective local prediction efficacy. No third-party code imported.
