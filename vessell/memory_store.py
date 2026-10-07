# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Persist, review, and retrieve local user-authored memories with provenance."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCOPES = ("user", "repository")
STATUSES = ("pending", "approved", "corrected", "rejected")
DEFAULT_DATABASE = Path(".vessell/memories.sqlite3")


def _timestamp(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("valid_until must be an ISO-8601 timestamp with a timezone.") from error
    if parsed.tzinfo is None:
        raise ValueError("valid_until must include a timezone.")
    return parsed.astimezone(UTC).isoformat()


def _validate_memory(statement: Any, scope: Any, citations: Any) -> None:
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError("statement must be a non-empty string.")
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of: {', '.join(SCOPES)}.")
    if not isinstance(citations, list) or not citations:
        raise ValueError("citations must be a non-empty list of source references.")
    if any(not isinstance(item, str) or not item.strip() for item in citations):
        raise ValueError("each citation must be a non-empty string.")


def _connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            statement TEXT NOT NULL CHECK(length(trim(statement)) > 0),
            scope TEXT NOT NULL CHECK(scope IN ('user', 'repository')),
            citations_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'corrected', 'rejected')),
            created_at TEXT NOT NULL,
            valid_until TEXT,
            supersedes_id TEXT REFERENCES memories(id)
        );
        CREATE TABLE IF NOT EXISTS memory_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT NOT NULL REFERENCES memories(id),
            decision TEXT NOT NULL CHECK(decision IN ('created', 'approved', 'corrected', 'rejected')),
            reviewer TEXT NOT NULL,
            note TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );
        """
    )
    return connection


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "statement": row["statement"],
        "scope": row["scope"],
        "citations": json.loads(row["citations_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "valid_until": row["valid_until"],
        "supersedes_id": row["supersedes_id"],
    }


def add_memory(database: Path, memory: dict[str, Any]) -> str:
    """Add a pending memory, preserving its supplied citations and optional expiry."""
    statement = memory.get("statement")
    scope = memory.get("scope")
    citations = memory.get("citations")
    _validate_memory(statement, scope, citations)
    valid_until = _timestamp(memory.get("valid_until"))
    identifier = str(uuid.uuid4())
    now = _now()
    with _connect(database) as connection:
        connection.execute(
            """INSERT INTO memories
               (id, statement, scope, citations_json, status, created_at, valid_until)
               VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
            (identifier, statement.strip(), scope, json.dumps(citations), now, valid_until),
        )
        connection.execute(
            """INSERT INTO memory_reviews (memory_id, decision, reviewer, note, occurred_at)
               VALUES (?, 'created', ?, '', ?)""",
            (identifier, "system", now),
        )
    return identifier


