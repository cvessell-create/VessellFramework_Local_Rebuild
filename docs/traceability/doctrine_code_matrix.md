# Doctrine-to-Code Traceability Matrix (Initial)

Purpose: provide committee-visible evidence that doctrine claims are mapped to executable behavior and test coverage.

| Doctrine requirement | Code implementation | Conformance test | Status |
|---|---|---|---|
| Distinguish SOURCE-ESTABLISHED, FRAMEWORK SYNTHESIS, WORKING HYPOTHESIS, ILLUSTRATIVE evidence classes | vessell/app/pipeline.py status parser and counts | tests/conformance/test_program_pipeline.py::test_source_status_distinction_is_preserved | Mapped |
| Repeated reporting from one root must not inflate independent stream count | vessell/provenance.py + vessell/app/pipeline.py independent root handling | tests/conformance/test_program_pipeline.py::test_repeated_reporting_does_not_inflate_independence | Mapped |
| Missing lineage must not be treated as independence | vessell/provenance.py unresolved parent state + vessell/app/pipeline.py confidence ceiling logic | tests/conformance/test_program_pipeline.py::test_confidence_is_capped_when_lineage_unresolved | Mapped |
| Emit deterministic machine/human outputs for case review | vessell/app/reporting.py + vessell/app/main.py output writers | tests/conformance/test_output_snapshot.py (byte-identical reproduction, content landmarks, dependent registration) | Mapped |
| Trace maskirovka convergence through shared provenance graph | vessell/provenance.py assess_maskirovka_convergence + vessell/app/pipeline.py | tests/test_provenance.py + tests/conformance/test_maskirovka_convergence.py (cross-domain: cyber, news, supply-chain) | Mapped |

## Next Matrix Expansion

Completed 2026-10-10: Decision Provenance chain rows and failure-class
benchmark rows added below. External-validation row references remain
pending benchmark outcomes review.

## Decision Provenance Chain

The chain every operational use of a claim must travel: intake → gate →
use registers itself → correction propagates to all registered users in
causal order. Each link is executable and tested.

| Chain link | Code implementation | Conformance test | Status |
|---|---|---|---|
| 1. Intake tags the claim (source/tier/kind/uncertainty) | `vessell.provenance.intake_claim`; `vessell.validation.require_provenance_fields` | `tests/test_doctrine_reconciliation.py::test_require_provenance_fields_rejects_untagged_records`, `test_intake_records_kind_and_uncertainty` | Mapped |
| 2. Consequential use passes the gate (fails closed) | `vessell.provenance.gate_for_use` / `require_gate`; stale CORROBORATED claims blocked | `tests/test_doctrine_reconciliation.py::test_require_gate_raises_instead_of_returning_false`, `test_stale_corroborated_claim_blocked_for_consequential_use` | Mapped |
| 3. Every operational use registers itself as a dependent | `vessell.provenance.register_dependent` on pipeline results, reports, weight records, scan imports, defense plans, remediation proposals | `tests/test_doctrine_reconciliation.py::test_pipeline_intakes_evidence_and_links_result`, `test_propose_remediation_with_claim_registers_dependent`, `test_weight_set_registers_dependents_against_claim`; `tests/conformance/test_output_snapshot.py::test_end_to_end_outputs_register_dependents` | Mapped |
| 4. Correction is delivered to every registered dependent in causal order | `vessell.provenance.deliver_correction` / `propagate_correction(..., correction_id=)`; `confirm_dependent_update` verifies receipt; `CausalOrderingError` on violation | `tests/test_causal_paths.py` (11 tests) | Mapped |
| 5. Deterministic outputs make the chain auditable end-to-end | `vessell/app/main.py` + `vessell/app/reporting.py` writers | `tests/conformance/test_output_snapshot.py` (byte-identical reproduction) | Mapped |

## Failure classes (benchmark-linked)

Each failure class names how the method can fail; each row pins the
control that prevents it and the test that proves the control holds.

