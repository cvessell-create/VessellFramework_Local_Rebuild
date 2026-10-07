# Local reviewed-memory store

`vessell-memory` is an application-owned, local SQLite store for concise
user-authored facts. It is not connected to GitHub Copilot memory and cannot
read or vote on Copilot's saved memories. The default database is
`~/.vessell/memories.sqlite3`; use `--database` to choose another location.

## Add and review

Create a JSON file with an assertion, explicit scope, and source references:

```json
{
  "statement": "This project supports Python 3.12 and newer.",
  "scope": "repository",
  "citations": ["pyproject.toml:10", "CONTRIBUTING.md:15"]
}
```

Then add it as pending and explicitly approve it:

```sh
vessell-memory add memory.json
vessell-memory review MEMORY_ID approve --reviewer "project owner" --note "Checked both sources"
```

Scopes are `repository` and `user`. A memory may optionally include an
ISO-8601 `valid_until` timestamp with timezone. User scope is for non-sensitive
preferences only; do not put secrets, credentials, personal data, or participant
data in this store.

Pending entries are never returned by retrieval. Review decisions and their
reviewer, note, and timestamp are retained in the local database. Rejected
entries remain available for audit through `list --status rejected`. Correcting
a pending or approved entry marks the old version corrected and creates a new
pending version with a link to the prior ID; the replacement must be approved
before retrieval. Corrections cannot silently change scope.

```sh
vessell-memory review MEMORY_ID correct --replacement corrected-memory.json \
  --reviewer "project owner" --note "Updated after checking the source"
vessell-memory list
vessell-memory list --status pending
```

The replacement JSON uses the same fields as the add file. Citations are
preserved as supplied; the application does not fetch, authenticate, or assess
them.

## Retrieve

Retrieval requires a scope and returns only approved, unexpired memories with
at least one matching word. Results are ranked by the number of matched query
terms. This is a small lexical match, not semantic search or an assessment of
truth. Each returned item includes its ID, scope, status, creation/expiry
timestamps, and citations so the caller can display provenance:

```sh
vessell-memory retrieve "Python compatibility" --scope repository --limit 5
```

The database is local application data, not a shared service. Back it up and
restrict filesystem access according to the sensitivity of approved content.

## R environment and Python database conversion

An equivalent standalone R CLI and SQLite store is provided in `r/`. Install R
and the required packages once:

```r
source("r/setup.R")
```

Run it directly with `Rscript`; its default database is shared with the Python
CLI at `~/.vessell/memories.sqlite3` because both use the same SQLite schema:

```sh
Rscript r/memory_store.R add memory.json
Rscript r/memory_store.R review MEMORY_ID approve
Rscript r/memory_store.R retrieve "Python compatibility" --scope repository
```

To convert rather than share an existing Python database, use the converter
with a **new** destination path. It copies memory IDs, scopes, status, citations,
timestamps, correction links, and review events; it leaves the source untouched
and refuses to overwrite an existing destination:

```sh
Rscript r/convert_python_memory_db.R \
  ~/.vessell/memories.sqlite3 \
  ~/.vessell/memories-r.sqlite3
Rscript r/memory_store.R --database ~/.vessell/memories-r.sqlite3 list
```

Run the R regression checks from the repository root using
`Rscript r/test_memory_store.R`. The R implementation and converter do not
connect to Copilot or runtime memory services; they only operate on the
application's local SQLite store.

## Copilot cloud-agent environment

`.github/workflows/copilot-setup-steps.yml` provisions Python 3.12 and R 4.3.3
with this repository's Python development extras and R memory-store packages
before a Copilot cloud-agent session. It runs both memory-store test suites and
the repository integrity-manifest check. After this workflow is merged to the
repository's default branch, Copilot cloud-agent sessions can run the
`vessell-memory` Python command or `Rscript r/memory_store.R`. The repository's
`.github/copilot-instructions.md` asks Copilot to retrieve only relevant
repository-scoped notes when the application database is already present, and
to verify all cited details against current files.

This setup does **not** connect to, import, modify, or vote on Copilot's own
private memory system; that system does not expose a repository-callable API.
The agent environment is ephemeral, and the default user database under its
home directory is not a durable cross-session store. To work with application
memories, provide a database explicitly through a trusted workflow or import
reviewed repository facts; do not place personal or sensitive memories in
source control or configure shared caches/secrets as an unreviewed memory
channel.

## Continuous repository checks

The regular GitHub Actions workflow runs on every push and pull request. Its
`memory-store-r` job installs R 4.3.3 and runs the R memory-store and converter
regression suite, while the Python matrix tests the Python implementation. The
Copilot instructions also attempt a relevant repository-scoped lookup for each
repository coding/documentation task when the application database is present.
“Always on” here means per-session lookup and continuous change validation;
GitHub Actions does not run a permanent daemon, and no memory database is
implicitly shared or kept alive between ephemeral Copilot sessions.
