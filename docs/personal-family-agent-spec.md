# Personal and family privacy, safety and rights agent

Status: PROPOSED PRODUCT SPECIFICATION / NOT IMPLEMENTED / NOT VALIDATED.

The owner requested a personal- and family-oriented agent, broader than claim
verification. The owner selected documentation and product-contract alignment first, with no
new protective implementation in this phase. This document is a derivative proposal, not a
replacement for the owner paper, private draft or existing released history.

The companion [protection guide](personal-family-protection-guide.md) develops
owner-oriented response options and proposed commitments from the private
draft. It does not adopt a new license, bind third parties or authorize filings.

## Purpose

Help people understand privacy and safety risks, organize evidence, research
potential rights and remedies, and prepare proportionate, human-reviewed plans.
Protecting rights is the objective, not a guarantee of legal protection,
physical safety, accurate attribution or successful enforcement.

The evidence specialist remains a supporting engine. Claim verification becomes
one capability within a broader service, not the identity of the whole product.
The six pillars remain reciprocal constraints on evidence and interpretation.
Knowing Field supports affected-person perspectives, dissent and human review;
software does not simulate presencing. Game Theory is optional, requires supplied
actors/actions/information/utility units/evidence, and cannot infer motives or
authorize action. Missing strategic inputs remain NOT_SUPPLIED.

## Private draft review

The owner supplied an 18-page "Repo Protections: Laws, Workflows & Decisions"
PDF dated October 10, 2026. Its extracted text was reviewed locally. The PDF
and extraction remain outside the repository; no personal details from the
draft should be published without separate review.

Retain its useful distinctions:

- Person, creative work, project name and platform are different subjects.
- Copying, naming confusion, impersonation, unwanted disclosure and threats
  need different factual questions and response routes.
- Preserve sources and competing explanations before drawing conclusions.
- A proposed response needs a reason, scope, limitations and human decision.
- Private incident records should not be stored in a public code repository.

Do not adopt the draft's legal or technical conclusions wholesale:

| Draft proposition | Required specification correction |
| --- | --- |
| Headers and hashes prove authorship, ownership or a date | A digest compares bytes. Authorship, identity, trusted time and ownership require separate evidence. |
| Brief quotation with credit is fair use | Credit and brevity alone do not decide fair use; the Copyright Office describes a case-specific, multifactor inquiry. |
| Every modified redistribution must have a different name | Do not add a blanket restriction to Apache-licensed code. Section 6 withholds trademark permission; specific naming claims require separate review. |
| An inventory in another local mirror is this checkout's ground truth | Verify this repository and revision independently; the draft's repository URL and inventory are not current-checkout findings. |
| Public disclosure eliminates every possible trade-secret/access claim | Do not make categorical historical or jurisdictional conclusions. Separate public contents, previously confidential material, disclosure timing and alleged acquisition. |
| Preservation means never deleting private records | Preserve analytical correction lineage without imposing indefinite personal-data retention. Provide explicit retention, deletion and legal-hold review. |
| Filing is the default after a checklist passes | Checklist completion is not legal judgment or authority. Preparation, human review and external execution remain distinct. |
| Family membership supplies consent | Each person's data and permissions are separate. Relationship, payment or household administration is not blanket access authority. |

Other draft assertions about court cases, platform rules, registration,
compensation, remedies and enforceability remain UNVERIFIED unless independently
reviewed against applicable primary sources. No new NOTICE, trademark declaration,
social-media policy, license restriction or legal filing is adopted here.

## Candidate capabilities

| Capability | Proposed assistance | Explicit boundary |
| --- | --- | --- |
| Privacy planning | User-selected data inventory, purpose, recipients, retention and disclosure review | No account scraping, background collection or automatic uploads |
| Account and identity safety | Review user-supplied alerts; prepare recovery and impersonation checklists | No passwords, recovery codes, impersonation accusations or automatic account changes |
| Scam and message assessment | Analyze voluntarily supplied messages, links and payment requests | No certainty from appearance; do not follow links or send payments automatically |
| Harassment and unwanted disclosure | Build a private, source-attributed incident timeline and possible reporting routes | No surveillance, retaliation, doxxing or automatic confrontation |
| Household device safety | Explain consented account/device settings and consequences | No covert tracking or automatic monitoring-software removal |
| Rights research | Show jurisdiction, source edition, elements, exceptions, enforcement actor and access limits | Legal information, not counsel, a verdict or complete national protection |
| Response preparation | Produce redacted drafts and review checklists for a chosen recipient | No complaint, takedown, notification, signature or filing without explicit authorization |
| Family coordination | Share selected records or tasks with a chosen person | No default household-wide view; no authority inferred from being a guardian |

Minor-specific features require separate research into age, capacity, applicable
law, guardian authority and the child's privacy and safety. Do not build a
child-monitoring feature by repurposing adult consent. Health, financial and
legal advice are not replaced by the agent.

