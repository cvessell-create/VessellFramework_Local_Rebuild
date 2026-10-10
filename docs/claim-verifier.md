# Local claim verifier

The browser page is a local interface to the existing Python verification
functions. It does not duplicate their rules or collect sources from the web.
It checks only the sightings and postings entered by the operator; URLs are
recorded as supplied but never fetched or authenticated. Results are analysis
previews, not evidence corroboration, human approval, or report release.

Install the optional local UI dependencies and start it from a repository
checkout:

```sh
python -m pip install -e ".[verifier]"
vessell-verify-ui
```

Open `http://127.0.0.1:8765/`. The service binds only to loopback, rejects
non-local and cross-origin requests, limits JSON requests to 64 KiB and 100
entries, and keeps no database or browser storage. Stop it with Ctrl-C.

The JSON API exposes the same deterministic checks:

- `POST /api/v1/verification/claims` runs `verify_claim` and
  `analyze_planted_news` over submitted claim sightings.
- `POST /api/v1/verification/jobs` groups submitted postings by normalized
  employer, title, and location, then runs `detect_ghost_job` for each role.

The tool validates request structure and dates but does not establish that
source names, timestamps, tiers, official-record flags, URLs, or excerpts are
accurate. Those remain operator-supplied inputs. It has no network access,
durable evidence store, release action, or execution authority.
