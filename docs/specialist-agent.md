# Callable evidence specialist

The [product vision](../VISION_AND_SCOPE.md) defines VessellFramework as a
full-stack SI sub-agent whose implemented core provides reusable,
provenance-aware analytical services to coordinating agents. The email-inspired
workspace is its human-facing control plane, not the primary product.
This contract preserves distinct boundaries among task intake, bounded
analysis, durable evidence and provenance history, human review and report
release, and explicitly authorized execution. Submission and result-retrieval
capabilities do not confer review or execution authority; human filing metadata
does not corroborate claims or change analytical confidence.

Start the existing [ambient API and review dashboard](ambient-workflows.md).

Pull the package directly from this repository, or install `".[ambient]"` from
a checkout. No PyPI publication is implied:

```sh
python -m pip install "vessell-framework[ambient] @ git+https://github.com/cvessell-create/VessellFramework_Local_Rebuild.git@master"
```

Replace `master` with a reviewed commit SHA for a pinned installation. Register
the SDK methods and `SpecialistClient.tool_contract()` in your orchestrator;
this does not silently install a native VS Code/MCP agent or grant host tools.

## Task contract and Python client

```python
import os
from datetime import UTC, datetime
from vessell.ambient.models import AgentEvidence
from vessell.ambient.specialist import SpecialistClient, SpecialistTask

client = SpecialistClient(
    "http://127.0.0.1:8000",
    os.environ["VESSELL_AMBIENT_INGEST_TOKEN"],
)
task = SpecialistTask(
    task_id="analysis-001",
    caller="my-orchestrator",
    timestamp=datetime.now(UTC),
    question="What does this reported event actually establish?",
    evidence=[
        AgentEvidence(source_id="report-a", description="The caller reports a changed setting."),
    ],
)
receipt = client.submit(task)
same_job = client.submit(task)  # Same timestamp and normalized task: replay, not a new task.
assert same_job["id"] == receipt["id"]
snapshot = client.get(receipt["id"])
```

Install `vessell-framework[ambient]` for these imports. HTTP callers use
`POST /api/v1/agent/tasks` with the same JSON fields and a timezone-aware ISO
timestamp, then `GET /api/v1/agent/tasks/{job_id}`. Both require the ingest
bearer token. Unknown fields are rejected; evidence has 1-24 entries with unique
source IDs and bounded text. Optional `upstream_of` declares source lineage,
not independent corroboration. Total request bodies are capped at 64 KiB.
Optional `field_inquiry` supplies structured caller context using the
[shared schema](../schemas/field-inquiry.schema.json) and the task's evidence
IDs. It remains DOCUMENTED_UNREVIEWED and cannot satisfy the human completion
gate. Omitting it retains replay compatibility with earlier tasks.

Identity is `(agent, caller, task_id)`. Replaying the same normalized content
returns the same job; changing it under that identity returns 409. Retain the
original timestamp for replay. The `caller` string is a declaration by the
credential holder, not cryptographically attested agent identity.

## Result contract

Responses contain `id`, `provider`, `state`, `version`, original `event`,
`preview`, `result`, `history`, `artifacts`, `filing` and `field_review`.
A new task is PENDING and the
bounded worker creates its preview. The structured pipeline includes evidence
counts, lineage, Harm Gate, posture, notes and confidence ceiling.

- Agent-supplied descriptions are always **WORKING HYPOTHESIS**.
- Specialist confidence is capped at **VERY LOW** until external verification
  occurs outside this interface; reporting source IDs does not establish truth.
- `preview` is not a released result.
- A separate human reviewer completes the source/preview-bound
  [Knowing Field inquiry](ambient-workflows.md#mandatory-knowing-field-completion)
  and then approves or rejects in the review console. The calling agent cannot
  complete inquiry or approve. Missing/declined perspectives must be explicit.
- Only `state == "COMPLETED"` with non-null `result` is a released report.
- REJECTED/FAILED/pending are not completion, even if a preview exists.
- Approval releases analysis; it does not corroborate claims.
- Human inquiry records are independent of the immutable analysis snapshot.
  Read their verified status/version/history in `field_review`; completion
  neither raises confidence nor validates embodied fourth-person knowing.

The caller's ingest credential can submit/read specialist tasks, but cannot
read ordinary review jobs, approve/reject jobs, fetch private artifacts through
admin routes or dispatch GitHub Actions. Keep the separate reviewer credential
out of agent configuration. This first release has one shared ingest
credential and no per-caller tenant isolation; do not share it with mutually
untrusted external organizations.

The client accepts HTTPS or loopback HTTP, rejects credential-bearing URLs
and redirects, uses a timeout and bounds response size. Provider/API errors
raise rather than returning fake reports. It does not persist credentials or
spawn a background polling loop.

## Execution distinction

Calling the specialist never authorizes shell commands, webhook builds,
repository changes or models. GitHub execution is a separate
[owner-authenticated named-workflow surface](github-control-panel.md).
Static rendering is a separate
[operator-approved capture path](static-artifact-capture.md).
Agents may request work and report evidence; the human retains execution and
release authority.