## Safety and consent requirements

1. Ask whether the current device and communications channel are safe before
   suggesting sensitive activity. Do not assume a monitored device can be made
   safe through this application.
2. Do not automatically change passwords, remove software, disable sharing,
   confront someone or notify family. Such actions can alert another person,
   destroy evidence or increase danger.
3. Offer user-selected access to qualified support and emergency resources.
   The agent is not an emergency responder; recommendations must be appropriate
   to the supplied location and verified resource access.
4. Separate the affected person from a requester, helper, guardian, reviewer
   and execution approver. None of those roles implies the others.
5. Permissions must name person, purpose, record scope, recipient, expiry and
   revocation behavior. Refusal or revocation must not trigger family alerts.
6. New household membership must not expose older private records. Removal must
   stop future access; already exported copies cannot be recalled by a promise.
7. Sharing must preview exact fields, attachments and identifying metadata.
   Redaction is not automatically anonymization.
8. No hidden location tracking, keylogging, ambient recording, relationship
   scoring, political classification or speculative offender identification.

These are proposed requirements, not implemented controls.

## Data lifecycle and trust boundaries

```text
Voluntary, scoped intake
  -> minimum necessary private record
  -> source-access and provenance review
  -> bounded analysis with alternative explanations
  -> private preview and affected-person perspective
  -> separate human completion and release decision
  -> explicitly scoped sharing or execution approval
  -> confirmed outcome or explicit failure
  -> user-controlled retention and deletion review
```

For a future contract, distinguish:

- Case identity, affected-person identifiers, jurisdiction and safety context.
- Evidence facts, user reports, inferences and external-source access.
- Consent grants and revocations, independent of confidence and case status.
- Legal references: statute/policy/bill/court decision, source edition,
  inspected scope, applicability UNKNOWN and enforceability UNVERIFIED.
- Proposed action, recipient, exact payload preview, exposure risks, approval
  identity and expiry; execution receipt must report actual outcome.
- Private originals, redacted sharing copies and minimal audit events.

Do not embed private identifiers or case contents in public manifests, GitHub
issues, telemetry or static Pages assets. Do not promise "local-only" while
runtime dependencies, external models or other services make network requests.
Research queries must omit private incident details unless specifically approved.

Retention must include purpose and expiry, export, access revocation, deletion
of raw data and derived copies, backups and embeddings if introduced. A minimal
deletion audit must not preserve the deleted private text. Legal holds and
conflicting requests require explicit review, not indefinite silent retention.
Keep historical source artifacts intact; private-data deletion requirements
must be designed separately from immutable analytical correction lineage.

## Relationship to the current implementation

The current architecture explicitly excludes multiuser/tenant isolation.
Its single-owner review credentials and SQLite workflows are not evidence of
safe family isolation. Do not expose them to multiple family members as-is.

The existing specialist API, evidence methods, preview/release separation and
human control plane are candidates for reuse after contract review. The static
GitHub Pages verifier is not a private family case workspace. Preserve existing
entry points and validated methods while designing the new service.

Deployment, account model, custody, encryption/key recovery, offline operation,
family sharing and external model providers are NOT_SELECTED. No implementation
or migration should infer those decisions.

## Proposed contract handoffs

This table is a requirements map, not a new JSON schema or API. New fields and
routes require reviewed implementation and compatibility tests before use.

| Boundary | Required information or decision | Current/proposed distinction |
| --- | --- | --- |
| Private intake | Affected person, safe channel, purpose, authority, data minimization and retention | Proposed; no household identity or consent API |
| Evidence task | Bounded question, source descriptions, lineage and optional inquiry/model context | Existing [specialist contract](specialist-agent.md); caller labels remain assertions |
| Rights/process review | Jurisdiction, source edition/access, elements, exceptions, enforcement actor and missing facts | Proposed workflow using bounded legal references; no eligibility engine |
| Response draft | Specific requested remedy, recipient, redacted payload, risks and missing requirements | Proposed; guide templates are not submissions or sworn filings |
| Human completion/release | Exact evidence preview, inquiry revision and separate human report decision | Existing supporting lifecycle; not legal approval or sharing consent |
| External action | Explicit approver, exact recipient/payload/action, expiry and actual receipt | Not authorized by this proposal; existing GitHub study dispatch is a separate surface |
| Retention/deletion | Original/derivative/backup inventory, requested scope, conflicts and minimal deletion audit | Proposed private-data lifecycle; current pruning is not certified secure erasure |

### Distinct state vocabularies

- **Workflow lifecycle:** existing PENDING, RUNNING, AWAITING_APPROVAL,
  APPROVED, COMPLETED, REJECTED and FAILED concern evidence reports.
  COMPLETED does not mean a person is protected or an external action succeeded.