def review_memory(
    database: Path,
    identifier: str,
    decision: str,
    *,
    reviewer: str = "local-user",
    note: str = "",
    replacement: dict[str, Any] | None = None,
) -> str | None:
    """Review a pending memory; correction creates a new pending version."""
    if decision not in ("approve", "reject", "correct"):
        raise ValueError("decision must be approve, reject, or correct.")
    if not reviewer.strip():
        raise ValueError("reviewer must not be empty.")
    if decision == "correct":
        if replacement is None:
            raise ValueError("correct requires replacement content.")
        _validate_memory(
            replacement.get("statement"), replacement.get("scope"), replacement.get("citations")
        )
        if replacement["scope"] != _existing_scope(database, identifier):
            raise ValueError("a correction must retain the original memory scope.")
        replacement_expiry = _timestamp(replacement.get("valid_until"))
    elif replacement is not None:
        raise ValueError("replacement content is only valid with decision=correct.")
    else:
        replacement_expiry = None

    with _connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM memories WHERE id = ?", (identifier,)).fetchone()
        if row is None:
            raise ValueError(f"Memory not found: {identifier}")
        allowed_statuses = ("pending", "approved") if decision in ("reject", "correct") else ("pending",)
        if row["status"] not in allowed_statuses:
            raise ValueError(
                f"Cannot {decision} a memory with status {row['status']}."
            )
        now = _now()
        status = {"approve": "approved", "reject": "rejected", "correct": "corrected"}[decision]
        connection.execute("UPDATE memories SET status = ? WHERE id = ?", (status, identifier))
        connection.execute(
            """INSERT INTO memory_reviews (memory_id, decision, reviewer, note, occurred_at)
               VALUES (?, ?, ?, ?, ?)""",
            (identifier, decision, reviewer, note, now),
        )
        if decision != "correct":
            return None
        replacement_id = str(uuid.uuid4())
        connection.execute(
            """INSERT INTO memories
               (id, statement, scope, citations_json, status, created_at, valid_until, supersedes_id)
               VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (
                replacement_id,
                replacement["statement"].strip(),
                replacement["scope"],
                json.dumps(replacement["citations"]),
                now,
                replacement_expiry,
                identifier,
            ),
        )
        connection.execute(
            """INSERT INTO memory_reviews (memory_id, decision, reviewer, note, occurred_at)
               VALUES (?, 'created', ?, ?, ?)""",
            (replacement_id, reviewer, f"Correction of {identifier}", now),
        )
        return replacement_id


def _existing_scope(database: Path, identifier: str) -> str:
    with _connect(database) as connection:
        row = connection.execute("SELECT scope FROM memories WHERE id = ?", (identifier,)).fetchone()
    if row is None:
        raise ValueError(f"Memory not found: {identifier}")
    return str(row["scope"])


def list_memories(database: Path, status: str | None = None) -> list[dict[str, Any]]:
    """List memories in creation order, optionally restricted to a valid status."""
    if status is not None and status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}.")
    query = "SELECT * FROM memories"
    parameters: tuple[str, ...] = ()
    if status is not None:
        query += " WHERE status = ?"
        parameters = (status,)
    query += " ORDER BY created_at, id"
    with _connect(database) as connection:
        return [_row_to_dict(row) for row in connection.execute(query, parameters)]


def retrieve_memories(
    database: Path, query: str, scope: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Return current, approved, unexpired memories ranked by lexical relevance."""
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of: {', '.join(SCOPES)}.")
    if limit < 1:
        raise ValueError("limit must be at least 1.")
    terms = set(re.findall(r"[\w-]+", query.casefold()))
    if not terms:
        raise ValueError("query must contain at least one searchable term.")
    now = _now()
    with _connect(database) as connection:
        rows = connection.execute(
            """SELECT * FROM memories
               WHERE status = 'approved' AND scope = ?
                 AND (valid_until IS NULL OR valid_until > ?)
               ORDER BY created_at DESC, id""",
            (scope, now),
        ).fetchall()
    ranked: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        memory = _row_to_dict(row)
        matched = terms.intersection(re.findall(r"[\w-]+", memory["statement"].casefold()))
        if matched:
            memory["relevance"] = len(matched) / len(terms)
            ranked.append((len(matched), memory))
    ranked.sort(key=lambda item: (-item[0], item[1]["created_at"], item[1]["id"]))
    return [memory for _, memory in ranked[:limit]]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object.")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vessell-memory",
        description="Store, review, and retrieve locally managed memories with provenance.",
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Add a memory as pending review")
    add.add_argument("input", type=Path, help="JSON object with statement, scope, and citations")
    review = commands.add_parser("review", help="Approve, reject, or correct a pending memory")
    review.add_argument("id")
    review.add_argument("decision", choices=("approve", "reject", "correct"))
    review.add_argument("--reviewer", default="local-user")
    review.add_argument("--note", default="")
    review.add_argument("--replacement", type=Path, help="JSON replacement for a correction")
    listing = commands.add_parser("list", help="List memory records")
    listing.add_argument("--status", choices=STATUSES)
    retrieve = commands.add_parser("retrieve", help="Find current approved memories")
    retrieve.add_argument("query")
    retrieve.add_argument("--scope", required=True, choices=SCOPES)
    retrieve.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        if args.command == "add":
            identifier = add_memory(args.database, _read_json(args.input))
            print(json.dumps({"id": identifier, "status": "pending"}))
        elif args.command == "review":
            replacement = _read_json(args.replacement) if args.replacement else None
            if args.decision == "correct" and replacement is None:
                raise ValueError("--replacement is required when decision is correct.")
            if args.decision != "correct" and replacement is not None:
                raise ValueError("--replacement is only valid when decision is correct.")
            replacement_id = review_memory(
                args.database,
                args.id,
                args.decision,
                reviewer=args.reviewer,
                note=args.note,
                replacement=replacement,
            )
            final_status = {
                "approve": "approved",
                "reject": "rejected",
                "correct": "corrected",
            }[args.decision]
            result = {"id": args.id, "status": final_status}
            if replacement_id:
                result["replacement_id"] = replacement_id
            print(json.dumps(result))
        elif args.command == "list":
            print(json.dumps(list_memories(args.database, args.status), indent=2))
        else:
            print(
                json.dumps(
                    retrieve_memories(args.database, args.query, args.scope, args.limit), indent=2
                )
            )
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as error:
        print(f"MEMORY STORE FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
