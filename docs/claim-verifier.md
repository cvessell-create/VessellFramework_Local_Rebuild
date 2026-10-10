# Local claim verifier

The browser page is a local interface to the existing Python verification
functions. It does not duplicate their rules or collect sources from the web.
It checks only the sightings and postings entered by the operator; URLs are
recorded as supplied but never fetched or authenticated. Results are analysis
previews, not evidence corroboration, human approval, or report release.

## Form-based UI and Python client

From a checkout with Python 3.13+, start the standard-library server:

```sh
python -m vessell.app
```

It opens the form-based UI at `http://127.0.0.1:8765/`. Illustrative examples
exercise the verifier; they do not establish current events or employer facts.
New sightings default to WORKING HYPOTHESIS. Stop with Ctrl-C.

The compatible JSON API returns verdict fields plus `source_access:
NOT_PERFORMED` and `release_status: ANALYSIS_ONLY_NOT_RELEASED`:

- `POST /api/verify` accepts `claim` and `sightings`.
- `POST /api/planted-news` accepts the same shape.
- `POST /api/ghost-job` accepts postings for one employer/title/location.
  Unrelated roles are rejected rather than compared as cloned postings.

The server rejects non-loopback Host and cross-origin requests, invalid framing,
non-JSON bodies, oversized bodies/arrays, unknown fields and malformed dates.
It applies no-store and browser security headers. Nothing is stored.

```python
from vessell.app.client import launch

with launch() as client:
    report = client.verify("Illustrative claim", [])
    assert report["source_access"] == "NOT_PERFORMED"
```

`launch()` starts a loopback HTTP server in a background thread, even though
it runs within your process. `VerifierClient` connects to an already-running
server. Both call the canonical Python verifier.

## Optional JSON-input UI

Install the optional FastAPI UI dependencies and start it from a checkout:

```sh
python -m pip install -e ".[verifier]"
vessell-verify-ui
```

Open `http://127.0.0.1:8765/`. The service binds only to loopback, rejects
non-local and cross-origin requests, limits JSON requests to 64 KiB and 100
entries, and keeps no database or browser storage. Stop it with Ctrl-C.
The two UIs use the same default port: run one at a time, or use the optional
UI's `--port` flag. They are separate interfaces, not the ambient review
dashboard or its durable release workflow.

The JSON API exposes the same deterministic checks:

- `POST /api/v1/verification/claims` runs `verify_claim` and
  `analyze_planted_news` over submitted claim sightings.
- `POST /api/v1/verification/jobs` groups submitted postings by normalized
  employer, title, and location, then runs `detect_ghost_job` for each role.

The tool validates request structure and dates but does not establish that
source names, timestamps, tiers, official-record flags, URLs, or excerpts are
accurate. Those remain operator-supplied inputs. It has no network access,
durable evidence store, release action, or execution authority.
