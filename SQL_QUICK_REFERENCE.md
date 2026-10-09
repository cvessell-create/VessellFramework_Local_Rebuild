# SQL quick reference

This is a practical reference for reading and writing common SQL. Examples
primarily use portable SQL with **SQL Server (T-SQL)** notes where syntax
differs. `?` placeholders in examples are SQLite/Python parameter syntax;
SQL Server clients commonly use named parameters such as `@customer_id`.
The companion [`data/sql_reference.sqlite`](data/sql_reference.sqlite) indexes
the terms and the SQL patterns found in this repository.

## Dialect first

SQL is not one identical language across database engines. In particular,
SQLite does **not** implement stored procedures, `TRUNCATE TABLE`, `TOP`,
`GETDATE()`, `DATEPART()`, `DATEDIFF()`, `PIVOT`, `ROLLUP`, or `CUBE`.
`RIGHT JOIN` and `FULL OUTER JOIN` are supported by SQLite 3.39.0 and later.
`ALTER VIEW` is not supported by SQLite. Check the actual engine/version
before copying dialect-specific SQL.

The catalog covers both SQL Server (T-SQL) and SQLite. The framework's
implemented database code uses SQLite through Python's `sqlite3` module; the
SQL Server entries are dialect reference material, not evidence of a SQL
Server runtime in this repository.

### Same task, different dialect

| Need | SQL Server (T-SQL) | SQLite |
|---|---|---|
| Bind values | `WHERE id = @id` | `WHERE id = ?` or `WHERE id = :id` |
| Limit rows | `SELECT TOP (10) ... ORDER BY id` or `OFFSET ... FETCH` | `SELECT ... ORDER BY id LIMIT 10` |
| Current timestamp | `GETDATE()` (server local time) | `CURRENT_TIMESTAMP` / `datetime('now')` (UTC) |
| Null fallback | `ISNULL(value, fallback)` or `COALESCE` | `ifnull(value, fallback)` or `COALESCE` |
| String slice | `LEFT(code, 3)` / `RIGHT(code, 3)` | `substr(code, 1, 3)` / `substr(code, -3)` |
| Drop index | `DROP INDEX ix_name ON dbo.items` | `DROP INDEX IF EXISTS ix_name` |
| Reusable routine | `CREATE PROCEDURE` and call with `EXEC` | No stored procedures; use parameterized application code |

SQL Server identifiers often use schemas such as `dbo.items`; SQLite commonly
uses unqualified names. SQL Server types such as `nvarchar` and `datetime2`
are not SQLite's storage model; SQLite applies type affinity. These examples
are guides, not mechanically interchangeable migrations.

## Basic retrieval, columns, and aliases

```sql
SELECT c.id, c.name AS customer_name
FROM customers AS c;
```

- `SELECT` names result columns; `*` selects every column but is usually less
  stable than listing the required fields.
- `FROM` names the source table, view, or subquery.
- `AS` gives a column or table a readable alias. Table aliases can omit `AS`
  in many engines.
- A calculated field is an expression returned as a column:
  `SELECT quantity * unit_price AS line_total FROM order_lines;`
- Use bound parameters for values. Python SQLite uses `?` placeholders:
  `db.execute("SELECT id FROM users WHERE email = ?", (email,))`.

## Filtering, Boolean logic, and sorting

```sql
SELECT id, name
FROM customers
WHERE active = 1
  AND (region IN ('North', 'West') OR region IS NULL)
  AND created_at BETWEEN '2026-01-01' AND '2026-12-31'
  AND name LIKE 'A%'
ORDER BY name ASC, id DESC;
```

- `WHERE` filters rows before grouping. Conditions can use `AND`, `OR`, and
  `NOT`; parentheses make mixed logic explicit.
- `BETWEEN low AND high` is inclusive at both ends. For timestamps, a
  half-open range (`>= start AND < next_start`) is often less error-prone.
- `IN (...)` matches any listed value; `NOT IN` has NULL edge cases, so
  consider `NOT EXISTS` for nullable subqueries.
- `IS NULL` / `IS NOT NULL` test missing values. `= NULL` does not work.
- `LIKE` performs pattern matching (`%` any-length, `_` one character);
  case-sensitivity depends on the engine/collation.
- `ORDER BY` sorts the final result; `ASC` is ascending (default), `DESC`
  descending. Without `ORDER BY`, row order is not guaranteed.
- `TOP (10)` is SQL Server syntax and belongs after `SELECT`. SQLite uses
  `LIMIT 10` at the end; standard SQL also defines `FETCH FIRST`.

## Functions, expressions, and conditional logic

```sql
SELECT
  UPPER(LTRIM(RTRIM(name))) AS clean_name,
  LEFT(code, 3) AS prefix,
  SUBSTRING(description, 1, 40) AS preview,
  ROUND(amount * POWER(1 + rate, years), 2) AS future_value,
  CASE WHEN score >= 80 THEN 'pass'
       WHEN score IS NULL THEN 'unscored'
       ELSE 'review' END AS result
FROM evaluations;
```

