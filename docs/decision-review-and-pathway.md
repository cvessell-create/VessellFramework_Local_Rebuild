# Decision review and development pathway

**Status:** Source-bounded review, October 8, 2026. This reviews durable
repository records, not private model reasoning or a complete conversation
transcript.

## Scope and limits

The review covers the local repository checkout, the user's supplied workflow
status excerpt, and the files cited below. A session-history query limited to
the prior 30 days and matching the exact phrases “decision graph,” “game theory,”
or “chain of thought” returned no rows. GitHub job logs, PR review comments,
other accounts/branches, and private chain-of-thought were not available or reviewed.
The supplied status excerpt reports successful CI and CodeQL runs and a merge of
PR #11; those statuses were not independently confirmed from run logs here.

Repository searches used `rg` on checkout revision
`6304f576ac1364715c02d56e1cfeaf0f5840eb43`. Targeted primary files were opened,
but capped search output means this is not a line-by-line audit of every match
or every branch.

**SEARCH RECORD 1:** query regex
`decision|rationale|alternatives|open questions|chain.of.thought|reasoning trace`
/ repository `rg` / Markdown files at checkout revision
`6304f576ac1364715c02d56e1cfeaf0f5840eb43` / 253 matches in 49 files / yes,
display capped at 140 results / primary sources opened: yes / source-bounded
findings / files on other branches, external accounts and hidden reasoning NOT
checked.

**SEARCH RECORD 2:** query regex `decision|rationale|chain.of.thought|reasoning trace`
/ repository `rg` / Python, schemas and tests at checkout revision
`6304f576ac1364715c02d56e1cfeaf0f5840eb43` / 157 matches in 34 files / yes,
display capped at 100 results / primary sources opened: yes / source-bounded
findings / GitHub job logs, PR comments, files on other branches, external
accounts and hidden reasoning NOT checked.

**SEARCH RECORD 3:** query
`t.user_message ILIKE '%decision graph%' OR t.user_message ILIKE '%game theory%' OR t.user_message ILIKE '%chain of thought%'`
/ `session_store_sql` / accessible session history, last 30 days, maximum 20 rows
/ result_count: 0 / limit_hit: no / primary_source_opened: no / status: NOT FOUND
IN SCOPE / what was NOT checked: other time periods, hyphenated variants,
private accounts and hidden reasoning.

## Conclusions

1. **The recorded architectural direction is coherent.** The current vision
   treats **VessellFramework** as a callable, provenance-aware evidence
   specialist, with the HTML workspace as its human control plane. Some retained
   skill filenames use the historical `VesselFramework` spelling. The current
   architecture distinguishes task intake, bounded analysis, durable evidence,
   human release, and authorized execution. It places GAME THEORY alongside the
   existing pillars; KNOWING FIELD completion remains a human release
   prerequisite. See [`VISION_AND_SCOPE.md`](../VISION_AND_SCOPE.md) and
   [`README.md`](../README.md).
2. **The decision-graph work is bounded, not an authority engine.** The
   Game Theory audit identifies motive attribution, information structure,
   model inputs, and oversight as design risks. Its response is source-linked
   conditional models, explicit limits, and continued human review. The
   specialist contract describes this as preview analysis, not corroboration,
   approval, or execution. See
   [`docs/game-theory-framework-audit.md`](game-theory-framework-audit.md),
   [`docs/specialist-agent.md`](specialist-agent.md), and
   [`VesselFramework_Game_Theory_SKILL_v0.1.md`](../VesselFramework_Game_Theory_SKILL_v0.1.md).
3. **Tests support implementation claims, not empirical efficacy.** The kernel
   bounds inputs and reports conditional results; tests cover exact calculations,
   malformed inputs, source binding, replay identity, and unchanged confidence
   and release state. These establish tested software behavior for those cases,
   not truth of supplied sources, human decision improvement, or deployed
   effectiveness. See [`vessell/game_theory.py`](../vessell/game_theory.py) and
   [`tests/test_game_theory.py`](../tests/test_game_theory.py).
4. **There is an existing decision-provenance concept to build on.** The
   historical combined framework describes a Decision Provenance Chain from
   signal through evidence to decision and feedback. The current pathway should
   connect that concept to the specialist's versioned evidence and review
   lifecycle rather than create a competing “reasoning” subsystem. Its older
   five-pillar wording should not override the current six-pillar vision.
   See [MetaMatrix section 4: The Decision Provenance Chain](../VesselFramework_MetaMatrix_Framework_v3.8_v3.9_Combined.md#4-the-decision-provenance-chain-cross-domain-extension).
5. **The reviewed record does not expose the author's private decision process.**
   It supports evaluating decisions that were recorded in source, contracts,
   tests, and supplied status snapshots—not reconstructing unshared reasoning
   or attributing intent. The continuation reconciliation likewise separates
   owner-shared requests, observed code, and unverified claims; see
   [`docs/game-theory/continuation-reconciliation.md`](game-theory/continuation-reconciliation.md).

## Review assessment

**Strong choices:** preserving original sources and separating derivatives;
adding strategic analysis only when actors, actions, information, utility units,
and evidence are declared; keeping calculations conditional; retaining
source-bound human completion and separate release authority; and treating
tests, source integrity, empirical effects, and authorization as different
claims.

**Main improvement opportunity:** make decision provenance easy to review
end-to-end. The relevant policy, model, audit, code, tests, and workflow status
are documented in different places. For consequential changes, add a compact
decision record that links the owner's stated need to source revisions,
alternatives, implementation, test/evaluation results, unresolved risks, and
the human release decision. Do not rewrite historical decisions or silently
upgrade the evidence status of a prior release.

This is an auditable rationale summary, **not hidden chain-of-thought**. Do not
persist private internal reasoning, fabricate a thought transcript, or treat
longer reasoning text as stronger evidence. Record reviewable inputs, concise
reasons, alternatives, uncertainty, outcomes, and provenance instead.

## Proposed pathway

1. **Decision record (documentation/process):** identify the decision question,
   owner and scope; link source IDs and revisions; distinguish established
   evidence, framework synthesis, and working hypotheses; record alternatives,
   concise rationale, assumptions, disconfirmers, harms, authority, expected
   consequences, and conditions for revisiting the decision.
2. **Implementation traceability:** where a change is consequential, link its
   decision record to the task/preview/result version, code revision, tests, and
   human review. Keep those links separate from filing metadata and do not let a
   caller-authored rationale confer corroboration, confidence, approval, or
   execution authority.
3. **Comparative evaluation:** define the target decision and baseline before
   evaluation; use held-out cases and independent/blinded review where feasible;
   measure relevant outcomes and harms; preserve disagreement, null results, and
   adverse findings. Do not promote the framework based on coherence, test
   counts, or model-generated confidence.
4. **Human promotion and revision:** treat new methods and records as candidates
   until an authorized human review accepts them. Preserve the exact source and
   preview binding, the prior released version, and an auditable correction or
   supersession history.

## Open questions

- Should the next deliverable be a reusable decision-record schema and UI/API
  linkage, or first a documented manual review template?
- Which human role may approve a decision record, and is its scope task-level,
  project-level, or both?
- Can the owner provide PR #11 review comments and workflow logs if a
  commit-by-commit decision review is wanted? The supplied status summary alone
  does not show the underlying review evidence.
- Should the older MetaMatrix document remain a historical source as-is, with a
  current-status crosswalk, or receive a carefully attributed status annotation?
- What held-out decision tasks, baseline, outcome measures, and harm criteria
  should govern any future empirical promotion?
