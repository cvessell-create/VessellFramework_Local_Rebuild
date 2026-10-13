# GitHub-hosted agent discovery and public-safe analysis

This repository-defined v1 contract provides **public capability discovery,
fixed-corpus reference search and authenticated asynchronous analysis previews**.
It is not an anonymous API, an MCP/A2A server, live web search or a private
family-case service. AI/SI/coordinating agents may integrate with the contract;
discovery does not demonstrate adoption by any agent or search engine.

The personal/family [protection guide](personal-family-protection-guide.md)
remains an owner-review draft. This integration reuses supporting evidence
engines, not the proposed consent, safety or rights-enforcement layers.
It preserves the [vision](../VISION_AND_SCOPE.md) and
[professor packet](../PROFESSOR_README.md); SI remains product direction.

## Public discovery and search

- [Agent landing page](agents.html): human-readable capabilities and reference search.
- [Capability descriptor](agent-capabilities.json): repository-defined transport,
  operation list, input/result schemas, limits and deployment uncertainty.
- [Reference index](agent-reference-index.json): generated derivatives of 12
  explicitly allowlisted public documents, with source byte digests.

Search requires every case-insensitive letter/digit token on the same source
line, in corpus order. It returns at most ten hits, total matches, limit-hit
status, exact file/line and a source digest. Snippets are truncated at 1,000
characters; duplicate documents/lines are not independent evidence.
Zero results means **NOT FOUND IN SCOPE**, not absence everywhere.
No live primary sources, other repository files, private records or accounts
are searched. Matching a statute reference is not current-law verification.
Browser search runs locally over this public index, with no submission of
the query to the analysis workflow. Pages/CDN requests remain network access.
Do not type private case details into this public workspace.

Generate both public JSON files after editing an indexed source:

```bash
python -m vessell.hosted_agent --build-discovery .
```

The generator uses a fixed file list, not a recursive crawl. Wheel resources
contain the same generated index. Digests establish snapshot byte agreement,
not source truth. Master links can change; compare the source digest before
relying on a citation. These generated copies are not independent corroboration.

## Authorized Actions transport

[agent-analysis.yml](../.github/workflows/agent-analysis.yml) is separate from
the existing [owner control-panel workflow](github-control-panel.md).
Its three-operation allowlist and App interface are unchanged.
The new workflow accepts only `workflow_dispatch` for this exact repository,
`master`, and actor `cvessell-create`. It fails explicitly for another actor,
repository, ref or event. There is no anonymous intake, scheduled collection,
browser token or permission to read family records. Other agents require an
owner-authorized credential/context; a caller name is only a declaration.
Do not distribute the owner's credential to independent untrusted agents.

GitHub's dispatch documentation requires write access and a workflow on the
default branch. Workflow permissions here are `contents: read`; checkout
does not retain credentials. The owner must publish/review the workflow
before remote use. Local implementation does not prove deployed availability.

The only workflow input is `request_json`, a v1 JSON object of at most **32 KiB**:

| Operation | Payload | Result scope |
| --- | --- | --- |
| `evidence-analysis` | Existing [SpecialistTask](specialist-agent.md), 1–24 evidence rows; optional bounded field/game records | Reuses specialist analysis, VERY LOW ceiling; no human completion accepted as release |
| `claim-analysis` | Claim and 1–24 sightings | Existing claim classifier over uncorroborated supplied material |
| `spread-analysis` | Claim and 1–24 sightings | Existing spread heuristics, not intent/actor attribution |
| `job-analysis` | 1–24 postings, one employer/title/location | Existing posting-pattern heuristics, not confirmation of a real vacancy |
| `reference-search` | Query (1–200 characters), limit (1–10, default 5) | Fixed public reference corpus only |

Every request requires `contract_version: "1.0"`, a canonical lowercase UUID
`request_id`, and `data_classification: "public-non-sensitive"`. Unknown fields,
duplicate JSON keys, non-finite constants, unsupported operations, invalid
timestamps and schema violations fail; no success artifact is emitted.
Hosted sightings may omit `tier` (defaults to WORKING HYPOTHESIS) or explicitly
use WORKING HYPOTHESIS; SOURCE-ESTABLISHED and asserted official records are
rejected rather than promoted. Source URLs are not fetched or authenticated.
Evidence source IDs and optional declared models retain existing validation.

**The public/non-sensitive declaration is not a sensitive-data detector.**
An authorized caller can still put private content in an input. It may be
visible through workflow metadata, logs, GitHub events and artifacts. Never
submit private family narratives, children's details, credentials, medical
records or owner-private documents. Seven-day artifact retention is not a
deletion guarantee for logs, copies or previously downloaded files.
Public previews are technical artifacts, not authorized report publication.