- **Source standing:** SOURCE-ESTABLISHED and UNVERIFIED describe inspected
  legal-source access in the catalogs, not legal enforceability.
- **Jurisdiction:** a US state name is a location/reference, not a lifecycle
  value, governing-law determination or uniform national right.
- **Permissions and action outcomes:** future consent, revocation, submission
  and remedy states must be independently defined and audited; do not overload
  report state, confidence or filing colors to represent them.

The protection guide remains pending owner editing. An edit may change proposed
requirements but cannot silently migrate permissions, modify source evidence,
adopt legal terms or authorize external action.

## Acceptance criteria before implementation release

- A second person cannot read, infer, export or mutate an unshared case through
  API, UI, search, caches, attachments or logs.
- Expired/revoked permissions fail closed; new members cannot inherit history.
- Declining sharing or help does not notify a potentially unsafe contact.
- Supplied allegations stay reports; unknown attribution stays unknown.
- Legal search failure stays UNVERIFIED; bills and outdated editions are not
  presented as current enforceable protections.
- No execution occurs from analysis, a checklist, family membership or release.
- Export previews match actual payloads; sensitive metadata is tested explicitly.
- Retention/deletion behavior is demonstrated across originals, derivatives,
  backups and any search index, not just a hidden UI row.
- Network behavior and third-party exposure are measured and disclosed.
- Coercive-control, compromised-device and unsafe-notification scenarios are
  tested without assuming that immediate technical remediation is safest.
- An independent access-boundary review and user acceptance against exact
  source/preview are required; passing unit tests is not a safety certification.

## Primary-source research record

This is a bounded first pass, not a fifty-state family-rights review. Source
access establishes only inspected text, not application to a person.

| ID | Source opened | Supported observation | Limits |
| --- | --- | --- | --- |
| PF-01 | [NIST Privacy Framework: getting started](https://www.nist.gov/privacy-framework/getting-started-0) | Privacy risk includes harms from data operations throughout collection-to-disposal; cybersecurity alone is insufficient. | Voluntary guidance; excerpt truncated after framework structure. No certification or complete control mapping. |
| PF-02 | [FTC: Stalkerware, What To Know](https://consumer.ftc.gov/articles/stalkerware-what-know) | Removing monitoring software can alert an abusive person; safety planning, safer communications and evidence considerations precede changes. | Fetch returned 403; ordinary browser displayed substantive guidance. Not evidence any user's device is monitored. |
| PF-03 | [Copyright Office: Copyright in General](https://www.copyright.gov/help/faq/faq-general.html) | Copyright concerns fixed expression; ideas and systems differ; registration has separate procedural significance. | General guidance, not a repository ownership finding or registration search. |
| PF-04 | [Copyright Office: Fair Use Index](https://www.copyright.gov/fair-use/) | Fair use is case-specific and multifactor; even quantity alone is not decisive. | Overview excerpt, not a court opinion or a verdict on any proposed use. |
| PF-05 | [Washington RCW 4.24.790](https://app.leg.wa.gov/RCW/default.aspx?cite=4.24.790) | Electronic impersonation provision includes consent, intent, injury, exclusions and limits on provider liability. | Statutory text opened; current case law and any particular person's elements not assessed. |
| PF-06 | [Repository Apache license](../LICENSE) | Sections 2, 4 and 6 separate copying permissions, redistribution conditions and trademark permissions. | Existing file inspected; no license amendment, trademark ownership or infringement finding. |

SEARCH RECORD: personal/family privacy-risk and draft-claim verification /
official web fetch, one targeted stalkerware discovery search, ordinary browser
and local draft/license reads / named sources above / six supporting sources
opened / limit hit yes: selected excerpts and scope / primary source opened yes
for listed observations / SOURCE-ESTABLISHED for inspected guidance and text
only; product effectiveness UNVERIFIED / all-state rights, family authority,
child-specific law, court status, platform policies and deployment design NOT
checked exhaustively.

FTC business-data and COPPA pages returned 403 through fetch; child identity-theft
guidance was not substantively opened in that initial pass. Subsequent parallel
research opened FTC child-identity guidance and the rendered IdentityTheft.gov
homepage; see the companion [protection guide](personal-family-protection-guide.md)
for source-attributed observations and limits. A 2023 COPPA snapshot does not
establish current requirements. CISA and Safety Net initial fetches exposed
navigation, title or incomplete content. They remain research leads,
not corroboration or support for new legal claims. NIST version 1.1 appeared as
an initial draft on the landing page; no final-version claim is made.

## Next research decisions

First select a narrow initial assistance area and deployment/access model.
Then deepen research into affected-person consent, minors/guardianship,
jurisdictional remedies, privacy threat models and safe response options for that
area. Expand the legal catalog without calling it complete protection.
Only after those decisions should a typed contract and implementation plan be
approved. No external filing, monitoring or account integration is authorized.
