# Author-source reconciliation: why the repository needed correction

Date: 2026-10-04.

## Source authority and scope

The user identified the supplied `claim-correction-case-study.md` as what
they actually wrote, in contrast with the LLM-produced paper. That explicit
source designation governs this correction; fluency, length, a DOI string,
or earlier repository placement cannot substitute for author authorization.

The canonical [paper](claim-correction-case-study.md) is restored byte-for-byte
from that supplied file, including its original wording and references.
The [machine-readable record](paper-source-reconciliation.json) pins its
SHA-256 and the superseded versions. It contains no private filesystem paths.
The earlier expanded repository text remains inspectable through Git at
commit `b4b6b022ae0c191ac333d4e423d67fed64bd7af2`, rather than being silently
erased or presented as the author's current paper.

This artifact verifies source fidelity, not the incident's independent truth.
The author-source document reports an incident and a manual correction.
Original external logs and configurations have not been supplied here.

## Observed differences and corrective decisions

| Area | Supplied author source | Superseded repository version | Correction and reason |
|---|---|---|---|
| Title and thesis | Unverified sentence becoming system behavior; structural prevention and correction | AI-to-SI title and capability-oriented framing | Restore the author's title; do not add an intelligence classification |
| Subject and attribution | Describes "the subject"; origin of the statement explicitly uncertain | First-person account, analyst/subject identification, Meta Muse workflow attribution | Preserve reported speech and uncertainty; do not infer identities or platform details |
| Method and historical evidence | Reports manual repair of three scheduled configurations, goal file and memory | Adds a parallel assistant/framework experiment and historical hashed correction event | Remove additions from canonical paper; current local tests are not historical logs |
| Search incident | No author-name lookup incident | Adds a photographed-screen/citation-search account | Remove historical attribution; keep the existing search tests only as synthetic fixtures |
| Mechanism table | Six mechanisms: intake, corroboration, gate, status, dependents and disavowal | Adds causal-path delivery and negative-finding rows | Restore six rows; retain tested extensions separately, not as authored text |
| Playbook | Six practical prevention/correction rules | Recasts the rules around causal-order literature and SI operation | Restore practical rules and separate implementation analogies |
| References | ICD 203, Doyle, de Kleer, Parasuraman/Riley, Sambasivan et al., framework files | Adds hallucination, causal-order, platform and policy citations; adds DOI/private-repo assertions | Restore the source's bibliography; no fresh bibliographic validation or DOI attribution inferred |
| Evaluation input | Author-designated Markdown source | Executable spec pins a different DOCX | Pin the supplied Markdown; retain old hashes as historical lineage |
| Proof language | Includes "structurally impossible" and "proof" | Further expands formal/SI and historical outcome claims | Preserve actual authored phrases, but explicitly limit software evidence in evaluation documentation |

The observed failure is source substitution and attribution drift: additions
in an LLM-expanded document were promoted into governing doctrine and historical
claims. The local files establish that textual mismatch. They do not establish
the model's internal reason for producing it or the truth of every added claim.
Absence from the supplied paper means "not supported by this source," not
necessarily "false everywhere."

## Repository changes

- Restored the canonical paper without inserting editorial caveats into it.
- Corrected source identity in the executable
  [case-study specification](../case_studies/claim_correction/spec.json).
- Reconciled the [README](../README.md),
  [references](references.md),
  [doctrine matrix](traceability/doctrine_code_matrix.md), and
  [operational study](operational-case-studies.md).
- Removed historical attribution from negative-finding implementation
  docstrings and test descriptions. Updated report wording so it no longer
  describes the restored canonical paper as local-only. Runtime policies and
  scenario behavior remain unchanged.
- Added [source-integrity regression tests](../tests/test_paper_source.py).
  Editing the canonical paper now fails a pinned-digest check; an intentional
  source revision needs an explicit provenance update, not a silent rewrite.

No new external research was used to amend the author's paper. Useful existing
causal-order, negative-finding and hash-chain features remain available as later
implementation extensions. Removing unsupported attribution is not a reason
to remove working safeguards.

## Evidence boundaries

The current controlled comparison covers five reconstructed constraint
consumers and two synthetic positive-control consumers. Its acceptance
requirements are zero unsupported consequential uses in the framework arm,
two permitted corroborated control uses, seven correction read-backs and zero
original framework snapshots remaining. Those requirements describe managed
local files, not actual employer systems or the historical assistant.

Dependency coverage is limited to registered consumers. A registry cannot
discover every unregistered copy. Acknowledgment alone is not external repair;
the adapter verifies local writes by read-back. Hash chains are not a
machine-checked distributed proof or signed third-party attestation.
An official-record flag is a declared fixture/source classification, not
authentication of an external institution. Revalidation fields do not imply
an autonomous scheduled service. The broader game-pattern workflow remains a
later adaptation, not part of the September paper.

Earlier evaluation results remain pinned to their original versions. New
evaluation output records the corrected source/spec hashes; no old result is
rewritten to look as though it originally used this author-source document.

## Verification performed

The restored paper passed a byte comparison with the supplied author file.
The superseded document's hash was checked against its retained Git revision.
The corrected-source comparison passed: five unsupported uses blocked, two
corroborated control uses permitted, seven files corrected/read back, zero
original framework snapshots remaining. A separate verification process
reopened all seven saved framework receipts successfully.

Source-integrity tests pin both the canonical text and the corrected spec.
Final validation passed: 376 regression tests, focused Ruff checks, strict
Mypy checks for the touched runtime modules, all 285 source-manifest entries,
and diff whitespace checks. One existing Starlette/httpx deprecation warning
remains. Results from earlier releases were not used as a substitute.