### Local contract check

Install existing optional dependencies, then run either supplied fixture:

```bash
python -m pip install -e ".[core,ambient,verifier]"
python -m vessell.hosted_agent --request examples/hosted-agent-evidence.json --output preview.json
python -m vessell.hosted_agent --request examples/hosted-agent-search.json --output search-preview.json
```

These are synthetic/public-reference examples, not real incident verification.
Without `--github`, execution identity is null; do not label it a GitHub run.

### Owner-reviewed remote dispatch and retrieval

After authorized publication, an owner-context agent can use GitHub CLI:

```bash
gh workflow run agent-analysis.yml \
  --repo cvessell-create/VessellFramework_Local_Rebuild --ref master \
  --field request_json=@examples/hosted-agent-evidence.json
```

Or use authenticated REST `POST /repos/cvessell-create/VessellFramework_Local_Rebuild/actions/workflows/agent-analysis.yml/dispatches`
with `{"ref":"master","inputs":{"request_json":"<serialized v1 JSON>"}}`.
Consult the current GitHub REST version and response contract; do not assume
all API/client versions return the same dispatch response.

Dispatch acceptance is not analysis completion or report release. Locate and
inspect the exact run, then download its unique artifact:

```bash
gh run view RUN_ID --repo cvessell-create/VessellFramework_Local_Rebuild
gh run download RUN_ID --repo cvessell-create/VessellFramework_Local_Rebuild \
  --name agent-preview-RUN_ID-RUN_ATTEMPT --dir downloaded-preview
```

Require successful run completion, validate `preview.json` against the
descriptor's result schema, and check repository/ref/actor/source revision,
run ID/attempt, request UUID and digest against the intended request.
Run identity records GitHub execution metadata, not independently attested
caller/source identity. Request digests use canonical normalized JSON with
model defaults; compare the same normalization, not raw whitespace bytes.

Each valid output has state **UNRELEASED_PREVIEW**, `analysis_only: true`,
`report_released: false` and `execution_authorized: false`. Preview digest
binds exact canonical preview bytes. Missing corroboration remains
`FRAMEWORK STATE: DEGRADED — UNVERIFIED EXTERNAL CLAIM`.
Retries/re-runs are separate runs; a UUID is correlation, not durable
deduplication or replay protection. Downloaded files are not a durable
evidence store or an approval ledger.

No release/execution operation exists in this workflow. A real report must
enter the separately authenticated [human-review lifecycle](ambient-workflows.md)
with its actual sources and preview, source/preview-bound human Knowing Field
completion and a separate release decision. Merely copying a preview or
declaring approval is not that handoff. Field/game record completeness,
mathematical outputs, search matches and cohesion cannot bypass those gates.

## Primary-source research record and limits

This pass opened five official GitHub documentation pages and canonical
repository metadata. No third-party code or new package was imported;
workflow actions and Python extras reuse existing repository dependencies.

| Query / tool | Scope / count / limit | Primary opened / standing | Not checked |
| --- | --- | --- | --- |
| Exact repository / `gh repo view` | One repository / 1 / no limit hit | [Canonical metadata](https://github.com/cvessell-create/VessellFramework_Local_Rebuild) / SOURCE-ESTABLISHED for name and master | Live integration, account permissions, App handshake |
| Pages hosting / web fetch | One official page / 1 / no limit hit | [What is Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) / SOURCE-ESTABLISHED for static hosting | This landing page deployed or indexed |
| Dispatch prerequisites / web fetch | One official page / 1 / no limit hit | [Manual runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow) / SOURCE-ESTABLISHED for access/default-branch prerequisite | Actual owner token/dispatch |
| REST dispatch body/response / web fetch | Targeted workflow sections / 1 / page pagination used | [REST workflows](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event) / SOURCE-ESTABLISHED for inspected contract | Other API versions and live response |
| Workflow syntax / web fetch | Initial official excerpt / 1 / truncated after 3,500 characters | [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) / SOURCE-ESTABLISHED for YAML placement/run-name only | Full current syntax reference; remote runner |
| Artifact retrieval / web fetch | One official page / 1 / no limit hit | [Downloading artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts) / SOURCE-ESTABLISHED for read access/CLI retrieval | Actual retention/deletion and remote artifact |

SEARCH RECORD fields are represented above: query / tool / scope /
result count / limit hit / primary source opened / status / what was NOT checked.
This research supports a bounded implementation design, not adoption,
certification, live deployment or empirical family-protection efficacy.
