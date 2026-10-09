# Prompt steering, observable outputs, and reasoning limits

## Purpose and boundary

This work builds a reproducible audit of **observable prompt/steering summaries,
assistant-visible outputs, and verifiable outcomes**. It cannot reconstruct a
user's private mental process or expose an assistant's private hidden
chain-of-thought. A written explanation or generated rationale is itself
visible output, not privileged proof of the causal computation that produced
the answer.

Accordingly, the framework records:

1. the user's stated goal and explicit constraints;
2. visible requirement changes or corrections;
3. the assistant-visible answer/action claims;
4. source, test, runtime, or user-reported outcome evidence;
5. missing turns, uncertain attribution, and alternative interpretations.

It does **not** infer subconscious motives, latent beliefs, private model
reasoning, or "what the model really thought." Replace such fields with
`NOT_ACCESSIBLE` or `NOT_ASSESSED`. "SI-level" is a research aspiration, not a
capability this audit measures or certifies.

The generated catalog also inventories repository-authored Markdown, RST, and
TXT guidance files (tracked or non-ignored, up to 2 MB each): source path/kind,
SHA-256, byte and line counts, plus counts of directive/topic terms. It stores
no duplicate document text in that inventory. SQL usage scanning is separately
bounded to eligible source/test files and `.sql` files, with SQL-string
heuristics; dynamically assembled queries and excluded/generated/dependency
directories can be missed. Neither inventory establishes actual prompt use or
causal impact.

## Scope of the supplied run

Input: the user-supplied `Prompt_Usage_Audit.zip`, read locally. Its
`Prompt_Usage_Audit.sqlite` contains 12 selected, analyst-summarized cases.
The ZIP's `build_audit.py` was not run. The new importer reads the SQLite
member in memory and never extracts or executes archive code.

The case summaries describe iterative task development: broad requests,
additional requirements or corrections, followed by requests to inspect or
verify results. This is a qualitative pattern in the selected summaries, not
a population-level finding about every prompt or the user's personality.

### Outcome labels in the selected audit

| Visible outcome class | Cases |
|---|---:|
| `output_missing` | 3 |
| `claimed_tests_partial_completion` | 1 |
| `claimed_implementation_unverified` | 1 |
| `claimed_fix_unverified` | 1 |
| `claimed_fix_with_user_failure_reports` | 1 |
| `user_reported_defect_unresolved` | 1 |
| `output_not_verified` | 1 |
| `summary_only` | 1 |
| `retrieval_summary_only` | 1 |
| `bounded_assistant_claim` | 1 |
| **Selected case summaries** | **12** |

These categories are not a success rate, compliance score, or causal estimate.
Most are explicitly missing independent runtime/source verification. No
complete account export or raw, turn-by-turn transcript was supplied. The
archive states that internal interpretation logs and hidden reasoning are
unavailable.

The uploaded audit also compared SQL-reference categories to natural-language
prompting as an **analogy**; it explicitly did not establish that SQL was run
on those prompts or that SQL parameter binding was used in those chats. There
is no evidence in this selected set that the prompts were prompt-injection
attacks. Do not conflate:

- **SQL injection:** untrusted data changes a SQL statement that is parsed and
  executed by a database.
- **Prompt injection:** untrusted text is mistaken for an instruction by an
  LLM or agent.
- **User steering:** the user explicitly revises task requirements or
  acceptance criteria; this is not inherently an attack.

The SQL/SQLite catalog is still useful for the database boundary; it does not
turn conversational text into SQL or a steering prompt into an injection.

## Observable model: user steering versus assistant-visible process

Use paired, versioned records rather than imagined thought traces:

| User-side observable event | Assistant-side observable event | Evidence allowed |
|---|---|---|
| Initial goal and explicitly stated reason | Acknowledgement/interpretation returned to user | Visible prompt and response |
| Added, changed, or withdrawn constraint | Plan, clarification, refusal, or implementation claim | Ordered visible turns/tool calls |
| User acceptance, correction, or reported failure | Artifact or action performed | Diff, command/test output, user report, or external system receipt |
| User's stated uncertainty or boundary | Assistant's stated uncertainty and source limits | Exact visible language and cited source |
| Missing turn or unavailable account data | No substitute is inferred | `NOT_AVAILABLE` with provenance |

A paired comparison may assess *observable alignment*: whether the assistant
preserved the latest explicit goal, followed constraints, cited evidence,
requested clarification when necessary, and verified the requested outcome.
It must not claim to know the user's or model's private reasoning.

For future studies, preregister a task, permitted inputs, prompt version,
model/provider/version (if the operator supplies it), tool permissions,
expected safe action, task-utility test, attack success definition, and
disconfirmation conditions. Compare a baseline with one intervention at a time,
repeat over a documented case set, preserve failures, and report confidence
intervals only when a sampling design justifies them. Deterministic state
assertions are preferable to asking a model to grade its own security success.
Never send private conversation text to an external model or service without
explicit authorization.

## GitHub agent handoff

The owner-provided [session handoff](../data/prompt_session_handoff.json) is a
portable context package for a GitHub coding agent. It includes summarized
historical goals, the currently supplied user statements, assistant-visible
rationale summaries, repository/test results, explicit gaps, and a task for
the next agent. It is intentionally **not** a full transcript or a hidden
reasoning dump. Each historical item is labeled as a summary. Validate and
render it locally with:

```sh
python -m vessell.agent_handoff
```

