# Product direction

Apply `VesselFramework_Knowing_Field_SKILL_v0.1.md` and its source/audit records.
The current analytical architecture has five pillars; KNOWING FIELD complements
PARADOX, BOTTLENECK, DUAL LAYER and XFACTOR. Human completion against the exact
source and preview is mandatory before new report release, including pending
legacy workflows. Do not simulate presencing, fabricate participant accounts,
raise confidence from cohesion or retroactively rewrite released history.

Consult `VISION_AND_SCOPE.md` before architectural changes. Develop the product
as a full-stack SI sub-agent whose implemented core provides bounded,
provenance-aware evidence analysis through a callable agent contract. The
email-inspired HTML workspace is its human-facing control plane, not the
primary product or a replacement for the specialist's supporting services.

Maintain distinct boundaries among authenticated task intake, bounded analysis,
durable evidence and provenance history, human review and report release,
and explicitly authorized execution. Caller requests cannot confer
corroboration, approval or execution authority. Owner-authorized GitHub Actions
tasks and operator-approved offline captures remain separate from the pure
analysis worker.

Persistent filing metadata requires independent revisions and audit history.
Folders, read/unread markers, flags and category colors organize information;
they must not mutate evidence, analysis digests, lifecycle versions, confidence
or authorization. Preserve the author-source paper and validated methods.
Describe SI as product direction, not as an established superintelligence
capability or a substitute for empirical validation.

# Search Gate for coding agents

Follow `VesselFramework_Search_Gate_SKILL_v0.1.md` before repository/identity,
licence/IP, live/current, code/safety-check, personal-memory/external-account,
version/dependency and people/organisation claims. It is subordinate to Evidence
Assurance, the provenance firewall and the Harm Gate.

- No search, no claim. Search summaries remain WORKING HYPOTHESIS until an
  applicable primary source is opened and cited; summaries cannot upgrade themselves.
- Look up owners and repositories rather than guessing. If direct lookup fails,
  search by name, open canonical metadata and state the corrected name before writes.
- Before importing third-party code, art, audio or data, search its licence and
  confirm the exact material against primary `COPYING`/`LICENSE` or the rights-holder
  grant. Check project compatibility with `vf-search-gate check-import`; never
  import proprietary, unknown or incompatible material. Record files, sources,
  licences, credit, changes and any owner-approved relicensing decision in an
  attribution file. Search Gate clearance never overrides licence obligations.
- Search and cite implementing files/revisions before claiming a code or safety
  check exists; do not confuse existence with tested effectiveness.
- Report scope, result counts, search limits and what was not checked. Zero
  results means NOT FOUND IN SCOPE, not “does not exist”.
- Never invent inaccessible accounts or memories. Say plainly what cannot be
  accessed and ask the user to paste the material.
- Treat snapshots as snapshots, never as final outcomes without primary confirmation.
- Derivative copies are not independent corroboration; use the provenance firewall.
- Include SEARCH RECORDs in PR descriptions for external facts or imports:
  `query / tool / scope / result count / limit hit / primary source opened (y/n) / status / what was NOT checked`,
  plus primary citations and corrected names where applicable.

Unverified external claims return
`FRAMEWORK STATE: DEGRADED — UNVERIFIED EXTERNAL CLAIM`.
The deterministic offline checker evaluates supplied records, not their truth.

# Token budget

The owner often reviews from a phone. Keep work and output lean without
weakening any check above.

- Keep PR descriptions short: what changed, test count, merge order, and
  anything unverified. Put long inventories in a collapsed `<details>` block.
- Bundle related small fixes into one task and one PR instead of separate sessions.
- Don't re-read or re-run unchanged work; run targeted tests while iterating,
  then the full suite once before finishing.
- Don't paste large files, logs or diffs into PR text; link or cite paths instead.
- Never skip the Search Gate, Harm Gate, tests or verification to save tokens.
