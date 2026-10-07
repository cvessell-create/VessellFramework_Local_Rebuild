# VessellFramework vision and scope

## Product vision

VessellFramework is being developed as a **full-stack SI sub-agent** that provides
reusable, provenance-aware analytical services to coordinating agents. Its
implemented core is a **callable evidence specialist** that accepts bounded
tasks, produces structured analyses and exposes explicit review and release
states. The product comprises the agent contract, analysis runtime, durable
evidence infrastructure, human oversight and separately authorized execution
interfaces; it is not defined by a particular dashboard presentation.

The **email-inspired intelligence workspace is the human-facing control plane,
not the primary product**. Its purpose is to support evidence inspection,
information triage, persistent organization and human review. Folders,
read/unread markers, flags and category colors are organizational metadata.
They neither replace the specialist's analytical services nor confer
corroboration, confidence, report-release authority or execution permission.

The SI designation expresses the intended product direction rather than a
demonstrated superintelligence capability. Implementation tests, local case
studies and interface availability must be distinguished from independent
field efficacy, formal attestations and production certification.

This document specifies the rebuild's architectural direction and scope.
The [author's original paper](docs/claim-correction-case-study.md) remains the
authoritative source for its authored correction playbook. Subsequent software
development does not revise that paper's historical account or constitute
independent evidence of its original incidents.

## Architectural and governance principles

### Five-pillar inquiry architecture

The current framework uses PARADOX, BOTTLENECK, DUAL LAYER, XFACTOR and
**KNOWING FIELD**. The fifth pillar extends inquiry to observer participation,
affected parties, perspective gaps, dissent, relational source conditions
and attention/intention/agency. It is grounded in the entire Scharmer and
Pomeroy (2024) article, not only its abstract.
See the [theory skill](Knowing_Field_Theory_SKILL_v0.1.md),
[framework audit](docs/knowing-field-framework-audit.md) and
[combined application skill](VesselFramework_Knowing_Field_SKILL_v0.1.md).

The article's fourth-person theory concerns human embodied knowing. Software
supports its inquiry records; it does not perform or verify presencing.
The owner selected mandatory human completion before every new report release,
including pending legacy workflows. This is policy adoption and an unvalidated
research adaptation, not demonstrated efficacy. Honest missing/declined
perspectives are acceptable findings; fabricated accounts are not.
Existing released records remain historical and are not retroactively certified.

The stack maintains distinct functional and authorization boundaries:

1. **Agent task intake:** authenticated, typed interfaces accept bounded
   requests and preserve replay identity without granting reviewer privileges.
2. **Bounded analysis:** the analytical runtime applies the framework's evidence
   and provenance methods without treating caller descriptions as corroboration.
3. **Evidence infrastructure:** durable storage retains source inputs, analysis
   outputs, captured artifacts and verifiable histories independently of
   human-facing filing metadata.
4. **Human review and release:** an authorized reviewer assesses an analysis
   and records a decision. Report release does not establish the truth of
   the underlying external claims.
5. **Execution authority:** external execution requires a distinct,
   explicitly authorized interface and scope. Task submission, report release
   and workspace interaction are not interchangeable execution grants.

The HTML workspace operates as a client of these services. Repository-scoped
GitHub App authentication supports owner-requested, allowlisted GitHub Actions
tasks; the specialist API supports agent submission and result retrieval;
SQLite history and captured artifacts preserve operational records. Each
capability retains its own authorization boundary and validation requirements.

## End-to-end architecture

```text
Calling agent -> authenticated specialist task API -> durable SQLite job
              -> bounded evidence analysis -> preview + provenance/history
              -> human Knowing Field completion -> separate human release decision
              -> released structured report + inquiry history -> calling agent

Owner HTML panel -> GitHub App sign-in -> allowlisted workflow dispatch
                 -> GitHub Actions -> logs/artifacts/source SHA -> owner review

Operator-reviewed HTML snapshot -> offline disposable capture container
                               -> source/PNG/checks/log hashes -> review job
```

Other agents receive a submission/read credential, **not** the human-review
credential or GitHub token. Submitted descriptions remain working hypotheses.
A preview is not a released result; a released result is not proof that the
reported external claims are true. Failed, rejected and pending tasks remain
distinct from completed tasks.

## Current release scope

- Importable Python specialist client and authenticated, idempotent task API.
- Bounded inputs, explicit source lineage, conservative confidence ceiling,
  Harm Gate and durable human-reviewed report lifecycle.
- Source/preview-bound Knowing Field completion with independent human audit
  revisions and mandatory checks at approval and worker release.
- Existing validators, evidence pipeline and case studies as reusable methods.
- GitHub App owner sign-in and three named GitHub Actions operations on master:
  framework validation, claim-correction study and static-capture study.
- Source-bound offline static HTML capture with measured output and human review.
- Safe HTML display of evidence, captured PNGs, workflow status and artifact links.
- Separate public read-only Display Mode; a server is required for secure OAuth.
- Persistent human intelligence filing using the supplied numbered hierarchy,
  read/unread markers, flags and category colors, with independent revision and
  audit history. Opening an item marks it read; manual unread remains available.
  Existing and incoming items start in Inbox. Archive preserves an item; it
  does not delete it, verify it or complete its analysis.

## Explicitly out of scope

- Arbitrary agent-issued shell commands, webhook cloning/building, paid model
  calls, autonomous code changes or automatic approvals.
- GitLab OAuth, local password accounts, email-based identity merging,
  PostgreSQL identity storage and shared hard-coded master passwords.
  Existing GitLab push ingress is not GitLab sign-in.
- An asserted trained code-diff/screenshot verifier. Weight research is
  [recorded separately](docs/local-vision-weight-candidates.md); no model is
  installed or granted decision authority.
- Multiuser/tenant isolation, a public identity service, formal attestations,
  constant-time processing, infinite scale or unmeasured performance claims.
- Resuming the paused separate game build.
- Outlook/mailbox integration, real email delivery, copied private mailbox
  contents and automatically treating folder/category membership as evidence.

## Instructions for repository agents

1. Prioritize the full-stack sub-agent contract and supporting services.
   Develop the human control plane as a client of that architecture, not
   as a substitute for the analytical product.
2. Preserve working core behavior, the authoritative paper, license, resource
   packaging and backward-compatible entry points. Architectural changes
   must advance the service contract rather than introduce cosmetic rewrites
   or remove validated methods without justification.
3. Keep ingestion, analysis, human approval and external execution separate.
   An agent's output must never supply its own corroboration or execution grant.
4. Use typed, bounded contracts and repository-standard errors. Preserve
   histories and immutable input/result digests; never report acceptance as
   successful completion.
5. Wire every new capability through its client/API, storage, UI, installed
   package, documentation and tests where applicable.
6. Test the exact outcome: replay identity, permission separation, invalid
   requests, restart/tamper behavior, real captures and workflow artifacts.
7. Treat credentials as operator-managed secrets. Never put tokens/passwords
   in source, browser storage, public HTML, logs or artifact bundles.
8. Do not expand permissions, execution modes or identity providers without
   a new explicit scope decision and validation.
9. Maintain independent revision and audit mechanisms for human filing.
   Organizational changes must not mutate original input, analysis digests,
   lifecycle revisions, confidence, review authority or execution permissions.
10. Apply the fifth-pillar skill when revising any analytical surface. Agent
    context is unreviewed; only authorized human completion can satisfy the
    release gate. Presencing, source corroboration and record validation are
    different claims.

## Release acceptance

The release must demonstrate a caller submitting a task, receiving the same
job for a replay, reading an unreleased preview, being unable to approve it,
and receiving the durable result after a human review. The HTML runner must
dispatch only the three named operations and show GitHub acceptance separately
from the final run conclusion. Model-free capture must block scripts/network
and preserve measured failures for review. Live GitHub App login still needs
operator-created app credentials and installation; it must not be described
as validated until that real handshake has succeeded.