Then give the GitHub agent the `github_agent_task` in the JSON and have it read
the handoff plus this audit document. The repository's
[Copilot instructions](../.github/copilot-instructions.md) require it to keep
user statements, visible assistant rationale, actions, and verified outcomes
separate. The handoff notes that no GitHub agent was launched, no commit/push
occurred, and the previously considered VS Code recorder was removed before
any events were collected. Review this
owner-provided material before committing or publishing it, especially if the
repository is public.

## SQL and LLM boundary controls

SQL parameter binding protects the database parser boundary. Instruction
hierarchy and trusted-source separation protect the LLM prompt boundary.
Neither control substitutes for the other:

- SQL Server: use typed parameters, for example `sp_executesql` parameters;
  allowlist identifiers because a value parameter cannot stand for a table or
  column name.
- SQLite/Python: use `sqlite3` placeholders and a separate allowlist for
  dynamic identifiers.
- R/DBI: use `dbSendQuery` or `dbSendStatement`, `dbBind`, fetch results, and
  always clear result handles; placeholder syntax depends on the DBI backend.
- LLM agent: retrieved documents, database rows, logs, tool outputs, and
  quoted prompt text remain untrusted data, even if they contain imperative
  language. They cannot grant new tool permissions or override higher-priority
  instructions.
- Validate tool arguments and authorize side effects outside the LLM. A model
  refusal, explanation, detector score, or prompt delimiter is not an
  authorization mechanism.

Test SQL safety with actual database state and bound hostile-looking values.
Test LLM prompt-injection resistance with benign, isolated fixtures and
deterministic assertions about allowed tool calls, data disclosure, task
completion, and side effects. Do not use an LLM's claimed hidden reasoning as
the attack-success oracle.

## Six-pillar integration

| Pillar | Audit contribution | Boundary |
|---|---|---|
| PARADOX | Keep competing readings of ambiguous or revised instructions visible. | A contradiction is not proof of deception or intent. |
| BOTTLENECK | Identify access, context-window, retrieval, tool, permission, and verification constraints. | A missing result is not evidence the work was done or not done. |
| DUAL LAYER | Separate explicit statements/observations from latent-state hypotheses; separate instructions from untrusted data. | Do not promote an interpretation to an observation. |
| XFACTOR | Mark model variance, prompt sensitivity, and untested conditions; compare controlled prompt variants. | A single run does not establish robustness or an emergent capability. |
| KNOWING FIELD | Preserve the owner's self-report, assistant-visible response, analyst synthesis, affected perspectives, and dissent separately. | No model or analyst may claim access to private lived experience or hidden cognition. |
| GAME THEORY | Where an actual attacker/defender interaction is studied, declare actors, action sets, information, utilities, and evidence. | A conditional strategy does not show the user intended an attack or the model held a private motive. |

The Scientific Evidence skill governs source quality, measurement, falsifiers,
and limits. The Search Gate governs what sources and artifacts are actually
available. The Evil Twin challenge tests the strongest alternative reading and
the residual failure path.

## Research and technical sources

1. Turpin et al. (2023), [Language Models Don't Always Say What They Think:
   Unfaithful Explanations in Chain-of-Thought Prompting](https://arxiv.org/abs/2305.04388).
   Demonstrates plausible rationales can omit influential prompt features.
2. Lanham et al. (2023), [Measuring Faithfulness in Chain-of-Thought
   Reasoning](https://arxiv.org/abs/2307.13702). Uses interventions such as
   early-answering and inserted mistakes; faithfulness varies across tasks.
3. Zhan et al. (2024), [InjecAgent: Benchmarking Indirect Prompt Injections in
   Tool-Integrated Large Language Model Agents](https://aclanthology.org/2024.findings-acl.624/).
   Benchmarks instructions embedded in tool-provided content.
4. Debenedetti et al. (2024), [AgentDojo: A Dynamic Environment to Evaluate
   Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352).
   Evaluates security and task utility in stateful tool environments with
   objective environment-state checks.
5. Liu et al. (2024), [An Early Categorization of Prompt Injection Attacks on
   Large Language Models](https://arxiv.org/abs/2402.00898). A taxonomy is not
   a coverage guarantee or a repository exposure assessment.
6. [Python `sqlite3` parameter binding](https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries)
   and [R DBI `dbBind`](https://dbi.r-dbi.org/reference/dbBind.html) document
   binding values separately from SQL syntax.
7. Microsoft, [SQL Injection - SQL Server](https://learn.microsoft.com/en-us/sql/relational-databases/security/sql-injection),
   covers SQL Server injection and dynamic-SQL risks.

These sources support cautious evaluation design, not claims that a particular
model's hidden reasoning was observed. Benchmarks are snapshots; this repo's
small selected audit is not a benchmark replication.

## Reproducible tools and result

Build the SQL Server/SQLite catalog and import the selected audit summaries:

```sh
python scripts/build_sql_reference_db.py \
  --prompt-audit-zip /path/to/Prompt_Usage_Audit.zip
python -m vessell.prompt_audit --database data/sql_reference.sqlite
Rscript r/prompt_audit.R data/sql_reference.sqlite
```

Python and R report aggregate visible outcome classes and scope limits. Neither
tool calls an LLM, infers chain-of-thought, executes code from the ZIP, or
releases private text to a service. Regenerate the catalog without
`--prompt-audit-zip` to remove the selected prompt-case summaries.
