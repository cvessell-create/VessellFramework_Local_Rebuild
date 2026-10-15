# Repository maintenance

Current doctrine is in [SKILL.md](../SKILL.md); product direction is in
[vision and scope](../VISION_AND_SCOPE.md). Start current research review with
[the review packet](../PROFESSOR_README.md), not an archived showcase.

## Source and archive boundaries

Keep active services, command entry points and their tests together. Move
superseded guidance and unused demonstrations to the [archive](../archive/README.md)
only after checking imports, documentation, packaging and workflows.
Do not archive author sources, licences or audit history as if they were
obsolete implementation. Preserve archived contents and record their original
paths; old results remain dated results, not current validation.

The compatibility case runner, single-file recognition tool, path synchronizer
and managed payloads still have callers or tests. They remain available but
are not the primary product setup.

## Validation

Use the selected Python environment. In a checkout with `.venv`:

```sh
.venv/bin/python -m pytest -q
```

Run focused tests while editing, then the full suite once before finishing.
Keep failures visible and preserve the measured result in its dated record.
Tests establish behavior under their inputs, not empirical usefulness.

## Repository artifacts

After reviewing and staging the intended source additions, moves and removals:

```sh
.venv/bin/python -m vessell.hosted_agent --build-discovery .
.venv/bin/python scripts/sync_repository_artifacts.py --apply
```

Discovery uses an explicit active-reference allowlist, not archived skills.
The synchronizer refreshes the packaged skill mirror and tracked-source hashes.
Stage generated artifacts after reviewing them. Hashes establish byte integrity,
not installation, human review or report release.

## Optional private-path synchronization

The existing installer remains supported by `run_framework.py` and its tests.
It is dry-run by default. Inspect an explicitly selected owner-controlled root:

```sh
.venv/bin/python run_framework.py --dry-run --target-root /absolute/owner-controlled/root
```

Review missing targets before separately authorizing `--apply`. Do not create
or overwrite private paths as part of an archive cleanup. Installation claims
require successful writes, post-write checks and the installer log. See the
[historical installation records](../archive/README.md) for prior states only.
