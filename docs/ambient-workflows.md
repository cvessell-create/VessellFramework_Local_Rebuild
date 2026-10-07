# Ambient event review stack (3.12.0)

This is an executable **analysis-only** stack: Next.js reviewer dashboard,
same-origin server-side API proxy, authenticated FastAPI ingress, SQLite
workflow/history storage, and a bounded Python analysis worker. It reuses the
existing evidence pipeline and Harm Gate. It is not a superintelligence claim,
LLM planner, autonomous remediation service or production certification.

The product direction is a full-stack SI sub-agent. The email-inspired
workspace is its human control plane, not a substitute for the
[callable agent contract](specialist-agent.md), and not an Outlook/mail service.

## One-command deployment

Prerequisites: Docker Engine with Compose, network access for image/dependency
builds, and free localhost ports 3000/8000. Generate distinct private secrets
of at least 32 characters and export them in the same terminal:

```sh
export VESSELL_AMBIENT_ADMIN_TOKEN="$(openssl rand -hex 32)"
export VESSELL_AMBIENT_INGEST_TOKEN="$(openssl rand -hex 32)"
export VESSELL_AMBIENT_REVIEWER="your-reviewer-name"
docker compose -f compose.ambient.yml up --build
```

Open **http://localhost:3000** and sign in with the admin token. The API is at
http://127.0.0.1:8000. Do not publish tokens in the repository or browser URLs.
Token configuration is an explicit prerequisite, not an insecure default.
Both host ports bind to loopback; containers are nonroot, read-only except the
SQLite volume and temporary storage, and drop capabilities.

Stop with Ctrl+C and `docker compose -f compose.ambient.yml down`. The named
volume retains state; do not add `--volumes` unless intentionally discarding it.
Compose does not detach by default or start a persistent scheduling automation.

For native development:

```sh
python -m pip install -e ".[ambient]"
VESSELL_AMBIENT_DB=/absolute/path/to/private/ambient.sqlite \
  uvicorn vessell.ambient.api:create_app --factory --host 127.0.0.1 --port 8000
# Separate terminal, with the same admin token environment:
cd frontend
npm ci
NEXT_TELEMETRY_DISABLED=1 npm run dev
```

