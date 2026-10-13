# R system readout

The R entry points refresh a private Markdown readout after use. By default it
is `~/.vessell/r-system-readout.md`; set `VESSELL_R_SYSTEM_READOUT_PATH` to
choose another local path. Each invocation replaces the prior snapshot; it is
not an append-only audit log. The snapshot records the latest operation, its
status, UTC timestamp, and R version only.

## What the R components inspect

| Operation | Data inspected or changed | Limits |
| --- | --- | --- |
| `setup.R` | Installed-package names and package versions for the declared dependencies; installs packages that are missing. | Does not inspect user datasets or attach optional packages. |
| Memory SQLite connection | Opens the selected database and ensures the memory/review tables and foreign-key setting exist. | Does not copy database contents into the readout. |
| `memory_store.R` add/review/list/retrieve | SQLite memory statement, scope, citations, status, validity, correction link, and review events. Retrieval requires a scope and returns approved, unexpired, matching entries. | The readout omits record contents, query terms, IDs, counts, reviewer identity, and notes. It is not connected to Copilot private memory. |
| `test_statistics_environment.R` | Generated synthetic vectors and test outputs used in assertions for paired/independent comparisons, categorical association, correlation, and rank-based alternatives. | This is a software smoke test, not analysis of real or user-supplied observations. |
| `run_github_observatory.R` | Projected repository metadata, default-branch commits, workflow runs, issue/PR metadata, contributors, branches, releases, and optional rolling traffic counts. | Requires the owner-authorized `gh` context. It omits issue/PR bodies, logs, emails, and tokens; output is an observational preview requiring human review. |
| `prompt_audit.R` | Aggregate counts by visible outcome class and SQL dialect in the selected local catalog. | Not a complete account export, private reasoning trace, or representative frequency sample. |
| `convert_python_memory_db.R` | Memory records and review events copied from a Python-compatible SQLite source to a new destination. | Source remains unchanged; destination must not already exist. |

## Automation and review loop

The GitHub observatory is an owner-triggered, read-only workflow that emits
review suggestions and evidence links. A defensible purple/orange workflow can
use one reviewer role to propose a bounded change and another to challenge its
sources, assumptions, harms, and tests. The challenge must be independently
checked against the cited source and implementation; accepted proposals still
need regression tests and authorized human review before a change is merged or
released. The usage readout itself does not run models or make changes.

This repository does not currently implement two independent AI agents, an
automatic code-change loop, or a connected Hail game runtime. The Hail
integration guide states that its build is paused and requires assets not
included in this repository. Deterministic scripts and synthetic tests are not
described as independent AI review or Hail evidence.

## Startup and cache boundaries

The R setup check uses installed-package metadata rather than loading every
package namespace. The GitHub Actions setup workflow caches Python package
downloads and the R user library; these caches improve repeated environment
setup, not cold application imports.
No analysis-result cache is used: current repository, memory, and evidence
inputs can change, and no existing analysis path has a verified
source/input/version cache key with safe invalidation. Memory review state,
evidence, and authorization decisions must never be reused from a stale result
cache.

The readout is private operational telemetry and should not be committed or
shared as analytical evidence. A successful write indicates only that the
snapshot was refreshed.
