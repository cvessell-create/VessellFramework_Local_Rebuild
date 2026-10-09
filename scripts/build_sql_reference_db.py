"""Build a searchable SQLite SQL reference and repository usage map."""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "sql_reference.sqlite"
DIALECTS = [
    (
        "sqlserver",
        "Microsoft SQL Server (T-SQL)",
        "SQL Server syntax; examples use @named parameters.",
    ),
    (
        "sqlite",
        "SQLite",
        "SQLite syntax; examples use ? placeholders for Python sqlite3 unless noted.",
    ),
]

LLM_PILLAR_CONTROLS = [
    (
        "PARADOX",
        "Keep competing explanations for an instruction or result visible; do not infer private motive from phrasing.",
        "Record explicit contradictions and unresolved alternatives in user-visible evidence.",
    ),
    (
        "BOTTLENECK",
        "Check tool, context, permission, budget, schema, and evidence limits before attributing an outcome to model reasoning.",
        "Record the blocking constraint, available inputs, and whether execution/verification was actually possible.",
    ),
    (
        "DUAL LAYER",
        "Separate instruction text from untrusted quoted, retrieved, tool, database, and code content.",
        "Track source and trust boundary for each instruction-bearing segment; keep data from gaining authority.",
    ),
    (
        "XFACTOR",
        "Keep novelty, ambiguity, model variability, and untested interaction effects as uncertain factors.",
        "Label untested factors NOT_ASSESSED; use controlled paired cases before generalizing.",
    ),
    (
        "KNOWING FIELD",
        "Treat the user's explicit account, assistant-visible response, and analyst interpretation as distinct perspectives.",
        "Preserve attribution, dissent, missing turns, and human review; do not claim access to internal mental states.",
    ),
    (
        "GAME THEORY",
        "Model attacker/defender actions only when actors, actions, information, utility, and evidence are declared.",
        "Mark unavailable strategic inputs NOT_SUPPLIED; conditional attack results do not prove intent or prevalence.",
    ),
]

RESEARCH_SOURCES = [
    (
        "turpin-2023-cot-unfaithfulness",
        "2023",
        "Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting",
        "https://arxiv.org/abs/2305.04388",
        "Primary empirical paper",
        "CoT explanations can omit influential prompt features and rationalize outputs; visible rationale is not privileged access to internal computation.",
    ),
    (
        "lanham-2023-cot-faithfulness",
        "2023",
        "Measuring Faithfulness in Chain-of-Thought Reasoning",
        "https://arxiv.org/abs/2307.13702",
        "Primary empirical paper",
        "Faithfulness varies by task and is evaluated by interventions on visible traces; a verbal trace alone does not verify a causal reasoning process.",
    ),
    (
        "zhan-2024-injecagent",
        "2024",
        "InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents",
        "https://aclanthology.org/2024.findings-acl.624/",
        "Peer-reviewed benchmark",
        "Tests malicious instructions embedded in tool-provided content; relevant to provenance-aware separation of task instructions and retrieved data.",
    ),
    (
        "debenedetti-2024-agentdojo",
        "2024",
        "AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents",
        "https://arxiv.org/abs/2406.13352",
        "Primary benchmark paper",
        "Evaluates utility and security outcomes in stateful tool environments; objective state checks are preferable to an LLM judging its own security success.",
    ),
    (
        "liu-2024-prompt-injection-taxonomy",
        "2024",
        "An Early Categorization of Prompt Injection Attacks on Large Language Models",
        "https://arxiv.org/abs/2402.00898",
        "Research taxonomy",
        "Provides a threat taxonomy; taxonomy coverage is not a defense guarantee or a measure of this repository's exposure.",
    ),
    (
        "python-sqlite3-placeholders",
        "current documentation",
        "Python sqlite3: How to use placeholders to bind values in SQL queries",
        "https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries",
        "Official language documentation",
        "Bind values rather than formatting them into SQL; identifiers require separately controlled construction.",
    ),
    (
        "r-dbi-dbbind",
        "current documentation",
        "DBI: Bind values to a parameterized/prepared statement",
        "https://dbi.r-dbi.org/reference/dbBind.html",
        "Official package documentation",
        "dbBind separates query text from values; placeholder syntax is backend-specific and results must be cleared.",
    ),
    (
        "microsoft-sql-injection",
        "current documentation",
        "SQL Injection - SQL Server",
        "https://learn.microsoft.com/en-us/sql/relational-databases/security/sql-injection",
        "Official database security documentation",
        "Concatenated dynamic SQL can be vulnerable; parameterization alone does not make unsafe dynamic SQL construction safe.",
    ),
]

LLM_IMPLEMENTATION_EXAMPLES = [
    (
        "sqlserver-parameterized-dynamic-query",
        "SQL",
        "sqlserver",
        "Safely bind a dynamic-query value with sp_executesql.",
        "EXEC sys.sp_executesql N'SELECT id FROM dbo.items WHERE id = @id', N'@id int', @id = @item_id;",
        "Values are parameters; allowlist identifiers because parameters cannot bind table or column names.",
        "https://learn.microsoft.com/en-us/sql/relational-databases/security/sql-injection",
    ),
    (
        "python-sqlite-parameterized-query",
        "Python",
        "sqlite",
        "Bind data values using Python sqlite3 qmark placeholders.",
        'rows = connection.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchall()',
        "Use placeholders for values; allowlist identifiers and never format untrusted input into SQL text.",
        "https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries",
    ),
    (
        "r-dbi-sqlite-bound-query",
        "R",
        "sqlite",
        "Prepare a DBI query and bind values with RSQLite-compatible placeholders.",
        'result <- DBI::dbSendQuery(connection, "SELECT id FROM items WHERE id = ?"); DBI::dbBind(result, list(item_id)); rows <- DBI::dbFetch(result); DBI::dbClearResult(result)',
        "Placeholder syntax is backend-specific; clear the result even after errors.",
        "https://dbi.r-dbi.org/reference/dbBind.html",
    ),
]

