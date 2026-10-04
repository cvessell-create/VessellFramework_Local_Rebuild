# Operational case-study release (3.9.0)

This is executable local software, not a demo-only distribution. Existing
validator, pipeline, tool and authorization interfaces remain available.
Examples remain examples. Removing the project-wide demo framing does not
remove authorization, provenance, review requirements or evidence limitations.
The pipeline now requires an explicit `--input` and validates its contract.

## Run the reconstructed claim-correction comparison

```sh
python -m pip install .
vessell-study --spec case_studies/claim_correction/spec.json \
  --output-dir outputs/claim-correction-study
vessell-study --verify-only --output-dir outputs/claim-correction-study/framework
```

Use a new output directory for every run. Existing runs are never overwritten.
Both arms run in separate Python processes to isolate lifecycle registries.
Every snapshot is a real JSON file. SQLite stores file receipts and the full
hash-chained lifecycle event records. A fresh process reopens the database and
checks every consumer's ID, digest and event ordering. Paired JSON/Markdown
reports are verified before success is returned. Exit statuses: 0 accepted,
1 comparison acceptance failed, 2 input, execution or integrity failure.

The first scenario reconstructs an unverified constraint and five dependent
consumers: goal, scheduled search, morning edition, evening edition and memory.
These are **managed local files**, not external accounts, scheduled services,
application portals or an actual memory system. The second scenario is a
constructed official-record positive control with two consumers, checking
that the gate does not simply block everything.

The `snapshot-only` baseline stores the initial claim, allows consequential
use without corroboration and does not update downstream snapshots after
withdrawal. It is a specified counterfactual comparator, not a measurement
of the original assistant or a competing product. Both arms use exactly the
same frozen input population. The framework arm uses existing intake, gate,
supersession, dependency delivery and confirmation APIs. It confirms a
correction **only after writing and reading back the actual file**. New
corrections remain UNVERIFIED; propagation does not establish their truth.

Reports count unverified uses allowed, corroborated uses blocked, corrections
read back and original snapshots remaining. Counts are deterministic for the
frozen specification; UUIDs, event execution times and hashes can differ.
No field-effectiveness percentages or statistical significance are inferred.
Narrative dates travel separately from actual lifecycle execution timestamps.
Noon UTC in the frozen specification is a normalized reconstruction value,
not a verified time from original operational logs.

## Author-source reconciliation (2026-10-04)

The governing source is now the author's supplied
[How an Unverified Sentence Became System Behavior — and How to Stop It](claim-correction-case-study.md).
It is preserved byte-for-byte, with SHA-256
`42b20766faa8192fb720f938980dc824b84f138ec34c60965d2aef3792305b75`.
The [reconciliation artifact](paper-source-reconciliation.md) explains the
differences from the superseded LLM-expanded narrative.

The earlier 3.9.0 reconstruction pinned a different DOCX with SHA-256
`edbfb32d793a313b1a5dc6451221c0798bd17164822ec7dc9bb80e2ac945c475`.
Its paragraph-number mapping and policy-terminology discussion are no longer
requirements attributed to the author's paper. Those historical evaluations
remain associated with their original source/spec hashes; they are not
retroactively relabeled as runs of the corrected specification.

| Author-source requirement | Executable response | Evidence boundary |
|---|---|---|
| Sections 1, 2.1, 3: preserve the unverified intake caveat | Provenance snapshot and consequential gate | Tests do not establish the reported historical events |
| Sections 2.2, 4.2-4.3: corroboration or explicit waiver | Existing consequential gate and waiver tests; positive control | No actual eligibility or employment finding |
| Sections 2.4, 3, 4.4-4.5: supersession, dependent enumeration and verified update | Registered managed JSON consumers, original retained, write/read-back before acknowledgment | Only registered local consumers; not arbitrary external systems |
| Sections 2.3, 4.6: claim decay and revalidation | Existing stale-claim fail-closed lifecycle tests | No long-duration field follow-up or automatic schedule inferred |

The paper is primary evidence of what the author wrote, not independent
verification of the incident. Original configurations, memory exports,
scheduled-job logs and external receipts remain absent for historical replay.
Its phrases "structurally impossible" and "proof" are preserved as authored
language, not adopted as universal software guarantees. The executable
comparison is still a deidentified reconstruction plus a synthetic positive
control, not the original assistant's measured behavior.

## Durable state and scope

The comparison persists receipts and events and supports post-restart
verification. The library's live lifecycle registries remain process-local.
This release is **not** a crash-resumable production workflow controller, a
transaction across arbitrary files and databases, or a distributed broadcast
service. Files and receipts can be damaged between operations; failed runs
remain for diagnosis and return failure rather than success. No automatic
repair of drift, concurrent consumer writers or arbitrary file formats is
supported. Local hashes detect alteration relative to receipts; they are not
an externally signed attestation or protection against rewriting all evidence.

Runtime reference code and schemas are now included in installed wheels and
source distributions, generated from canonical repository sources at build
time. CI runs the case study again from outside the checkout after non-editable
wheel installation. The historical manifest filename is retained for
compatibility; it tracks current source contents, not the runtime version.

Independent replication with a separate evaluator, prospective labeled
outcomes, authorized real-system connectors, crash/concurrency recovery and
sector-specific field studies remain subsequent gates. Public-data audits,
CDC retrospective scoring, the replay lab and Linux containment remain
separate evidence streams; their results are not new framework field outcomes.

## Release measurements

Executable source evaluated at commit
`6b4447d030911485a144d0e5e86c8973cb3259fa`; subsequent release changes only
document the measurements and update the source-integrity manifest.
The historical 3.9.0 frozen specification SHA-256 is
`c4c274bf47fbc54ba088037ba29ccea30e440487c6eb34b5ee654a0335d2903e`.
The corrected specification now pins the supplied Markdown source and has
SHA-256 `ebd9f4c7736eaa6d1bcc2653b078cfcc86ee3289764876e7c2d43dd4284b13dc`.
Only the spec's source-document hash changed; scenario inputs and runtime
policies were not rewritten. Report limitation text was also corrected to stop
calling the restored paper local-only. New runs identify the corrected spec
and their current implementation digest, not the old ones.
The historical 3.9.0 case-study implementation SHA-256 is
`28eb28f7a1ec294583665a0ef08a4887a1635ee8c7cb846134b1a395ddef655d`.

| Local outcome | Snapshot-only baseline | Framework |
|---|---:|---:|
| Unverified consequential uses allowed (five-consumer scenario) | 5 | 0 |
| Corroborated positive-control uses allowed | 2 | 2 |
| Corrected consumer files verified by read-back | 0 / 7 | 7 / 7 |
| Original snapshots remaining after withdrawal | 7 | 0 |
| Newly issued unverified corrections pass consequential gate | 0 | 0 |

All 342 regression tests passed on macOS and inside the offline Linux
container (zero Linux skips/failures/errors). Focused lint and strict type
checks passed. All ten containment assertions and all 271 source-manifest
entries passed in the evaluated image. Existing public-data replay and
ATT&CK/EPSS audits also passed without modifying the frozen inputs.

A fresh environment installed the non-editable wheel and completed the same
comparison from outside the checkout, then reopened and verified seven
framework receipts. A separate base-R script recalculated SHA-256 with the
system hashing tool and read all fourteen baseline/framework snapshot IDs:
all matched the exported SQLite receipts; seven original snapshots remained
in the baseline and none in the framework arm. This is cross-language
computational replication by the same evaluation workflow, **not independent
third-party or field validation**. No significance or population efficacy
estimate is reported from these seven managed consumers.
