from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.build_sql_reference_db import (
    CONCEPTS,
    DIALECTS,
    PROMPT_GUIDANCE,
    PROMPT_GUIDANCE_TEMPLATES,
    build_database,
    collect_guidance_inventory,
    tracked_guidance_files,
)
from vessell.prompt_audit import summarize_prompt_audit

ROOT = Path(__file__).resolve().parents[1]


def test_sql_reference_database_contains_full_catalog_and_prompt_playbook(tmp_path: Path) -> None:
    database = tmp_path / "sql-reference.sqlite"
    build_database(ROOT, database)

    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT COUNT(*) FROM concepts").fetchone()[0] == len(CONCEPTS)
        assert db.execute("SELECT COUNT(*) FROM prompt_guidance").fetchone()[0] == len(
            PROMPT_GUIDANCE
        )
        assert db.execute("SELECT COUNT(*) FROM dialects").fetchone()[0] == len(DIALECTS)
        assert db.execute("SELECT COUNT(*) FROM dialect_features").fetchone()[0] == (
            len(CONCEPTS) * len(DIALECTS)
        )
        assert (
            db.execute("SELECT COUNT(DISTINCT dialect_id) FROM dialect_features").fetchone()[0] == 2
        )
        assert db.execute(
            "SELECT COUNT(*) FROM prompt_guidance WHERE dialect_id = 'sqlite'"
        ).fetchone()[0] == len(PROMPT_GUIDANCE_TEMPLATES)
        assert db.execute(
            "SELECT COUNT(*) FROM prompt_guidance WHERE dialect_id = 'sqlserver'"
        ).fetchone()[0] == len(PROMPT_GUIDANCE_TEMPLATES)
        assert db.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT intent FROM prompt_guidance
                GROUP BY intent HAVING COUNT(DISTINCT dialect_id) = 2
            )
            """
        ).fetchone()[0] == len(PROMPT_GUIDANCE_TEMPLATES)
        assert db.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone() == (
            "4",
        )
        assert db.execute("SELECT value FROM metadata WHERE key = 'usage_row_count'").fetchone()[
            0
        ] == str(db.execute("SELECT COUNT(*) FROM repository_usage").fetchone()[0])
        assert (
            db.execute(
                "SELECT COUNT(*) FROM repository_usage WHERE source_path = 'vessell/ambient/store.py'"
            ).fetchone()[0]
            > 0
        )
        assert db.execute("SELECT COUNT(*) FROM repository_guidance_sources").fetchone()[0] > 0
        assert db.execute(
            """
            SELECT source_path FROM repository_guidance_sources
            WHERE source_path = '.github/copilot-instructions.md'
            """
        ).fetchone() == (".github/copilot-instructions.md",)
        assert db.execute(
            """
            SELECT support_status FROM dialect_features f
            JOIN concepts c USING (concept_id)
            WHERE c.term = 'CREATE PROCEDURE' AND f.dialect_id = 'sqlite'
            """
        ).fetchone() == ("unsupported",)
        assert db.execute(
            """
            SELECT example_sql FROM dialect_features f
            JOIN concepts c USING (concept_id)
            WHERE c.term = 'TOP' AND f.dialect_id = 'sqlite'
            """
        ).fetchone() == ("SELECT id FROM items ORDER BY id LIMIT 10;",)
        assert db.execute(
            """
            SELECT example_sql FROM dialect_features f
            JOIN concepts c USING (concept_id)
            WHERE c.term = 'TOP' AND f.dialect_id = 'sqlserver'
            """
        ).fetchone() == ("SELECT TOP (10) id FROM dbo.items ORDER BY id;",)
        assert db.execute(
            """
            SELECT dialect_id FROM prompt_guidance
            WHERE prompt_id = 'stored-procedure-sqlite'
            """
        ).fetchone() == ("sqlite",)
        assert (
            db.execute(
                """
            SELECT prompt_template FROM prompt_guidance
            WHERE prompt_id = 'stored-procedure-sqlite'
            """
            )
            .fetchone()[0]
            .find("SQLite has none")
            >= 0
        )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM repository_usage WHERE source_path LIKE 'tests/%'"
            ).fetchone()[0]
            > 0
        )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM concepts WHERE term IN ('TRUNCATE TABLE', 'CREATE PROCEDURE', 'PIVOT')"
            ).fetchone()[0]
            == 3
        )
        assert (
            db.execute("SELECT value FROM metadata WHERE key = 'prompt_history'")
            .fetchone()[0]
            .startswith("No private conversation transcripts")
        )
        assert (
            db.execute(
                """
                SELECT COUNT(*) FROM repository_usage u
                JOIN concepts c USING (concept_id)
                WHERE c.term = 'CREATE PROCEDURE'
                """
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                """
                SELECT COUNT(*) FROM repository_usage
                WHERE source_path = 'vessell/ambient/store.py'
                  AND source_kind = 'application'
                """
            ).fetchone()[0]
            > 0
        )


def test_sql_reference_quick_guide_covers_requested_engine_boundaries() -> None:
    guide = (ROOT / "SQL_QUICK_REFERENCE.md").read_text(encoding="utf-8")
    for term in (
        "TRUNCATE TABLE",
        "CREATE PROCEDURE",
        "ALTER PROCEDURE",
        "DROP PROCEDURE",
        "ROLLUP",
        "CUBE",
        "PIVOT",
        "FULL [OUTER] JOIN",
        "ROW_NUMBER()",
        "PARTITION BY",
        "ISNULL",
        "GETDATE()",
        "CREATE VIEW",
        "ALTER VIEW",
        "DROP VIEW",
        "Same task, different dialect",
        "SQL Server prompt",
        "SQLite prompt",
        "dialect_features",
    ):
        assert term in guide


def test_guidance_inventory_stores_hashes_and_counts_not_source_text() -> None:
    files = tracked_guidance_files(ROOT)
    inventory = collect_guidance_inventory(ROOT, files)
    assert inventory
    copilot = next(row for row in inventory if row[0] == ".github/copilot-instructions.md")
    assert copilot[1] == "prompt_or_instruction"
    assert len(copilot[2]) == 64
    assert copilot[3] > 0
    assert copilot[5] > 0
    assert "Follow" not in repr(copilot)
    assert (
        summarize_prompt_audit(ROOT / "data" / "sql_reference.sqlite")[
            "repository_guidance_sources"
        ]["total"]
        > 0
    )