CONCEPTS = [
    ("retrieval", "SELECT", "Choose columns or expressions for a result.", "All"),
    ("retrieval", "FROM", "Choose the source table, view, or subquery.", "All"),
    ("retrieval", "AS", "Name a result column or table alias.", "All"),
    ("filtering", "WHERE", "Filter rows before grouping.", "All"),
    ("filtering", "TOP", "Limit rows in SQL Server; SQLite uses LIMIT.", "SQL Server only"),
    ("filtering", "LIKE", "Match text patterns using % and _ wildcards.", "All; collation varies"),
    ("filtering", "AND", "Require both Boolean conditions.", "All"),
    ("filtering", "OR", "Require either Boolean condition.", "All"),
    ("filtering", "NOT", "Negate a Boolean condition.", "All"),
    ("filtering", "BETWEEN", "Test an inclusive range.", "All"),
    ("filtering", "IN", "Test membership in a value or query set.", "All"),
    ("filtering", "IS NULL", "Test for a NULL value.", "All"),
    ("sorting", "ORDER BY", "Sort output rows explicitly.", "All"),
    ("sorting", "ASC", "Sort in ascending order.", "All"),
    ("sorting", "DESC", "Sort in descending order.", "All"),
    (
        "functions",
        "LEFT",
        "Return leading characters; SQLite commonly uses substr.",
        "SQL Server; SQLite alternative",
    ),
    (
        "functions",
        "RIGHT",
        "Return trailing characters; SQLite commonly uses substr.",
        "SQL Server; SQLite alternative",
    ),
    (
        "functions",
        "SUBSTRING",
        "Extract part of a string; SQLite commonly uses substr.",
        "SQL Server; SQLite alternative",
    ),
    ("functions", "LTRIM", "Trim leading spaces.", "All"),
    ("functions", "RTRIM", "Trim trailing spaces.", "All"),
    ("functions", "UPPER", "Convert supported letters to upper case.", "All"),
    ("functions", "LOWER", "Convert supported letters to lower case.", "All"),
    ("functions", "GETDATE", "Return current local date/time in SQL Server.", "SQL Server only"),
    (
        "functions",
        "DATEPART",
        "Extract a date component in SQL Server.",
        "SQL Server; SQLite alternative",
    ),
    (
        "functions",
        "DATEDIFF",
        "Count date-part boundaries in SQL Server.",
        "SQL Server; SQLite alternative",
    ),
    ("functions", "ROUND", "Round a numeric expression.", "All; precision varies"),
    (
        "functions",
        "PI",
        "Return pi; SQLite build support varies.",
        "SQL Server; optional SQLite math",
    ),
    ("functions", "POWER", "Raise a number to an exponent.", "SQL Server; optional SQLite math"),
    (
        "functions",
        "ISNULL",
        "SQL Server null fallback; SQLite uses ifnull/coalesce.",
        "SQL Server; SQLite alternative",
    ),
    ("calculated fields", "AS", "Give an expression a readable output alias.", "All"),
    ("grouping", "DISTINCT", "Remove duplicate result values/rows.", "All"),
    ("grouping", "SUM", "Sum non-NULL numeric values.", "All"),
    ("grouping", "AVG", "Average non-NULL numeric values.", "All"),
    ("grouping", "MIN", "Return the minimum non-NULL value.", "All"),
    ("grouping", "MAX", "Return the maximum non-NULL value.", "All"),
    ("grouping", "COUNT", "Count rows or non-NULL values.", "All"),
    ("grouping", "GROUP BY", "Aggregate rows by key combinations.", "All"),
    ("grouping", "HAVING", "Filter grouped results after aggregation.", "All"),
    ("grouping", "ROLLUP", "Produce hierarchical subtotals.", "SQL Server; not SQLite"),
    ("grouping", "CUBE", "Produce subtotal combinations.", "SQL Server; not SQLite"),
    ("grouping", "PIVOT", "Rotate row values into columns.", "SQL Server; not SQLite"),
    (
        "grouping",
        "FOR",
        "Engine-specific clause, e.g. SQL Server FOR JSON/XML.",
        "Context-specific",
    ),
    (
        "windows",
        "ROW_NUMBER",
        "Assign sequential row numbers in a window.",
        "Modern SQL Server/SQLite",
    ),
    ("windows", "RANK", "Rank rows, leaving gaps after ties.", "Modern SQL Server/SQLite"),
    ("windows", "DENSE_RANK", "Rank rows without gaps after ties.", "Modern SQL Server/SQLite"),
    ("windows", "NTILE", "Divide ordered rows into buckets.", "Modern SQL Server/SQLite"),
    ("windows", "OVER", "Define the window for a window function.", "Modern SQL Server/SQLite"),
    (
        "windows",
        "PARTITION BY",
        "Restart window calculations by partition.",
        "Modern SQL Server/SQLite",
    ),
    ("conditional", "CASE", "Begin a conditional expression.", "All"),
    ("conditional", "WHEN", "Specify a condition in CASE.", "All"),
    ("conditional", "THEN", "Specify a CASE result for a matched condition.", "All"),
    ("conditional", "ELSE", "Specify a CASE fallback.", "All"),
    (
        "conditional",
        "END",
        "Close CASE (or other block in dialects that use it).",
        "All/context-specific",
    ),
    ("joins", "INNER JOIN", "Keep matching rows from both inputs.", "All"),
    ("joins", "JOIN", "Combine rows using a match condition.", "All"),
    ("joins", "ON", "Specify the join match condition.", "All"),
    ("joins", "LEFT JOIN", "Preserve all rows from the left input.", "All"),
    ("joins", "RIGHT JOIN", "Preserve all rows from the right input.", "Modern SQL Server/SQLite"),
    ("joins", "FULL JOIN", "Preserve unmatched rows from both inputs.", "Modern SQL Server/SQLite"),
    ("joins", "CROSS JOIN", "Return the Cartesian product.", "All"),
    ("set logic", "UNION", "Combine result sets and remove duplicates.", "All"),
    ("set logic", "UNION ALL", "Combine result sets retaining duplicates.", "All"),
    ("set logic", "INTERSECT", "Return rows present in both sets.", "Modern SQL Server/SQLite"),
    (
        "set logic",
        "EXCEPT",
        "Return rows from the first set absent in the second.",
        "Modern SQL Server/SQLite",
    ),
    ("subqueries", "EXISTS", "Test whether a subquery returns any row.", "All"),
    (
        "subqueries",
        "WITH",
        "Define a statement-scoped common table expression.",
        "All; recursive syntax varies",
    ),
    ("subqueries", "SUBQUERY", "Nest a query within another statement.", "All"),
    ("data changes", "INSERT INTO", "Insert rows into a table.", "All"),
    ("data changes", "VALUES", "Supply literal or parameterized inserted values.", "All"),
    ("data changes", "DELETE", "Remove rows selected by a predicate.", "All"),
    (
        "data changes",
        "TRUNCATE TABLE",
        "Remove all rows while retaining a table.",
        "SQL Server; not SQLite",
    ),
    ("data changes", "UPDATE", "Change values in rows selected by a predicate.", "All"),
    (
        "data changes",
        "SET",
        "Assign columns in UPDATE; other dialect-specific uses exist.",
        "All/context-specific",
    ),
    (
        "procedures",
        "STORED PROCEDURE",
        "Reusable server-side routine with parameters.",
        "Not SQLite",
    ),
    (
        "procedures",
        "CREATE PROCEDURE",
        "Define a stored procedure.",
        "SQL Server/other server engines",
    ),
    ("procedures", "BEGIN", "Begin a transaction or procedure block.", "Engine/context-specific"),
    ("procedures", "EXEC", "Invoke a SQL Server stored procedure.", "SQL Server"),
    ("procedures", "CALL", "Invoke procedures in engines such as PostgreSQL/MySQL.", "Not SQLite"),
    (
        "procedures",
        "ALTER PROCEDURE",
        "Change a stored procedure definition.",
        "SQL Server/other server engines",
    ),
    (
        "procedures",
        "DROP PROCEDURE",
        "Remove a stored procedure definition.",
        "Server engines; not SQLite",
    ),
    ("tables and indexes", "CREATE TABLE", "Define a table and its constraints.", "All"),
    ("tables and indexes", "DROP TABLE", "Remove a table and its data.", "All"),
    ("tables and indexes", "CREATE INDEX", "Create an index to support selected queries.", "All"),
    ("tables and indexes", "DROP INDEX", "Remove an index.", "Syntax varies by engine"),
    ("views", "CREATE VIEW", "Define a named query.", "All"),
    ("views", "ALTER VIEW", "Change a view definition.", "SQL Server; not SQLite"),
    ("views", "DROP VIEW", "Remove a view definition.", "All"),
    ("transactions", "BEGIN", "Begin a transaction; block syntax varies.", "All/context-specific"),
    ("transactions", "COMMIT", "Commit the current transaction.", "All"),
    ("transactions", "ROLLBACK", "Undo the current transaction.", "All"),
]