| Failure class | Control | Benchmark / test | Status |
|---|---|---|---|
| Governance: consequential use without authorization | `gate_for_use` / `require_gate` fail closed; explicit named waivers (`record_waiver`) are the only bypass | `tests/test_doctrine_reconciliation.py::test_require_gate_raises_instead_of_returning_false`; waiver tests in `tests/test_provenance.py` | Mapped |
| Authority: asserting what the evidence does not support | Verification verdict ladder (VERIFIED → UNVERIFIABLE); SINGLE_SOURCE/UNVERIFIABLE claims stay gated; negative findings require ≥2 independent search paths | `tests/test_verify.py` (corroboration scoring, official-record rule, independence discount; 10 Section-1 gate tests); `tests/test_doctrine_reconciliation.py::test_verify_and_record_unverified_stays_gated` | Mapped |
| Efficacy: silent degradation on thin intake | Degradation is a labeled output, never silent: unresolved lineage caps confidence and blocks convergence; missing timestamps degrade burst detection with a label | `tests/conformance/test_program_pipeline.py::test_confidence_is_capped_when_lineage_unresolved`; `tests/conformance/test_maskirovka_convergence.py::test_unresolved_provenance_never_reads_as_independence` | Mapped |
| Operator risk: harm from acting on the output | Harm Gate and Forward-Posture ladder govern what may be done; analytical posture stays distinct from forecast; remediation requires named approval + change ticket | `vesselframework_case_runner.py::evaluate_harm_gate`; `tests/test_remediation_orchestrator.py`; `tests/test_doctrine_reconciliation.py::test_propose_remediation_with_claim_registers_dependent` | Mapped |

## Causal-path correction semantics (Section 4, redone 2026-09-30)

Grounded in Lamport (1978) happens-before and Castello/Redmond/Kuper (2024) causal separation diagrams: causal relationships are witnessed by the paths information follows.

| Section 4 rule | Code implementation | Conformance test | Status |
|---|---|---|---|
| 4. Correction carries its causal predecessor (the witnessed path) | `vessell.provenance.ClaimRecord.causal_path` / `causal_predecessor()`; stamped by `disavow()` (chains across correction-of-correction; falls back to `supersedes` for legacy records) | `tests/test_causal_paths.py::test_disavow_correction_carries_causal_path`, `test_causal_path_chains_across_correction_of_correction`, `test_causal_predecessor_falls_back_to_supersedes_for_legacy_records` | Mapped |
| 5. Dependents record HOW the claim reached them | `vessell.provenance.register_dependent(..., via=)` — the witnessed path (artifact + location + via) | `tests/test_causal_paths.py::test_register_dependent_records_via_witnessed_path`, `test_via_defaults_to_empty_for_existing_callers` | Mapped |
| 5. Causal-order delivery; no silent out-of-order completion (causal broadcast, Redmond et al. 2022) | `vessell.provenance.deliver_correction()` / `propagate_correction(..., correction_id=)` (delivery-order guard); `confirm_dependent_update(..., correction_id=)` (never-delivered + application-order guard); `CausalOrderingError` | `tests/test_causal_paths.py` (11 tests: delivery stamping, never-delivered rejection, out-of-order delivery/application rejection, wrong-claim rejection, causal-order happy path) | Mapped |

## Meta-note mechanism (Section 1: the analyst's miss, 2026-09-30)

| Section 1 rule | Code implementation | Conformance test | Status |
|---|---|---|---|
| A negative existential ("no X exists") enters UNVERIFIED and may not be reported/operationalized until ≥2 independent search paths corroborate the absence; every attempted path is recorded provenance | `vessell.verify.SearchPath`, `record_search_path()`, `search_paths()`, `gate_negative_finding()` / `require_negative_finding()` (independence = distinct strategy+source; any hit contradicts the absence; `MIN_ABSENCE_PATHS = 2`) | `tests/test_verify.py` (10 tests incl. the Castello worked example end-to-end) | Mapped |