Node 24+ is required; the lockfile pins frontend dependency resolution.
Frontend server environment `VESSELL_AMBIENT_API_URL` defaults to
http://127.0.0.1:8000. `VESSELL_DASHBOARD_ORIGIN` must match the browser origin
exactly (Compose uses http://localhost:3000); mutation requests from other
origins are rejected. No wildcard CORS is installed.

## Ingest and review

Send a timezone-aware, provider-neutral event using the **ingest** token:

```sh
curl --fail-with-body http://127.0.0.1:8000/api/v1/events \
  -H "Authorization: Bearer $VESSELL_AMBIENT_INGEST_TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @case_studies/ambient/event.json
```

Supported domains are `vcs` (`vcs.push`) and `monitoring` (`alert.triggered`).
Operator-approved `static.snapshot` jobs enter only through the
[offline capture CLI](static-artifact-capture.md), not webhook or event ingress.
Schemas, required fields and limits are documented by `/openapi.json`.
Unknown fields, domain/type mismatches, naive timestamps, malformed data and
bodies over 64 KiB fail explicitly. The worker creates a preview and waits
for review. Inspect the original input, analysis and history before approving.
Approval persists the already-reviewed report; it never executes provider
payloads, follows repository URLs, calls models, runs commands or changes files
outside the private database. Rejection remains `REJECTED`, not success.

### Mandatory Knowing Field completion

Apply [the fifth-pillar skill](../VesselFramework_Knowing_Field_SKILL_v0.1.md).
Before approval, the configured human reviewer inspects the original input
and exact preview, fills the structured inquiry editor, confirms that review
and records completion. This is an inquiry record, not simulated presencing
or a certificate that participant accounts are true.

Admin-only `POST /api/v1/jobs/{job_id}/field-inquiry` accepts lifecycle
`expected_version`, independent `expected_field_version` (0 initially) and
`assessment`. Fetch the job's blank `field_review.template` and fill every
required property according to the [shared schema](../schemas/field-inquiry.schema.json).
Document missing/declined voices rather than fabricate them. Evidence IDs must
refer to the job's sources; non-specialist events use `external-event`.
Each text is bounded to 2,000 characters, the canonical assessment to 32 KiB,
and the whole HTTP request to 64 KiB. Invalid input is 422, stale versions or
non-review states are 409. The endpoint requires the admin credential;
caller/ingest credentials cannot complete inquiry.
Live updates never silently rebase an open inquiry draft onto a newer server
revision. A stale draft is retained and cannot be submitted or approved until the reviewer
explicitly reloads and reviews the current inquiry; reloading replaces the draft.

Completion revisions are independent of filing and lifecycle revisions.
Source/preview digests, actor, timestamp and hash-linked completion history are
verified on read. Approval commits to the selected completion hash; worker
release preserves that binding. Human completion may be revised only while
AWAITING_APPROVAL, not after approval. Approval additionally requires the exact
`expected_field_version` (starting at 1), current lifecycle `expected_version`,
Harm Gate clearance and a separate nonblank decision reason. Rejecting does
not require completion. Caller inquiry context remains DOCUMENTED_UNREVIEWED.
Confidence and independent source roots never increase from completion.

On upgrade, pending and awaiting-review jobs require the new gate. A legacy
APPROVED job lacking completion returns explicitly to AWAITING_APPROVAL; it
does not auto-release. Historical COMPLETED records remain unchanged and are
labeled LEGACY_UNASSESSED where appropriate. The pipeline inside an immutable
preview/result records original caller inquiry status; authoritative human
completion lives in the separate `field_review` ledger and release state.
Historical CLI/case reports are previews, not exemptions to human release.

All workflow reads, decisions and event streaming require the admin token.
The dashboard exchanges that token for an eight-hour HttpOnly, SameSite=Strict
session; the backend token stays in server configuration, not localStorage.
HTTPS sessions use Secure cookies. Reviews require a nonblank reason and an
expected version, so concurrent/stale decisions conflict instead of silently
overwriting each other. Reviewer identity is configured server-side, not
accepted from event or action payloads.

This release has **one configured reviewer identity and shared credential**,
not a multiuser identity provider, per-role authorization, password recovery
or rate-limited public login. A public deployment needs TLS, identity/RBAC,
rate limiting, ingress governance and operational review; do not simply bind
this local application publicly.

## Human intelligence filing

Every legacy and newly submitted job starts in **Inbox**, unread, unflagged,
without a category color. The migration adds metadata and history without
rewriting source inputs, lifecycle history, previews or released reports.
The workspace provides this fixed, user-supplied hierarchy:

```text
Inbox
01 - ACTION REQUIRED
02 - STRATEGIC INTELLIGENCE
  02A - Market Intelligence
  02B - Policy Intelligence
  02C - Industry Intelligence
03 - PROFESSIONAL NETWORK INTELLIGENCE
04 - EDUCATION & CREDENTIALS
  Courses
  Certifications
05 - INDICATOR WATCHLIST
06 - ADMINISTRATIVE
07 - ARCHIVE
```

Parents and children are separate filing destinations. Selecting a parent
shows items filed directly there, not a hidden aggregate of its children.
Analysis-state views remain separate and span all folders. Folder counts
and search refer only to loaded jobs; load more to examine older items.
Opening an item marks it read. Manual unread, flags, folder moves and six
category colors persist across refresh/restart. These are human organization,
not corroboration, confidence upgrades or execution grants. Archive is
preservation, not deletion or report completion; explicit retention/pruning
policy still applies.

Admin-only `POST /api/v1/jobs/{job_id}/filing` accepts `expected_version`
(the **filing** revision) and one or more of `folder`, `is_read`, `flagged`,
`category_color`. Allowed IDs/colors and strict types appear in OpenAPI.
`category_color: null` clears a category. Unspecified fields stay unchanged.
A stale revision returns 409; invalid/empty patches return 422. An identical
patch at the current revision returns the unchanged snapshot without another
audit record. Actor identity comes from server configuration. Ingest/agent
credentials cannot mutate filing or approve reports.

Filing revisions and hash-linked history are independent of analysis
versions/digests. Reads verify both histories. Durable SSE notifications
cover lifecycle, filing and inquiry changes using one monotonic cursor; schema migration
preserves existing lifecycle cursor values. This detects stored drift, not
an attacker replacing all records and hashes. Calling agents can read filing
context with their task results under the existing shared-credential model;
there is no new per-caller or multitenant isolation.

## GitHub and GitLab adapters

Optional webhook routes are disabled until their distinct provider secret is
configured:

- `VESSELL_GITHUB_WEBHOOK_SECRET`: GitHub
  `/api/v1/ingress/github`, push events, `X-GitHub-Delivery`, HMAC-SHA256 over
  the exact bounded raw bytes in `X-Hub-Signature-256`.
- `VESSELL_GITLAB_WEBHOOK_SECRET`: GitLab
  `/api/v1/ingress/gitlab`, `Push Hook`, `X-Gitlab-Event-UUID`, timing-safe
  `X-Gitlab-Token` comparison. This is shared-token verification, not HMAC.

Restart/recreate the backend after configuration changes. These providers
cannot reach localhost directly; no tunnel, remote webhook registration or
GitHub repository setting is configured automatically. Testing adapters
locally does not establish a live GitHub/GitLab delivery connection.
Deletion pushes and missing head-commit timestamps are explicitly unsupported.
Only selected repository/ref/commit/author fields are retained, not whole
provider metadata or embedded secrets. Provider timestamps are reported
context, not proof of source truth. A valid signature authenticates the
delivery, not corroboration of every claim it contains.

## Durable execution and recovery

State graph:

```text
PENDING -> RUNNING -> AWAITING_APPROVAL -> APPROVED -> RUNNING -> COMPLETED
                            \-> REJECTED
PENDING / RUNNING / APPROVED -> FAILED (where applicable)
APPROVED -> AWAITING_APPROVAL (legacy/policy recheck failure, no release)
```

Bounded worker steps run inside `BEGIN IMMEDIATE` transactions. The analysis is
pure and local. RUNNING and its following checkpoint commit together; an
interruption rolls back the whole step, leaving PENDING or APPROVED eligible
after restart. This deliberately avoids a misleading BackgroundTasks-only
queue and orphaned durable RUNNING records. Multiple local worker attempts are
serialized by SQLite, not protected by `check_same_thread=False`.

Logical analysis failures record FAILED with server logging. Integrity,
database or unexpected worker failures stop the worker and make health
unavailable rather than silently dropping jobs; inspect logs and repair
through operator review. There are no automatic infinite retries.

Registration atomically deduplicates `(provider, source, event_id)` with a
unique constraint. Identical normalized content returns the original job;
changed content under the same key returns 409. Identity persists with the
job through restarts and review. Raw-provider fields not retained by the
normalizer are not part of the deduplication comparison. This is not a proof
of mathematical idempotence or exactly-once external side effects.

Each lifecycle record commits to its predecessor, input digest, preview/result
digests, actor, reason and logical version. Reads verify chains and snapshots.
This catches drift relative to persisted evidence, not an attacker replacing
all records and hashes. It is not a signed attestation or formal distributed
broadcast proof. SQLite provides local transactions, not distributed consensus.

SSE sends durable change IDs from SQLite, supports Last-Event-ID reconnect
replay, and uses heartbeat comments and bounded batches rather than unbounded
in-memory client queues. The dashboard loads a snapshot before/alongside SSE
and re-fetches on changes; Refresh is a visible recovery option. List results
are bounded and paginated by stable job ID, not creation time. Retention
removes replayable changes for deleted jobs; a fresh snapshot is authoritative.

## Inspection, explicit pruning and reset

```sh
vessell-ambient --database /absolute/path/ambient.sqlite status
vessell-ambient --database /absolute/path/ambient.sqlite verify
vessell-ambient --database /absolute/path/ambient.sqlite prune --days 30
# Inspect the dry-run count, archive evidence, then deliberately apply:
vessell-ambient --database /absolute/path/ambient.sqlite prune --days 30 --apply
vessell-ambient --database /absolute/path/ambient.sqlite reset \
  --confirm-path /absolute/path/ambient.sqlite
```

`init` explicitly creates a new database. Other CLI commands require an
existing file. Retention is disabled by default. Pruning deletes only old
terminal jobs and their histories/delivery identities together with foreign
keys enabled; live or awaiting-review deliveries remain deduplicated. Reset
requires the exact resolved path and refuses while any nonterminal job exists.
Neither operation recursively deletes paths or silently disables constraints.
Pruning/reset intentionally ends the replay guarantee for deleted IDs.
No automatic VACUUM or performance promise is made; indexes are tested as
schema structure, not O(1), sub-millisecond or million-row benchmark claims.

## Validation and provenance of this design

The supplied architecture discussion was treated as requirements and
illustrative pseudocode, not source-established implementation. Corrected
pitfalls include optional signature verification, unauthenticated approval,
read-before-insert races, deletion of live idempotency identities, ephemeral
BackgroundTasks, unbounded SSE queues, misspelled VACUUM and unsupported formal/
performance claims. Both idempotency **and regression tests** are needed.

The original paper and source reconciliation remain canonical; this feature
does not expand the author's historical claims. No course files, personal
records or the pasted source are uploaded as implementation evidence.
The game build remains paused and separate.

Run `pytest -q tests/test_ambient.py`, strict Mypy/Ruff for
`vessell/ambient`, and `npm run test`, `npm run typecheck`, `npm run build`
inside `frontend`. Tests exercise concurrent duplicates/reviews/workers,
restart/rollback, malformed/authenticated delivery, namespaces, tampering,
prune/reset and session/path restrictions. Container and browser observations
are computational checks, not field effectiveness or model intelligence.