PROMPT_GUIDANCE_TEMPLATES = [
    (
        "read-query",
        "Ask for a retrieval/report query",
        (
            "Write T-SQL for SQL Server {version} to {goal}. List required columns, "
            "joins, filters, NULL behavior and deterministic ordering. Use @named "
            "parameters and SQL Server row limiting (TOP or OFFSET/FETCH as appropriate)."
        ),
        (
            "Write SQLite SQL for {goal}. List required columns, joins, filters, "
            "NULL behavior and deterministic ordering. Use ? or named SQLite "
            "parameters and LIMIT/OFFSET; avoid SQL Server-only syntax."
        ),
        "Use explicit columns; test empty, duplicate, and NULL cases; state engine version.",
        "SQL_QUICK_REFERENCE.md; data/sql_reference.sqlite dialect_features",
    ),
    (
        "modify-rows",
        "Ask to insert, update, or delete data",
        (
            "For SQL Server {version}, implement {operation} on {table} with "
            "@named parameters. Show a SELECT preview, require a specific WHERE "
            "predicate, use TRY/CATCH and an explicit transaction where appropriate, "
            "and state the rollback plan."
        ),
        (
            "For SQLite {version}, implement {operation} on {table} with bound "
            "parameters (? or :name). Show a SELECT preview, require a specific "
            "WHERE predicate, use an explicit transaction where appropriate, "
            "and state the rollback plan."
        ),
        "Never run broad writes without an explicit all-rows requirement; verify row counts.",
        "SQL_QUICK_REFERENCE.md; data/sql_reference.sqlite dialect_features",
    ),
    (
        "schema-migration",
        "Ask to change tables, indexes, or views",
        (
            "Create a versioned SQL Server {version} migration for {change}. "
            "Use T-SQL-compatible DDL, preserve data/constraints, handle dependent "
            "objects and transaction behavior, and provide an ordered rollback plan."
        ),
        (
            "Create a versioned SQLite {version} migration for {change}. Use only "
            "supported SQLite DDL and PRAGMA behavior; preserve data/constraints, "
            "handle dependent objects and table-rebuild needs, and provide a rollback plan."
        ),
        "Check engine-specific DDL, foreign keys, indexes, dependent views, and backup needs.",
        "SQL_QUICK_REFERENCE.md; data/sql_reference.sqlite dialect_features",
    ),
    (
        "stored-procedure",
        "Ask for reusable database logic",
        (
            "Implement {operation} as a SQL Server {version} stored procedure. "
            "Declare typed parameters, validate inputs, define transaction/error "
            "behavior with TRY/CATCH where needed, and show EXEC plus caller parameter binding."
        ),
        (
            "Implement {operation} for SQLite {version} without a stored procedure "
            "(SQLite has none). Put reusable logic in parameterized application code "
            "or a transaction script; show bound parameters, transaction/error behavior, "
            "and the caller."
        ),
        "Do not claim SQLite supports CREATE/ALTER/DROP PROCEDURE, EXEC, or CALL.",
        "SQL_QUICK_REFERENCE.md; data/sql_reference.sqlite dialect_features",
    ),
    (
        "repository-search",
        "Ask how a SQL feature is currently used here",
        (
            "Search for SQL Server/T-SQL use of {feature}. Report source paths/lines, "
            "parameter style and code context; distinguish executable code from "
            "tests/docs. If none, say NOT OBSERVED IN SCANNED SCOPE."
        ),
        (
            "Search for SQLite SQL use of {feature}. Report source paths/lines, "
            "parameter style and code context; distinguish application from "
            "tests/tooling/docs. If none, say NOT OBSERVED IN SCANNED SCOPE."
        ),
        "Use repository_usage as a search index, then open cited source before conclusions.",
        "data/sql_reference.sqlite: repository_usage and dialect_features",
    ),
    (
        "review-sql",
        "Ask for a SQL safety/correctness review",
        (
            "Review this T-SQL and caller for SQL Server {version}: injection, "
            "predicate scope, NULL/duplicate behavior, transaction and error handling, "
            "locking/index implications, and compatibility. Cite lines and minimal fixes."
        ),
        (
            "Review this SQL and caller for SQLite {version}: injection, predicate "
            "scope, NULL/duplicate behavior, transaction/locking semantics, indexes, "
            "and compatibility. Cite lines and minimal fixes."
        ),
        "Parameterize values; identifiers need allowlists; avoid claiming tests prove production safety.",
        "SQL_QUICK_REFERENCE.md; data/sql_reference.sqlite dialect_features",
    ),
]

PROMPT_GUIDANCE = [
    (f"{prompt_id}-{dialect}", dialect, intent, template, checks, source)
    for prompt_id, intent, sqlserver_template, sqlite_template, checks, source in PROMPT_GUIDANCE_TEMPLATES
    for dialect, template in (
        ("sqlserver", sqlserver_template),
        ("sqlite", sqlite_template),
    )
]

