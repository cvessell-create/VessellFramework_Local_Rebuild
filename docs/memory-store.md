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