## Tradecraft standards (ICD 203; ICPM-2020-200-01)

| Tradecraft standard | Code implementation | Conformance test | Status |
|---|---|---|---|
| ICD 203: properly describe the quality and credibility of underlying sources; properly express and explain uncertainties | `vessell.verify.verify_claim` — tier-weighted independent-root counting, independence discounting, official-record rule; verdicts express uncertainty. `gate_negative_finding()` / `require_negative_finding()` — recorded search paths are the source-quality description for negative findings; the gated-or-cleared outcome is the expressed uncertainty | `tests/test_verify.py` (corroboration scoring, official-record rule, independence discount; 10 Section 1 gate tests incl. the Castello worked example) | Mapped |
| ICPM-2020-200-01: revision/recall notices go to *all recipients of the original product* | `vessell.provenance.deliver_correction()` / `propagate_correction(..., correction_id=)` — correction delivered to every registered dependent in causal order; `confirm_dependent_update` verifies receipt (`CausalOrderingError` on never-delivered or out-of-order) | `tests/test_causal_paths.py` (delivery stamping, never-delivered rejection, out-of-order delivery/application rejection, causal-order happy path) | Mapped |

## Claim-Correction Playbook (governing doctrine: docs/claim-correction-case-study.md)

| Playbook step | Code implementation | Conformance test | Status |
|---|---|---|---|
| 1. Tag at intake | `vessell.provenance.intake_claim` (source/tier/kind/uncertainty/observed_at); `vessell.validation.require_provenance_fields` rejects untagged records | `tests/test_doctrine_reconciliation.py::test_require_provenance_fields_rejects_untagged_records`, `test_intake_records_kind_and_uncertainty` | Mapped |
| 2. Corroborate before operationalizing | `vessell.provenance.gate_for_use` / `require_gate`; `vessell.verify.verify_and_record`, `analyze_planted_news_and_record`, `detect_ghost_job_and_record`; `filter_ghost_jobs` gates LIKELY_GHOST exclusion | `test_verify_and_record_mirrors_verdict_in_claim_standing`, `test_verify_and_record_unverified_stays_gated`, `test_filter_ghost_jobs_gates_the_exclusion` | Mapped |
| 3. Explicit waivers | `vessell.provenance.record_waiver` (named/dated/reasoned); orchestrator `approve()` requires approver + change ticket | `tests/test_provenance.py` (waiver tests) | Mapped |
| 4. Disavow by supersession, never erasure | `vessell.provenance.disavow` (original kept, correction linked; kind/uncertainty/valid_until inherited) | `test_disavow_correction_inherits_kind_uncertainty_valid_until` | Mapped |
| 5. Propagate, then verify the update landed | `register_dependent` on every operational use (pipeline results, reports, weight records, scan imports, defense plans, proposals); `confirm_dependent_update` / `pending_corrections` | `test_dependent_confirmation_workflow`, `test_pipeline_intakes_evidence_and_links_result`, `test_scanner_import_claim_content`, `test_defense_plan_carries_corroborated_claim`, `test_propose_remediation_with_claim_registers_dependent` | Mapped |
| 6. Re-validate on schedule | `ClaimRecord.valid_until` / `is_stale` / `revalidate_claim`; stale CORROBORATED claims fail closed for consequential use | `test_stale_corroborated_claim_blocked_for_consequential_use`, `test_revalidate_claim_clears_staleness_and_keeps_audit_trail`, `test_claim_without_valid_until_never_goes_stale` | Mapped |
| Causal order as data (Section 4) | `vessell.provenance.record_event` / `claim_events` / `verify_event_chain` — every lifecycle transition hashed into a per-claim SHA-256 chain (each event commits to its predecessor's hash); tampering, reordering, or deletion breaks verification | `tests/test_provenance_events.py` (genesis event, full lifecycle chain, tamper/reorder/removal detection, reset clears log) | Mapped |