DIALECT_FEATURE_NOTES = {
    "TOP": {
        "sqlite": ("alternative", "Use LIMIT at the end of the query."),
    },
    "LEFT": {
        "sqlite": ("alternative", "Use substr(text, 1, length)."),
    },
    "RIGHT": {
        "sqlite": ("alternative", "Use substr(text, -length) for trailing characters."),
    },
    "SUBSTRING": {
        "sqlite": ("alternative", "Use substr(text, start, length)."),
    },
    "GETDATE": {
        "sqlite": (
            "alternative",
            "Use CURRENT_TIMESTAMP or datetime('now'); SQLite values are UTC by default.",
        ),
    },
    "DATEPART": {
        "sqlite": ("alternative", "Use strftime/date/time functions; format tokens vary."),
    },
    "DATEDIFF": {
        "sqlite": (
            "alternative",
            "Use julianday(), unixepoch(), or date/time functions; boundary semantics differ.",
        ),
    },
    "PI": {
        "sqlite": (
            "conditional",
            "Requires a SQLite build with math functions enabled or an application-supplied value.",
        ),
    },
    "POWER": {
        "sqlite": ("conditional", "Requires a SQLite build with math functions enabled."),
    },
    "ISNULL": {
        "sqlite": ("alternative", "Use ifnull(value, fallback) or COALESCE(value, fallback)."),
    },
    "ROLLUP": {
        "sqlite": ("unsupported", "No built-in ROLLUP; use explicit UNION ALL subtotal queries."),
    },
    "CUBE": {
        "sqlite": ("unsupported", "No built-in CUBE; construct subtotal combinations explicitly."),
    },
    "PIVOT": {
        "sqlite": (
            "unsupported",
            "No PIVOT operator; conditional aggregation with CASE is a common alternative.",
        ),
    },
    "FOR": {
        "sqlserver": (
            "context-specific",
            "FOR XML/JSON is SQL Server-specific; syntax depends on the SELECT output mode.",
        ),
        "sqlite": (
            "unsupported",
            "No general FOR clause; use SQLite-specific functions or application code.",
        ),
    },
    "RIGHT JOIN": {
        "sqlite": (
            "versioned",
            "Available from SQLite 3.39.0; older versions can usually swap tables and use LEFT JOIN.",
        ),
    },
    "FULL JOIN": {
        "sqlite": (
            "versioned",
            "Available from SQLite 3.39.0; older versions need a LEFT JOIN/anti-match emulation.",
        ),
    },
    "TRUNCATE TABLE": {
        "sqlite": (
            "unsupported",
            "Not supported; DELETE FROM removes rows but has different identity/trigger behavior.",
        ),
    },
    "STORED PROCEDURE": {
        "sqlite": ("unsupported", "SQLite has no stored-procedure feature."),
    },
    "CREATE PROCEDURE": {
        "sqlite": ("unsupported", "SQLite has no CREATE PROCEDURE statement."),
    },
    "EXEC": {
        "sqlite": ("unsupported", "SQLite does not invoke stored procedures with EXEC."),
    },
    "CALL": {
        "sqlserver": ("alternative", "Use EXEC/EXECUTE to invoke a SQL Server stored procedure."),
        "sqlite": ("unsupported", "SQLite has no CALL or stored-procedure feature."),
    },
    "ALTER PROCEDURE": {
        "sqlite": ("unsupported", "SQLite has no ALTER PROCEDURE statement."),
    },
    "DROP PROCEDURE": {
        "sqlite": ("unsupported", "SQLite has no stored procedures to drop."),
    },
    "DROP INDEX": {
        "sqlserver": (
            "context-specific",
            "SQL Server syntax is DROP INDEX index_name ON table_name.",
        ),
        "sqlite": ("native", "SQLite syntax is DROP INDEX [IF EXISTS] index_name."),
    },
    "ALTER VIEW": {
        "sqlite": ("unsupported", "Drop and recreate the view, handling dependent objects."),
    },
    "SUBQUERY": {
        "sqlserver": (
            "native",
            "Nested SELECT expression; syntax depends on scalar/set/correlated use.",
        ),
        "sqlite": (
            "native",
            "Nested SELECT expression; syntax depends on scalar/set/correlated use.",
        ),
    },
    "BEGIN": {
        "sqlserver": (
            "context-specific",
            "BEGIN TRANSACTION starts a transaction; BEGIN...END delimits statement blocks.",
        ),
        "sqlite": (
            "context-specific",
            "BEGIN [DEFERRED|IMMEDIATE|EXCLUSIVE] starts a transaction.",
        ),
    },
}