| Function / expression | Purpose and compatibility notes |
|---|---|
| `LEFT`, `RIGHT` | Return leading/trailing characters in SQL Server. SQLite commonly uses `substr(text, start, length)`; negative start positions count from the right. |
| `SUBSTRING` | Extract part of a string. SQL Server uses `SUBSTRING(text, start, length)`; SQLite uses `substr`. |
| `LTRIM`, `RTRIM` | Remove leading/trailing spaces. SQLite supports both. |
| `UPPER`, `LOWER` | Change ASCII/locale-supported letter case; Unicode details vary by engine and extensions. |
| `GETDATE()` | SQL Server current local date/time. SQLite commonly uses `CURRENT_TIMESTAMP` or `datetime('now')` (UTC). |
| `DATEPART(part, date)` | SQL Server extracts a date component. SQLite uses `strftime`/`date` functions. |
| `DATEDIFF(part, start, end)` | SQL Server counts date-part boundaries; SQLite uses date/time functions such as `julianday` and `unixepoch`. Semantics are not a direct one-to-one translation. |
| `ROUND(value, places)` | Round numeric values; tie behavior/precision can vary. |
| `PI()` | Returns pi in SQL Server. SQLite may need a math-enabled build or a supplied constant. |
| `POWER(base, exponent)` | Exponentiation in SQL Server and math-enabled SQLite; verify SQLite build support. |
| `ISNULL(value, fallback)` | SQL Server null fallback. SQLite equivalent: `ifnull(value, fallback)` or standard `COALESCE(value, fallback)`. SQL Server also has `COALESCE`. |
| `CASE WHEN ... THEN ... ELSE ... END` | Conditional expression. `ELSE` is optional; omitted `ELSE` yields NULL when no `WHEN` matches. |

## Summaries and grouped results

```sql
SELECT department, COUNT(*) AS people,
       AVG(salary) AS average_salary,
       MIN(salary) AS min_salary, MAX(salary) AS max_salary,
       SUM(salary) AS total_salary
FROM employees
GROUP BY department
HAVING COUNT(*) >= 2;
```

- `DISTINCT` removes duplicate result rows (or duplicate values in a selected
  expression); it is not a substitute for choosing the right grouping.
- `COUNT(*)` counts rows; `COUNT(column)` ignores NULLs in that column.
  `SUM`, `AVG`, `MIN`, and `MAX` aggregate non-NULL values.
- `GROUP BY` creates one result group per key combination.
- `HAVING` filters groups after aggregation; use `WHERE` for row-level filters.
- SQL Server adds `GROUP BY ROLLUP(...)` and `GROUP BY CUBE(...)` for
  subtotal combinations. SQLite has no built-in `ROLLUP` or `CUBE`; use
  explicit `UNION ALL` queries or aggregate in application code.
- SQL Server `PIVOT` rotates values into columns. SQLite has no built-in
  `PIVOT`; conditional aggregates with `CASE` are a common alternative.
- `FOR` is not a general-purpose clause. SQL Server uses forms such as
  `FOR XML` / `FOR JSON`; other engines use `FOR UPDATE`, and `FOR` also
  appears in cursor syntax. The valid form is engine- and statement-specific.

## Window functions and ranking

```sql
SELECT department, employee, salary,
       ROW_NUMBER() OVER (
         PARTITION BY department ORDER BY salary DESC
       ) AS row_num,
       RANK() OVER (ORDER BY salary DESC) AS salary_rank,
       DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_salary_rank,
       NTILE(4) OVER (ORDER BY salary DESC) AS quartile
FROM employee_pay;
```

- `OVER (...)` makes an aggregate or ranking function operate as a window
  without collapsing result rows.
- `PARTITION BY` restarts the window calculation for each partition.
- `ROW_NUMBER()` gives every row a unique sequential number; ties are broken
  according to remaining `ORDER BY` keys, so add a stable tie-breaker.
- `RANK()` leaves gaps after ties; `DENSE_RANK()` does not.
- `NTILE(n)` divides ordered rows into up to `n` buckets.
- Window functions are supported by current SQLite and SQL Server versions;
  check older engine versions.

## Joins

```sql
SELECT o.id, c.name
FROM orders AS o
INNER JOIN customers AS c ON c.id = o.customer_id;
```

- `JOIN` combines rows from tables. `ON` states the match condition.
- `INNER JOIN` keeps matching pairs only; `INNER` may be omitted.
- `LEFT [OUTER] JOIN` keeps every left row and fills unmatched right columns
  with NULL. A right-table predicate in `WHERE` can accidentally remove those
  unmatched rows; place match restrictions in `ON` when appropriate.
