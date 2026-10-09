---
name: vessel-framework-search-gate
description: >
  Require scoped search and primary confirmation before external or code-existence
  claims and third-party imports. Subordinate to Evidence Assurance, the Provenance
  Firewall and the Harm Gate; search clearance never authorizes consequential action.
---

# VesselFramework Search Gate v0.1

**Status: NEW / PROSPECTIVE / NOT VALIDATED**

## Trigger table

| Claim type | Required search | Required primary confirmation |
|---|---|---|
| Repo/identity | Direct owner/repository lookup; if it fails, search by name | Open the canonical repository metadata; state any corrected owner/name before a write |
| Licence/IP | Search the exact material, version and applicable licence | Open its primary `COPYING`/`LICENSE` or rights-holder licence grant; check file-specific exceptions and project compatibility |
| Live or current facts | Search for current, time-stamped observations | Open the official record or direct primary source; record observation time and event state; a snapshot is not a final result |
| Code/safety-check existence | Search the relevant code and tests at the relevant revision | Open and cite the implementing file/lines; distinguish presence from execution or effectiveness |
| Personal memory or external account | Search only actually accessible, authorised material | Open the original message/record; if inaccessible, say so and ask the user to paste it |
| Version/dependency | Search the exact package and release/version | Open the upstream release metadata and applicable lockfile/package manifest; distinguish latest from installed |
| People/organisations | Search the exact identity and relevant context | Open a primary official record or first-party statement; distinguish its assertion from independently verified truth |

## Evidence mapping and authority

- Search snippet or summary → **WORKING HYPOTHESIS**.
- Opened primary source → **SOURCE-ESTABLISHED**, only for what that source establishes.
- Inaccessible material → **UNVERIFIED**.
- Derivative copies of one source are not independent. Reuse the shared provenance
  firewall (`vessell/provenance_firewall.py`) and Evidence Assurance rather than
  counting URLs or search results as independent roots.
- Search clearance is a prerequisite, not a truth, independence, effectiveness,
  legal-advice or permission-to-act verdict. The Harm Gate remains authoritative.

## Licence classes and import policy

| Class | Policy |
|---|---|
| PERMISSIVE | Preserve licence, attribution and applicable notices (MIT, Apache-2.0, BSD) |
| ATTRIBUTION | Credit source, licence and changes (CC-BY-4.0) |
| SHARE-ALIKE | Art, audio and data may stay separate with credit and their own licence; adaptations retain share-alike terms (CC-BY-SA-4.0); not cleared as code |
| COPYLEFT-CODE | Import only into a compatible project, or after owner-approved compatible relicensing; record the decision and chosen version before importing |
| PROPRIETARY | Block import; unknown or unsupported licences also count as blocked |

Compatibility is version-sensitive: GPL-2.0-only is not GPL-3.0; GPL-2.0-or-later
can select a compatible later version. AGPL obligations are not satisfied by a
GPL-only project. Do not infer a licence for a file from the project's name.
Record every imported file, primary licence source, credit, modifications and
any owner-approved relicensing decision in the project's attribution file.
The offline classifier is conservative and rejects unsupported identifiers and
compound expressions; it does not replace reading the licence.

## Output contract

`SEARCH RECORD: query / tool / scope / result count / limit hit / primary source opened (y/n) / status / what was NOT checked`

Name the search revision, account, date, file set or repository scope. Report
caps (for example, 10 results), truncated responses and inaccessible sources.
Cite the opened primary source; record the corrected name where applicable.
Do not silently broaden a scoped observation into a universal claim.

The JSON record uses `query`, `tool`, `scope`, `result_count`, `limit_hit`,
`primary_source_opened`, `status` and `what_was_not_checked`, with optional
`primary_source` citation and `corrected_name`. Supply records for **one exact
claim** to `evaluate_claim`; unrelated primary records cannot clear another claim.
Status values are `WORKING HYPOTHESIS`, `SOURCE-ESTABLISHED` and `UNVERIFIED`.

`vessell/search_gate.py` and `vf-search-gate` evaluate these supplied records without
network access. A positive, opened, cited primary record marked SOURCE-ESTABLISHED
clears the search prerequisite; summaries stay HYPOTHESIS ONLY; inaccessible or
empty searches return UNVERIFIED; no records returns BLOCKED. Limit hits and
unchecked scopes remain caveats even after clearance. The checker cannot
authenticate the record, infer claim relevance, establish freshness or perform
the search itself. Agents must perform and accurately record those steps.
`check_import` checks licence compatibility only; a CLEARED result still requires
the primary licence verification, attribution and recorded decision above.

## Hard rules

1. **No search, no claim.**
2. **Summaries never upgrade themselves.**
3. **Not found ≠ doesn't exist.** Say **NOT FOUND IN SCOPE** and name that scope.
4. **Never fabricate inaccessible content.**
5. **Correct names before writes.**
6. **Licence-blocked material is never imported.**
7. **Local history is not automatically authorized.** Use only user-exported
   records or explicit-consent capture. Never scrape private VS Code/Copilot
   stores or collect raw keystrokes, credentials, or unrelated file contents.

Unverified external claims return:
`FRAMEWORK STATE: DEGRADED — UNVERIFIED EXTERNAL CLAIM`.

## Worked examples from the supplied session

These are case inputs from the operator's session, not fresh searches or current
licence findings. Their facts must be searched and primarily confirmed again
before an actual import or external claim.

1. **Repository identity.** A direct lookup of
   `Cvessell-create/Vessellframework_Localrebuild` fails. Search by name finds
   `cvessell-create/VessellFramework_Local_Rebuild`. Open the canonical metadata,
   state that corrected name before writing, and retain both search scopes.
   Failure of the first lookup alone is NOT FOUND IN SCOPE, not proof of absence.
2. **Licence before import.** The supplied case identifies D&D 5e SRD 5.1 as
   CC-BY-4.0: allow with credit only after opening the primary grant. It identifies
   Battle for Wesnoth code as GPLv2+ and its art, music and unit data as CC BY-SA
   4.0: verify applicable primary files separately; block code for an Apache
   project, allow compatible GPL code, and keep credited assets under their own
   licence. The supplied Warhammer 40k/Games Workshop material is proprietary:
   block import. For the owner-approved `hail-to-the-analyst` GPL decision,
   record approval, chosen compatible licence and scope before copying code.
   This example does not relicense VesselFramework.
3. **Live facts.** An NHL search summary reports a score, but primary pages cannot
   be opened. Return HYPOTHESIS ONLY, state that it may be a mid-game snapshot,
   and never label it final. Opening a snapshot later does not establish finality.
4. **Inaccessible account.** A request to search an inaccessible Claude account
   returns UNVERIFIED. Say plainly that the account is inaccessible; ask for pasted
   material. Never invent messages, games or memories supposedly found there.
5. **Code before claim.** Before asserting a safety check exists, search code,
   open and cite its implementing file and revision, and identify what tests were
   inspected. A cap of 10 results must be disclosed; unopened files and other
   branches remain explicitly unchecked. Presence does not prove effectiveness.
6. **Absence isn't proof.** A search of two named repositories for game terms
   yields zero results. Report NOT FOUND IN SCOPE: those repositories and terms.
   Other accounts, Claude and local files were not checked; do not say the game
   does not exist.