DIALECT_EXAMPLES = {
    "TOP": {
        "sqlserver": "SELECT TOP (10) id FROM dbo.items ORDER BY id;",
        "sqlite": "SELECT id FROM items ORDER BY id LIMIT 10;",
    },
    "SELECT": {
        "sqlserver": "SELECT id, name FROM dbo.items;",
        "sqlite": "SELECT id, name FROM items;",
    },
    "FROM": {
        "sqlserver": "SELECT id FROM dbo.items;",
        "sqlite": "SELECT id FROM items;",
    },
    "AS": {
        "sqlserver": "SELECT amount * quantity AS total FROM dbo.lines;",
        "sqlite": "SELECT amount * quantity AS total FROM lines;",
    },
    "WHERE": {
        "sqlserver": "SELECT id FROM dbo.items WHERE active = @active;",
        "sqlite": "SELECT id FROM items WHERE active = ?;",
    },
    "LIKE": {
        "sqlserver": "SELECT id FROM dbo.items WHERE name LIKE @pattern;",
        "sqlite": "SELECT id FROM items WHERE name LIKE ?;",
    },
    "AND": {
        "sqlserver": "WHERE active = 1 AND region = @region",
        "sqlite": "WHERE active = 1 AND region = ?",
    },
    "OR": {
        "sqlserver": "WHERE status = @open OR status = @pending",
        "sqlite": "WHERE status = ? OR status = ?",
    },
    "NOT": {
        "sqlserver": "WHERE NOT (status = @closed)",
        "sqlite": "WHERE NOT (status = ?)",
    },
    "BETWEEN": {
        "sqlserver": "WHERE score BETWEEN @low AND @high",
        "sqlite": "WHERE score BETWEEN ? AND ?",
    },
    "IN": {
        "sqlserver": "WHERE status IN ('open', 'pending')",
        "sqlite": "WHERE status IN ('open', 'pending')",
    },
    "IS NULL": {
        "sqlserver": "WHERE deleted_at IS NULL",
        "sqlite": "WHERE deleted_at IS NULL",
    },
    "ORDER BY": {
        "sqlserver": "ORDER BY created_at DESC, id ASC",
        "sqlite": "ORDER BY created_at DESC, id ASC",
    },
    "DISTINCT": {
        "sqlserver": "SELECT DISTINCT region FROM dbo.items;",
        "sqlite": "SELECT DISTINCT region FROM items;",
    },
    "SUM": {
        "sqlserver": "SELECT SUM(amount) FROM dbo.lines;",
        "sqlite": "SELECT SUM(amount) FROM lines;",
    },
    "AVG": {
        "sqlserver": "SELECT AVG(score) FROM dbo.results;",
        "sqlite": "SELECT AVG(score) FROM results;",
    },
    "MIN": {
        "sqlserver": "SELECT MIN(created_at) FROM dbo.events;",
        "sqlite": "SELECT MIN(created_at) FROM events;",
    },
    "MAX": {
        "sqlserver": "SELECT MAX(created_at) FROM dbo.events;",
        "sqlite": "SELECT MAX(created_at) FROM events;",
    },
    "COUNT": {
        "sqlserver": "SELECT COUNT(*) FROM dbo.items;",
        "sqlite": "SELECT COUNT(*) FROM items;",
    },
    "ROUND": {
        "sqlserver": "SELECT ROUND(amount, 2) FROM dbo.items;",
        "sqlite": "SELECT round(amount, 2) FROM items;",
    },
    "LTRIM": {
        "sqlserver": "SELECT LTRIM(name) FROM dbo.items;",
        "sqlite": "SELECT ltrim(name) FROM items;",
    },
    "RTRIM": {
        "sqlserver": "SELECT RTRIM(name) FROM dbo.items;",
        "sqlite": "SELECT rtrim(name) FROM items;",
    },
    "UPPER": {
        "sqlserver": "SELECT UPPER(name) FROM dbo.items;",
        "sqlite": "SELECT upper(name) FROM items;",
    },
    "LOWER": {
        "sqlserver": "SELECT LOWER(name) FROM dbo.items;",
        "sqlite": "SELECT lower(name) FROM items;",
    },
    "PI": {
        "sqlserver": "SELECT PI();",
        "sqlite": "SELECT pi(); -- available when SQLite math functions are enabled",
    },
    "POWER": {
        "sqlserver": "SELECT POWER(2, 3);",
        "sqlite": "SELECT power(2, 3); -- available when SQLite math functions are enabled",
    },
    "ISNULL": {
        "sqlserver": "SELECT ISNULL(nickname, 'unknown') FROM dbo.users;",
        "sqlite": "SELECT ifnull(nickname, 'unknown') FROM users;",
    },
    "ROW_NUMBER": {
        "sqlserver": "ROW_NUMBER() OVER (PARTITION BY region ORDER BY id)",
        "sqlite": "ROW_NUMBER() OVER (PARTITION BY region ORDER BY id)",
    },
    "GROUP BY": {
        "sqlserver": "SELECT region, COUNT(*) FROM dbo.items GROUP BY region;",
        "sqlite": "SELECT region, COUNT(*) FROM items GROUP BY region;",
    },
    "HAVING": {
        "sqlserver": "GROUP BY region HAVING COUNT(*) > 1",
        "sqlite": "GROUP BY region HAVING COUNT(*) > 1",
    },
    "RANK": {
        "sqlserver": "RANK() OVER (ORDER BY score DESC)",
        "sqlite": "RANK() OVER (ORDER BY score DESC)",
    },
    "DENSE_RANK": {
        "sqlserver": "DENSE_RANK() OVER (ORDER BY score DESC)",
        "sqlite": "DENSE_RANK() OVER (ORDER BY score DESC)",
    },
    "NTILE": {
        "sqlserver": "NTILE(4) OVER (ORDER BY score)",
        "sqlite": "NTILE(4) OVER (ORDER BY score)",
    },
    "OVER": {
        "sqlserver": "COUNT(*) OVER (PARTITION BY region)",
        "sqlite": "COUNT(*) OVER (PARTITION BY region)",
    },
    "PARTITION BY": {
        "sqlserver": "ROW_NUMBER() OVER (PARTITION BY region ORDER BY id)",
        "sqlite": "ROW_NUMBER() OVER (PARTITION BY region ORDER BY id)",
    },
    "CASE": {
        "sqlserver": "CASE WHEN score >= 80 THEN 'pass' ELSE 'review' END",
        "sqlite": "CASE WHEN score >= 80 THEN 'pass' ELSE 'review' END",
    },
    "INNER JOIN": {
        "sqlserver": "SELECT i.id FROM dbo.items AS i INNER JOIN dbo.tags AS t ON t.item_id = i.id;",
        "sqlite": "SELECT i.id FROM items AS i INNER JOIN tags AS t ON t.item_id = i.id;",
    },
    "JOIN": {
        "sqlserver": "SELECT i.id FROM dbo.items AS i JOIN dbo.tags AS t ON t.item_id = i.id;",
        "sqlite": "SELECT i.id FROM items AS i JOIN tags AS t ON t.item_id = i.id;",
    },
    "ON": {
        "sqlserver": "JOIN dbo.tags AS t ON t.item_id = i.id",
        "sqlite": "JOIN tags AS t ON t.item_id = i.id",
    },
    "LEFT JOIN": {
        "sqlserver": "SELECT i.id FROM dbo.items AS i LEFT JOIN dbo.tags AS t ON t.item_id = i.id;",
        "sqlite": "SELECT i.id FROM items AS i LEFT JOIN tags AS t ON t.item_id = i.id;",
    },
    "RIGHT JOIN": {
        "sqlserver": "SELECT i.id FROM dbo.items AS i RIGHT JOIN dbo.tags AS t ON t.item_id = i.id;",
        "sqlite": "SELECT i.id FROM items AS i RIGHT JOIN tags AS t ON t.item_id = i.id;",
    },
    "FULL JOIN": {
        "sqlserver": "SELECT i.id FROM dbo.items AS i FULL OUTER JOIN dbo.tags AS t ON t.item_id = i.id;",
        "sqlite": "SELECT i.id FROM items AS i FULL OUTER JOIN tags AS t ON t.item_id = i.id;",
    },
    "CROSS JOIN": {
        "sqlserver": "SELECT i.id, t.id FROM dbo.items AS i CROSS JOIN dbo.tags AS t;",
        "sqlite": "SELECT i.id, t.id FROM items AS i CROSS JOIN tags AS t;",
    },
    "UNION": {
        "sqlserver": "SELECT id FROM dbo.active_items UNION SELECT id FROM dbo.archived_items;",
        "sqlite": "SELECT id FROM active_items UNION SELECT id FROM archived_items;",
    },
    "UNION ALL": {
        "sqlserver": "SELECT id FROM dbo.active_items UNION ALL SELECT id FROM dbo.archived_items;",
        "sqlite": "SELECT id FROM active_items UNION ALL SELECT id FROM archived_items;",
    },
    "INTERSECT": {
        "sqlserver": "SELECT id FROM dbo.a INTERSECT SELECT id FROM dbo.b;",
        "sqlite": "SELECT id FROM a INTERSECT SELECT id FROM b;",
    },
    "EXCEPT": {
        "sqlserver": "SELECT id FROM dbo.a EXCEPT SELECT id FROM dbo.b;",
        "sqlite": "SELECT id FROM a EXCEPT SELECT id FROM b;",
    },
    "EXISTS": {
        "sqlserver": "WHERE EXISTS (SELECT 1 FROM dbo.orders AS o WHERE o.customer_id = c.id)",
        "sqlite": "WHERE EXISTS (SELECT 1 FROM orders AS o WHERE o.customer_id = c.id)",
    },
    "WITH": {
        "sqlserver": "WITH totals AS (SELECT customer_id, SUM(amount) AS total FROM dbo.orders GROUP BY customer_id) SELECT * FROM totals;",
        "sqlite": "WITH totals AS (SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id) SELECT * FROM totals;",
    },
    "INSERT INTO": {
        "sqlserver": "INSERT INTO dbo.items (name) VALUES (@name);",
        "sqlite": "INSERT INTO items (name) VALUES (?);",
    },
    "VALUES": {
        "sqlserver": "INSERT INTO dbo.items (name) VALUES (@name);",
        "sqlite": "INSERT INTO items (name) VALUES (?);",
    },
    "UPDATE": {
        "sqlserver": "UPDATE dbo.items SET active = @active WHERE id = @id;",
        "sqlite": "UPDATE items SET active = ? WHERE id = ?;",
    },
    "SET": {
        "sqlserver": "UPDATE dbo.items SET active = @active WHERE id = @id;",
        "sqlite": "UPDATE items SET active = ? WHERE id = ?;",
    },
    "DELETE": {
        "sqlserver": "DELETE FROM dbo.items WHERE id = @id;",
        "sqlite": "DELETE FROM items WHERE id = ?;",
    },
    "CREATE TABLE": {
        "sqlserver": "CREATE TABLE dbo.items (id int PRIMARY KEY, name nvarchar(200) NOT NULL);",
        "sqlite": "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL);",
    },
    "DROP TABLE": {
        "sqlserver": "DROP TABLE IF EXISTS dbo.items;",
        "sqlite": "DROP TABLE IF EXISTS items;",
    },
    "CREATE INDEX": {
        "sqlserver": "CREATE INDEX ix_items_name ON dbo.items(name);",
        "sqlite": "CREATE INDEX ix_items_name ON items(name);",
    },
    "DROP INDEX": {
        "sqlserver": "DROP INDEX ix_items_name ON dbo.items;",
        "sqlite": "DROP INDEX IF EXISTS ix_items_name;",
    },
    "CREATE VIEW": {
        "sqlserver": "CREATE VIEW dbo.active_items AS SELECT id FROM dbo.items WHERE active = 1;",
        "sqlite": "CREATE VIEW active_items AS SELECT id FROM items WHERE active = 1;",
    },
    "DROP VIEW": {
        "sqlserver": "DROP VIEW IF EXISTS dbo.active_items;",
        "sqlite": "DROP VIEW IF EXISTS active_items;",
    },
    "COMMIT": {
        "sqlserver": "COMMIT TRANSACTION;",
        "sqlite": "COMMIT;",
    },
    "ROLLBACK": {
        "sqlserver": "ROLLBACK TRANSACTION;",
        "sqlite": "ROLLBACK;",
    },
    "ROLLUP": {
        "sqlserver": "SELECT region, SUM(amount) FROM dbo.sales GROUP BY ROLLUP(region);",
        "sqlite": None,
    },
    "CUBE": {
        "sqlserver": "SELECT region, channel, SUM(amount) FROM dbo.sales GROUP BY CUBE(region, channel);",
        "sqlite": None,
    },
    "PIVOT": {
        "sqlserver": "SELECT * FROM src PIVOT (SUM(amount) FOR quarter IN ([Q1], [Q2])) AS p;",
        "sqlite": None,
    },
    "TRUNCATE TABLE": {
        "sqlserver": "TRUNCATE TABLE dbo.stage_rows;",
        "sqlite": None,
    },
    "STORED PROCEDURE": {
        "sqlserver": "CREATE PROCEDURE dbo.FindItem @id int AS SELECT id FROM dbo.items WHERE id=@id;",
        "sqlite": None,
    },
    "CREATE PROCEDURE": {
        "sqlserver": "CREATE PROCEDURE dbo.FindItem @id int AS SELECT id FROM dbo.items WHERE id=@id;",
        "sqlite": None,
    },
    "EXEC": {
        "sqlserver": "EXEC dbo.FindItem @id = @item_id;",
        "sqlite": None,
    },
    "CALL": {
        "sqlserver": "EXEC dbo.FindItem @id = @item_id;",
        "sqlite": None,
    },
    "ALTER PROCEDURE": {
        "sqlserver": "ALTER PROCEDURE dbo.FindItem @id int AS SELECT id FROM dbo.items WHERE id=@id;",
        "sqlite": None,
    },
    "DROP PROCEDURE": {
        "sqlserver": "DROP PROCEDURE IF EXISTS dbo.FindItem;",
        "sqlite": None,
    },
    "ALTER VIEW": {
        "sqlserver": "ALTER VIEW dbo.active_items AS SELECT id FROM dbo.items WHERE active = 1;",
        "sqlite": None,
    },
    "FOR": {
        "sqlserver": "SELECT id, name FROM dbo.items FOR JSON PATH;",
        "sqlite": None,
    },
    "BEGIN": {
        "sqlserver": "BEGIN TRANSACTION; -- transaction; BEGIN...END also delimits a block",
        "sqlite": "BEGIN IMMEDIATE; -- transaction; use BEGIN...COMMIT",
    },
}