- `RIGHT [OUTER] JOIN` preserves the right side. It is supported by SQL Server
  and current SQLite; swapping table order and using `LEFT JOIN` is often
  clearer and more portable.
- `FULL [OUTER] JOIN` preserves unmatched rows from both sides. Supported by
  SQL Server and current SQLite; older SQLite releases may require a
  `LEFT JOIN` plus an anti-match `UNION ALL`.
- `CROSS JOIN` returns every left/right combination (Cartesian product). Use
  it only when the multiplication of row counts is intended.
- A self join joins a table to itself using different aliases:

```sql
SELECT e.name AS employee, m.name AS manager
FROM employees AS e
LEFT JOIN employees AS m ON m.id = e.manager_id;
```

## Set logic, subqueries, and common table expressions

```sql
SELECT customer_id FROM current_orders
UNION
SELECT customer_id FROM archived_orders;
```

- `UNION` combines compatible result shapes and removes duplicates.
- `UNION ALL` keeps duplicates and is usually cheaper.
- `INTERSECT` returns rows present in both results.
- `EXCEPT` returns rows in the first result but not the second. SQL Server's
  analogous operator is `EXCEPT`; Oracle uses `MINUS`.
- Set operands need the same number of columns in compatible types.

```sql
SELECT c.id
FROM customers AS c
WHERE EXISTS (
  SELECT 1 FROM orders AS o WHERE o.customer_id = c.id
);
```

- A subquery is a query nested inside another statement. It may be scalar,
  return a set for `IN`, or correlate to the outer query.
- `EXISTS` tests whether a subquery returns at least one row; `NOT EXISTS`
  tests the inverse.
- `WITH` defines a common table expression (CTE) scoped to one statement:

```sql
WITH totals AS (
  SELECT customer_id, SUM(amount) AS amount
  FROM orders GROUP BY customer_id
)
SELECT customer_id, amount FROM totals WHERE amount > 100;
```

CTEs can improve readability; they are not inherently faster than equivalent
subqueries. Recursive CTE syntax has engine-specific details.

## Insert, update, delete, and transaction safety

```sql
INSERT INTO customers (name, active)
VALUES (?, ?);

UPDATE customers
SET active = ?
WHERE id = ?;

DELETE FROM customers
WHERE id = ?;
```

- `INSERT INTO` adds rows. Name the destination columns. `VALUES` supplies
  corresponding values; multi-row `VALUES` and `INSERT ... SELECT` are common.
- `UPDATE ... SET` changes selected columns. Preview the target with the same
  `WHERE` clause as a `SELECT` before a high-impact update.
- `DELETE FROM` removes matching rows. Without `WHERE`, it removes every row.
- Use bound parameters for values; do not concatenate untrusted input into SQL.
  Parameters generally cannot stand in for table/column names.
- Wrap related changes in a transaction when atomicity is required:

```sql
BEGIN;
UPDATE accounts SET balance = balance - ? WHERE id = ?;
UPDATE accounts SET balance = balance + ? WHERE id = ?;
COMMIT;
-- On error, use ROLLBACK instead of COMMIT.
```

- `TRUNCATE TABLE` removes all rows while retaining the table. It is supported
  by SQL Server, not SQLite. SQLite's `DELETE FROM table_name` removes all
  rows but has different identity/transaction behavior; do not substitute
  blindly. Confirm constraints, triggers, backups, and rollback expectations.

## Tables, indexes, views, and stored procedures

```sql
CREATE TABLE notes (
  id INTEGER PRIMARY KEY,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX notes_created_at_idx ON notes(created_at);
CREATE VIEW recent_notes AS
  SELECT id, body, created_at FROM notes;
```

- `CREATE TABLE` defines columns, types, constraints, keys, and relationships.
  SQLite uses dynamic typing with type affinities; declare constraints
  explicitly (`NOT NULL`, `UNIQUE`, `CHECK`, foreign keys).
- `DROP TABLE` removes the table definition and its data; check dependencies
  and use migrations/backups rather than casual destructive changes.
- `CREATE INDEX` speeds selected lookups/orderings at a storage and write cost.
  Index the columns that queries actually filter/join/sort on; composite index
  column order matters. `DROP INDEX index_name` removes an index.
- `CREATE VIEW` saves a named query, not a separate copy of its rows.
  `DROP VIEW` removes the view. SQL Server supports `ALTER VIEW`; SQLite
  requires dropping and recreating a view (account for dependent views).
- SQL Server stored procedures package statements and parameters on the
  server. A typical pattern is:

