# Approved offline static artifact capture

This extension captures an explicitly allowlisted HTML snapshot and adds its
source, viewport PNG, JSON measurements and logs to the existing SQLite/SSE
review workflow. It does **not** execute repository builds, clone webhook URLs,
run user scripts, mutate repositories or automatically approve anything.
The ordinary ambient worker remains pure local analysis.

## Build and inspect

Install the `ambient` extra, initialize a private local database as described
in [ambient workflows](ambient-workflows.md), and build the trusted renderer:

```sh
docker build -t vessell-static-capture:local deploy/capture
vessell-ambient --database /absolute/path/private/ambient.sqlite init
vessell-capture inspect \
  --allowlist case_studies/ambient/static/allowlist.json --snapshot example
```

Building the image needs network access for its pinned Playwright dependency,
Python base image and Debian Chromium packages. Chromium's resolved version
and the image ID are recorded; the apt package version is not lock-pinned.
Capturing does not need network: each disposable container has
`--network none`, no host mounts, no Docker socket, a read-only root, a bounded
temporary filesystem, dropped capabilities, nonroot identity, PID/memory/CPU
limits and a 45-second host timeout. Chromium disables page JavaScript,
service workers and network requests; a restrictive CSP blocks external
resources. Only inline styles and data images are permitted. Interactive
applications are outside this capture mode.

Review the printed original source, declared intent, viewport and exact
selector/count/text checks. Copy its `request_sha256` only after reviewing
all of them:

```sh
vessell-capture run \
  --allowlist case_studies/ambient/static/allowlist.json --snapshot example \
  --database /absolute/path/private/ambient.sqlite \
  --output-dir /absolute/path/private/capture-evidence \
  --approve-request-sha REPLACE_WITH_INSPECTED_REQUEST_DIGEST \
  --reviewer your-name --reason "Capture this reviewed static snapshot"
```

The allowlist pins the HTML's exact UTF-8 bytes by SHA-256. Files must resolve
inside the allowlist directory, including symlink targets. Changing source,
intent, viewport or expected checks changes the required approval digest.
Source is limited to 32 KiB, combined requests to 64 KiB, checks to 16 and
viewports to 1920 by 1080. The immutable local Docker image ID is recorded in
the job rather than relying on a tag to identify the executed renderer.

Each attempt gets a new evidence directory. Failures exit nonzero, retain
available diagnostics and do not register a successful ambient job.
Successful source, receipt and artifacts are retained locally. A run is not
a replay key: repeating capture creates a distinct attempt with its own
timestamp and identity.

## Review and release

Point the native ambient API at that **same database path**, then inspect
the job in the Next.js dashboard. Source HTML is displayed as escaped JSON;
it is never hosted or evaluated in the reviewer browser. Only authenticated
PNG, JSON and plain-text artifact routes are exposed. The existing SSE history
notifies the dashboard of job creation and subsequent review.

The capture CLI is a separate operator process, not a backend execution
endpoint. For a named-volume Compose deployment, a host file path is **not**
the container's database path: use native deployment for capture/review, or
explicitly arrange an operator-owned shared database mount. No automatic
volume extraction, unsafe database copying or Docker socket integration is
provided.

Measurements include:

- Exact selector count, first element's text and Playwright visibility
  indicator (not opacity, contrast or readability).
- Horizontal overflow against the declared viewport; vertical page length is
  reported separately and not automatically treated as failure.
- Rendered viewport dimensions and artifact/source/request hashes.

The image is viewport-only, not a full-page screenshot. First elements hidden by
`display: none` or `visibility: hidden`
fail positive-count checks. Matching text does not establish readability,
accessibility, semantic intent, feature behavior or equivalence to a code
diff. A failed measurement still awaits human review; it cannot auto-release.
Approval releases the report, not a universal correctness certification.
Before approval, the configured human reviewer must also complete the
[Knowing Field assessment](ambient-workflows.md#mandatory-knowing-field-completion)
against this exact source and preview. Capture-request authorization, rendering
success, selector checks and prior approvals cannot satisfy that separate gate.
Pending legacy captures require completion too; previously released reports
retain their historical status without retroactive certification.

Artifacts are inserted atomically with the event and checked against its
hashes on read. The report binds the exact approved request and PNG dimensions.
Changing or deleting a persisted artifact fails verification; explicit job
pruning cascades to its artifacts. The container is disposable, not the
evidence: receipts and SQLite history remain until explicitly removed.

## Models and execution boundary

`model_status` is explicitly `not_configured`. No pretrained weights are
bundled, downloaded, called or assigned fabricated ONNX confidence scores.
The [parallel weight research](local-vision-weight-candidates.md) records
actual ONNX candidates, revision pins and unresolved redistribution checks.
A generic embedding or OCR model is not a trained code-versus-screenshot
verifier. Model integration requires a selected weight revision, license,
hash, input/output/preprocessing contract and measured local evaluation;
model findings must remain hypotheses with human review.

Docker isolation limits this specific static-data workload, not arbitrary
hostile code execution. Chromium's native process sandbox is not asserted
as enabled by this image; the container is the chosen boundary. The Docker
operator and image remain trusted, and a malicious administrator can replace
both evidence and hashes. There is no signature or formal attestation here.
Performance depends on source, browser, machine and storage; no constant-time,
hardware-identical, free-compute or infinite-scale guarantee is made.