def dialect_features() -> list[tuple[str, str, str, str, str | None, str]]:
    rows = []
    for category, term, _, _ in CONCEPTS:
        for dialect_id, _, _ in DIALECTS:
            override = DIALECT_FEATURE_NOTES.get(term, {}).get(dialect_id)
            if override:
                status, notes = override
            else:
                status = "native"
                notes = "Shared SQL syntax." if dialect_id == "sqlite" else "Native T-SQL syntax."
            example = DIALECT_EXAMPLES.get(term, {}).get(dialect_id)
            rows.append((category, term, dialect_id, status, example, notes))
    return rows


TEXT_SUFFIXES = {".py", ".sql", ".js", ".ts", ".tsx", ".jsx", ".html"}
GUIDANCE_SUFFIXES = {".md", ".rst", ".txt"}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "build",
    "dist",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".sites-runtime",
}
SQL_ANCHOR = re.compile(
    r"\b(?:SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|"
    r"CREATE\s+(?:TEMP(?:ORARY)?\s+)?TABLE|ALTER\s+TABLE|DROP\s+TABLE|"
    r"CREATE\s+(?:UNIQUE\s+)?INDEX|CREATE\s+VIEW)\b",
    re.IGNORECASE,
)
SQL_CALL = re.compile(
    r"\b(?:execute|executescript|executemany)\s*\(\s*(?:[rubf]{0,2})?"
    r"(?P<quote>\"\"\"|'''|\"|')",
    re.IGNORECASE,
)
TERM_PATTERNS = {
    term: re.compile(r"\b" + r"\s+".join(map(re.escape, term.split())) + r"\b", re.IGNORECASE)
    for _, term, _, _ in CONCEPTS
    if term != "SUBQUERY"
}
SQL_STRING_LITERAL = re.compile(r"'(?:''|[^'])*'")
GUIDANCE_DIRECTIVE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:must|never|do not|always|required|prohibited|avoid|ensure)\b"
)
GUIDANCE_TOPIC = re.compile(r"\b(?:prompt|instruction|agent|LLM|skill)\b", re.IGNORECASE)