```sql
CREATE PROCEDURE dbo.FindCustomer
  @CustomerId int
AS
BEGIN
  SET NOCOUNT ON;
  SELECT id, name FROM dbo.Customers WHERE id = @CustomerId;
END;
GO
EXEC dbo.FindCustomer @CustomerId = 42;
```

  `ALTER PROCEDURE` changes an existing procedure; SQL Server also supports
  `CREATE OR ALTER PROCEDURE`. `BEGIN ... END` delimits the procedure body.
  `EXEC` / `EXECUTE` invokes a SQL Server procedure; `CALL` is used by other
  engines such as PostgreSQL/MySQL. **SQLite has no stored-procedure,
  `CREATE/ALTER/DROP PROCEDURE`, `EXEC`, or `CALL` feature.** Put reusable
  SQLite operations in application code or a transaction script, bind
  parameters, and version schema changes as migrations.

## Repository use map and future prompting

### Appendix: prompt injection and visible-reasoning audit

SQL injection and prompt injection are different trust-boundary failures.
Bound SQL values protect the database parser; they do not prevent an LLM from
treating a retrieved row as an instruction. Conversely, an instruction
hierarchy does not make dynamically concatenated SQL safe. Keep user/system
instructions separate from retrieved text and authorize tool side effects
outside the model.

The paired prompt-audit catalog can import selected, analyst-summarized prompt
cases to compare explicit user steering with visible assistant outputs and
outcome evidence. It cannot reconstruct either participant's hidden reasoning.
The supplied ZIP provides 12 selected summaries—not all conversations or raw
turns—and expressly labels its SQL comparison as an analogy, not evidence that
the prompts executed as SQL. See
[`docs/prompt-steering-and-reasoning-audit.md`](docs/prompt-steering-and-reasoning-audit.md)
for the full analysis, research sources, six-pillar crosswalk, and reproducible
limits.

Cross-language parameterized-value examples are indexed in
`llm_implementation_examples`: T-SQL `sp_executesql`, Python `sqlite3`, and R
DBI/RSQLite. They bind values, not identifiers. R's result handle must be
cleared; SQL Server/SQLite placeholder conventions are not interchangeable.

The reference catalog stores **one feature row per dialect** in
`dialect_features`, including support status, notes, and a syntax example
where applicable. Use this query to compare a feature:

```sql
SELECT c.term, d.display_name, f.support_status, f.example_sql, f.notes
FROM concepts AS c
JOIN dialect_features AS f ON f.concept_id = c.concept_id
JOIN dialects AS d ON d.dialect_id = f.dialect_id
WHERE c.term = 'TOP'
ORDER BY d.dialect_id;
```

Reusable prompt templates are paired by intent in `prompt_guidance`. Choose
the `sqlite` or `sqlserver` template explicitly. For example:

**SQL Server prompt**

> Write T-SQL for the target SQL Server version to list the ten newest
> customers. Use `TOP` or `OFFSET/FETCH`, `@named` parameters for values,
> deterministic ordering, and state any NULL or collation assumptions.

**SQLite prompt**

> Write SQLite SQL for the target SQLite version to list the ten newest
> customers. Use `LIMIT`, `?` or `:named` bound parameters, deterministic
> ordering, and state any NULL or collation assumptions. Do not use SQL Server
> syntax.

For writes, migrations, reusable logic, repository searches, and reviews, use
the corresponding dialect-specific prompt rows rather than silently
translating syntax between engines.

The SQLite catalog extracts SQL string literals passed to `execute`,
`executescript`, or `executemany`, plus `.sql` files, from tracked or unignored
source/test files (`.py`, `.sql`, `.js`, `.ts`, `.tsx`, `.jsx`, and `.html`).
It excludes generated builds, dependency directories, and caches. Dynamically
assembled SQL may not be detected. Each usage row contains the path, line,
matched concept, source kind, and a short source excerpt. A concept with no
usage row is **not observed in the scanned scope**, not proof that it is unused
everywhere.

The database does not contain private conversation transcripts. Its
`prompt_guidance` rows are reusable prompt patterns synthesized from this
reference and observed repository practices; they help future coding prompts
specify the engine, scope, parameters, safety checks, and validation.

Regenerate after code or documentation changes:

```sh
python scripts/build_sql_reference_db.py
python -m pytest tests/test_sql_quick_reference.py
```

Quickly inspect the catalog with Python:

```sh
python - <<'PY'
import sqlite3
db = sqlite3.connect("data/sql_reference.sqlite")
for row in db.execute("""
    SELECT c.term, COUNT(u.usage_id) AS repo_uses
    FROM concepts AS c
    LEFT JOIN repository_usage AS u USING (concept_id)
    GROUP BY c.concept_id
    ORDER BY c.category, c.term
"""):
    print(*row, sep=": ")
PY
```

Tables: `concepts` (reference terms), `dialects` (engine conventions),
`dialect_features` (paired engine support/examples),
`repository_usage` (source-grounded code occurrences), `prompt_guidance`
(safe reusable request patterns, one per dialect), and `metadata`
(scan scope/version).