def tracked_source_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for entry in result.stdout.splitlines():
        path = Path(entry)
        if path.suffix.lower() not in TEXT_SUFFIXES or any(
            part in EXCLUDED_PARTS for part in path.parts
        ):
            continue
        absolute = root / path
        if absolute.is_file() and absolute.stat().st_size <= 2_000_000:
            paths.append(path)
    return sorted(paths)


def tracked_guidance_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for entry in result.stdout.splitlines():
        path = Path(entry)
        if path.suffix.lower() not in GUIDANCE_SUFFIXES or any(
            part in EXCLUDED_PARTS for part in path.parts
        ):
            continue
        absolute = root / path
        if absolute.is_file() and absolute.stat().st_size <= 2_000_000:
            paths.append(path)
    return sorted(paths)


def collect_guidance_inventory(root: Path, files: list[Path]) -> list[tuple[object, ...]]:
    inventory = []
    for path in files:
        try:
            content = (root / path).read_bytes()
            text = content.decode("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        name = path.name.lower()
        if "skill" in name or "skill" in path.parts:
            source_kind = "skill"
        elif "instruction" in name or "prompt" in name:
            source_kind = "prompt_or_instruction"
        else:
            source_kind = "documentation"
        inventory.append(
            (
                path.as_posix(),
                source_kind,
                hashlib.sha256(content).hexdigest(),
                len(content),
                text.count("\n") + (1 if text else 0),
                len(GUIDANCE_DIRECTIVE.findall(text)),
                len(GUIDANCE_TOPIC.findall(text)),
            )
        )
    return inventory


def read_prompt_audit(archive: Path) -> tuple[str, list[tuple[str, ...]]]:
    required = {
        "case_id",
        "topic",
        "period",
        "prompt_evidence",
        "output_evidence",
        "steering",
        "interpretation",
        "outcome_status",
        "provenance",
        "guidance_id",
    }
    with ZipFile(archive) as zipped:
        try:
            info = zipped.getinfo("Prompt_Usage_Audit.sqlite")
        except KeyError as exc:
            raise ValueError("Archive must contain Prompt_Usage_Audit.sqlite.") from exc
        if info.file_size > 20_000_000:
            raise ValueError("Prompt audit database exceeds the 20 MB import limit.")
        content = zipped.read(info)

    digest = hashlib.sha256(content).hexdigest()
    source_db = sqlite3.connect(":memory:")
    try:
        source_db.deserialize(content)
        columns = {row[1] for row in source_db.execute("PRAGMA table_info(audit_cases)")}
        if not required.issubset(columns):
            raise ValueError(
                "Prompt audit database does not match the expected audit_cases schema."
            )
        rows = source_db.execute(
            """
            SELECT case_id, topic, period, prompt_evidence, output_evidence,
                   steering, interpretation, outcome_status, provenance, guidance_id
            FROM audit_cases ORDER BY case_id
            """
        ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise ValueError("Prompt_Usage_Audit.sqlite is not a readable SQLite database.") from exc
    finally:
        source_db.close()
    return digest, rows


def sql_segments(path: Path, text: str) -> list[tuple[int, list[str]]]:
    if path.suffix.lower() == ".sql":
        return [(1, text.splitlines())]

    segments = []
    for match in SQL_CALL.finditer(text):
        quote = match.group("quote")
        start = match.end()
        end = text.find(quote, start)
        if end < 0:
            continue
        segment = text[start:end]
        if SQL_ANCHOR.search(segment):
            start_line = text.count("\n", 0, start) + 1
            segments.append((start_line, segment.splitlines()))
    return segments


def collect_usage(root: Path, files: list[Path]) -> list[tuple[str, int, str, str]]:
    usages: dict[tuple[str, int, str], str] = {}
    for path in files:
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for start_line, lines in sql_segments(path, text):
            for offset, line in enumerate(lines):
                for _, term, _, _ in CONCEPTS:
                    pattern = TERM_PATTERNS.get(term)
                    sql_code = SQL_STRING_LITERAL.sub(" ", line)
                    if pattern and pattern.search(sql_code):
                        snippet = " ".join(line.strip().split())[:300]
                        usages[(path.as_posix(), start_line + offset, term)] = snippet
    return [(path, line, term, snippet) for (path, line, term), snippet in sorted(usages.items())]


def build_database(
    root: Path,
    output: Path,
    prompt_audit_zip: Path | None = None,
) -> None:
    files = tracked_source_files(root)
    usages = collect_usage(root, files)
    guidance_inventory = collect_guidance_inventory(root, tracked_guidance_files(root))
    audit_digest, audit_cases = (
        read_prompt_audit(prompt_audit_zip) if prompt_audit_zip else (None, [])
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    with sqlite3.connect(output) as db:
        db.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE concepts (
                concept_id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                term TEXT NOT NULL,
                description TEXT NOT NULL,
                dialect_support TEXT NOT NULL,
                UNIQUE (category, term)
            );
            CREATE TABLE dialects (
                dialect_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                conventions TEXT NOT NULL
            );
            CREATE TABLE dialect_features (
                concept_id INTEGER NOT NULL REFERENCES concepts(concept_id),
                dialect_id TEXT NOT NULL REFERENCES dialects(dialect_id),
                support_status TEXT NOT NULL CHECK (
                    support_status IN ('native', 'versioned', 'alternative', 'conditional', 'unsupported', 'context-specific')
                ),
                example_sql TEXT,
                notes TEXT NOT NULL,
                PRIMARY KEY (concept_id, dialect_id)
            );
            CREATE TABLE repository_usage (
                usage_id INTEGER PRIMARY KEY,
                concept_id INTEGER NOT NULL REFERENCES concepts(concept_id),
                source_path TEXT NOT NULL,
                source_kind TEXT NOT NULL CHECK (source_kind IN ('application', 'test', 'tooling')),
                line_number INTEGER NOT NULL CHECK (line_number > 0),
                excerpt TEXT NOT NULL,
                UNIQUE (concept_id, source_path, line_number)
            );
            CREATE TABLE repository_guidance_sources (
                source_path TEXT PRIMARY KEY,
                source_kind TEXT NOT NULL CHECK (
                    source_kind IN ('skill', 'prompt_or_instruction', 'documentation')
                ),
                content_sha256 TEXT NOT NULL,
                byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
                line_count INTEGER NOT NULL CHECK (line_count >= 0),
                directive_line_count INTEGER NOT NULL CHECK (directive_line_count >= 0),
                steering_term_count INTEGER NOT NULL CHECK (steering_term_count >= 0)
            );
            CREATE TABLE prompt_guidance (
                prompt_id TEXT PRIMARY KEY,
                dialect_id TEXT NOT NULL REFERENCES dialects(dialect_id),
                intent TEXT NOT NULL,
                prompt_template TEXT NOT NULL,
                safety_checks TEXT NOT NULL,
                derived_from TEXT NOT NULL
            );
            CREATE TABLE llm_research_sources (
                source_id TEXT PRIMARY KEY,
                year_or_version TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source_type TEXT NOT NULL,
                finding_and_limit TEXT NOT NULL
            );
            CREATE TABLE llm_pillar_controls (
                pillar TEXT PRIMARY KEY,
                control TEXT NOT NULL,
                observable_evidence TEXT NOT NULL
            );
            CREATE TABLE llm_implementation_examples (
                example_id TEXT PRIMARY KEY,
                language TEXT NOT NULL,
                dialect_id TEXT NOT NULL REFERENCES dialects(dialect_id),
                intent TEXT NOT NULL,
                example TEXT NOT NULL,
                limitation TEXT NOT NULL,
                source_url TEXT NOT NULL
            );
            CREATE TABLE prompt_audit_cases (
                source_audit_sha256 TEXT NOT NULL,
                case_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                period TEXT NOT NULL,
                prompt_summary TEXT NOT NULL,
                visible_output_summary TEXT NOT NULL,
                steering_summary TEXT NOT NULL,
                analyst_interpretation TEXT NOT NULL,
                outcome_status TEXT NOT NULL,
                provenance TEXT NOT NULL,
                guidance_id TEXT NOT NULL,
                evidence_kind TEXT NOT NULL DEFAULT 'analyst summary; not raw transcript',
                PRIMARY KEY (source_audit_sha256, case_id)
            );
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE INDEX repository_usage_concept_idx
                ON repository_usage(concept_id);
            CREATE INDEX repository_usage_path_idx
                ON repository_usage(source_path, line_number);
            CREATE INDEX concepts_term_idx
                ON concepts(term);
            """
        )
        db.executemany(
            "INSERT INTO concepts(category, term, description, dialect_support) VALUES (?, ?, ?, ?)",
            CONCEPTS,
        )
        db.executemany(
            "INSERT INTO dialects(dialect_id, display_name, conventions) VALUES (?, ?, ?)",
            DIALECTS,
        )
        db.executemany(
            """
            INSERT INTO llm_research_sources(
                source_id, year_or_version, title, url, source_type, finding_and_limit
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            RESEARCH_SOURCES,
        )
        db.executemany(
            """
            INSERT INTO llm_pillar_controls(pillar, control, observable_evidence)
            VALUES (?, ?, ?)
            """,
            LLM_PILLAR_CONTROLS,
        )
        db.executemany(
            """
            INSERT INTO llm_implementation_examples(
                example_id, language, dialect_id, intent, example, limitation, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            LLM_IMPLEMENTATION_EXAMPLES,
        )
        if audit_cases:
            db.executemany(
                """
                INSERT INTO prompt_audit_cases(
                    source_audit_sha256, case_id, topic, period, prompt_summary,
                    visible_output_summary, steering_summary, analyst_interpretation,
                    outcome_status, provenance, guidance_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(audit_digest, *row) for row in audit_cases],
            )
        db.executemany(
            """
            INSERT INTO dialect_features(
                concept_id, dialect_id, support_status, example_sql, notes
            )
            SELECT concept_id, ?, ?, ?, ? FROM concepts WHERE category = ? AND term = ?
            """,
            [
                (dialect, status, example, notes, category, term)
                for category, term, dialect, status, example, notes in dialect_features()
            ],
        )
        db.executemany(
            """
            INSERT INTO repository_usage(
                concept_id, source_path, source_kind, line_number, excerpt
            )
            SELECT concept_id, ?, ?, ?, ? FROM concepts WHERE term = ?
            """,
            [
                (
                    path,
                    "test"
                    if path.startswith("tests/") or "/tests/" in path
                    else "tooling"
                    if path.startswith("scripts/")
                    else "application",
                    line,
                    excerpt,
                    term,
                )
                for path, line, term, excerpt in usages
            ],
        )
        db.executemany(
            """
            INSERT INTO repository_guidance_sources(
                source_path, source_kind, content_sha256, byte_count, line_count,
                directive_line_count, steering_term_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            guidance_inventory,
        )
        db.executemany(
            """
            INSERT INTO prompt_guidance(
                prompt_id, dialect_id, intent, prompt_template, safety_checks, derived_from
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            PROMPT_GUIDANCE,
        )
        usage_row_count = db.execute("SELECT COUNT(*) FROM repository_usage").fetchone()[0]
        db.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [
                ("schema_version", "4"),
                ("catalog_dialects", "sqlite,sqlserver"),
                ("llm_audit_case_count", str(len(audit_cases))),
                ("llm_audit_source_sha256", audit_digest or "NOT_SUPPLIED"),
                ("source_file_count", str(len(files))),
                ("guidance_source_count", str(len(guidance_inventory))),
                (
                    "guidance_inventory_limit",
                    "Tracked and non-ignored Markdown/RST/TXT repository files up to 2 MB; metadata and counts only, no document text copied.",
                ),
                ("usage_row_count", str(usage_row_count)),
                (
                    "source_scope",
                    "git-listed/unignored source/test files; SQL string literals passed to execute/executescript/executemany and .sql files; generated/dependency/cache directories excluded; dynamically assembled SQL may be missed",
                ),
                (
                    "prompt_history",
                    "No private conversation transcripts are stored; guidance is synthesized from the reference and observed code.",
                ),
            ],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--prompt-audit-zip",
        type=Path,
        help="Optional archive containing Prompt_Usage_Audit.sqlite. The archive's Python script is never executed.",
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = args.output.resolve()
    build_database(root, output, args.prompt_audit_zip)
    with sqlite3.connect(output) as db:
        concepts = db.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        dialect_feature_count = db.execute("SELECT COUNT(*) FROM dialect_features").fetchone()[0]
        usages = db.execute("SELECT COUNT(*) FROM repository_usage").fetchone()[0]
        prompts = db.execute("SELECT COUNT(*) FROM prompt_guidance").fetchone()[0]
        guidance_sources = db.execute(
            "SELECT COUNT(*) FROM repository_guidance_sources"
        ).fetchone()[0]
        audit_cases = db.execute("SELECT COUNT(*) FROM prompt_audit_cases").fetchone()[0]
        implementation_examples = db.execute(
            "SELECT COUNT(*) FROM llm_implementation_examples"
        ).fetchone()[0]
    print(
        f"Built {output}: {concepts} concepts, {dialect_feature_count} dialect entries, "
        f"{usages} repository usages, {prompts} dialect-specific prompt patterns, "
        f"{guidance_sources} repository guidance files, "
        f"{audit_cases} selected prompt-audit summaries, "
        f"{implementation_examples} language examples."
    )


if __name__ == "__main__":
    main()
