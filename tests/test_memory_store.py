import json

import pytest

from vessell.memory_store import (
    add_memory,
    list_memories,
    main,
    retrieve_memories,
    review_memory,
)

MEMORY = {
    "statement": "Use Python 3.12 or newer for this repository.",
    "scope": "repository",
    "citations": ["pyproject.toml:10", "CONTRIBUTING.md:15"],
}


def test_memories_are_pending_until_approved_and_retrieval_is_scoped(tmp_path) -> None:
    database = tmp_path / "state" / "memories.sqlite3"
    identifier = add_memory(database, MEMORY)

    assert list_memories(database)[0]["status"] == "pending"
    assert retrieve_memories(database, "Python 3.12", "repository") == []

    review_memory(database, identifier, "approve", reviewer="reviewer-1", note="Verified")
    found = retrieve_memories(database, "Python compatibility", "repository")
    assert [item["id"] for item in found] == [identifier]
    assert found[0]["citations"] == MEMORY["citations"]
    assert found[0]["scope"] == "repository"
    assert found[0]["status"] == "approved"
    assert retrieve_memories(database, "Python compatibility", "user") == []


def test_correction_versions_original_and_requires_new_approval(tmp_path) -> None:
    database = tmp_path / "memories.sqlite3"
    identifier = add_memory(database, MEMORY)
    replacement = {
        **MEMORY,
        "statement": "Use Python 3.12+; CI also tests Python 3.13.",
        "citations": [".github/workflows/ci.yml:12-17"],
    }

    replacement_id = review_memory(
        database, identifier, "correct", replacement=replacement, reviewer="reviewer-2"
    )
    records = {memory["id"]: memory for memory in list_memories(database)}
    assert records[identifier]["status"] == "corrected"
    assert records[replacement_id]["status"] == "pending"
    assert records[replacement_id]["supersedes_id"] == identifier
    assert retrieve_memories(database, "Python", "repository") == []

    review_memory(database, replacement_id, "approve")
    assert [row["id"] for row in retrieve_memories(database, "Python 3.13", "repository")] == [
        replacement_id
    ]


def test_reject_and_expired_memories_are_not_retrieved(tmp_path) -> None:
    database = tmp_path / "memories.sqlite3"
    rejected = add_memory(database, MEMORY)
    review_memory(database, rejected, "reject", note="Citation not checked")
    expired = add_memory(database, {**MEMORY, "valid_until": "2000-01-01T00:00:00Z"})
    review_memory(database, expired, "approve")

    assert retrieve_memories(database, "Python", "repository") == []
    assert list_memories(database, "rejected")[0]["id"] == rejected


@pytest.mark.parametrize(
    "memory",
    [
        {**MEMORY, "statement": ""},
        {**MEMORY, "scope": "global"},
        {**MEMORY, "citations": []},
        {**MEMORY, "valid_until": "tomorrow"},
        {**MEMORY, "valid_until": "2030-01-01T00:00:00"},
    ],
)
def test_invalid_memory_fields_are_rejected(tmp_path, memory: dict) -> None:
    with pytest.raises(ValueError):
        add_memory(tmp_path / "memories.sqlite3", memory)


def test_only_pending_memories_can_be_approved_and_scope_cannot_change(tmp_path) -> None:
    database = tmp_path / "memories.sqlite3"
    identifier = add_memory(database, MEMORY)
    review_memory(database, identifier, "approve")
    with pytest.raises(ValueError, match="Cannot approve"):
        review_memory(database, identifier, "approve")
    with pytest.raises(ValueError, match="retain the original"):
        review_memory(
            database,
            identifier,
            "correct",
            replacement={**MEMORY, "scope": "user"},
        )


def test_cli_add_review_retrieve_and_correction(tmp_path, capsys) -> None:
    database = tmp_path / "memories.sqlite3"
    input_path = tmp_path / "memory.json"
    input_path.write_text(json.dumps(MEMORY), encoding="utf-8")
    assert main(["--database", str(database), "add", str(input_path)]) == 0
    created = json.loads(capsys.readouterr().out)

    assert main(["--database", str(database), "review", created["id"], "approve"]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "--database",
                str(database),
                "retrieve",
                "Python 3.12",
                "--scope",
                "repository",
            ]
        )
        == 0
    )
    retrieved = json.loads(capsys.readouterr().out)
    assert retrieved[0]["id"] == created["id"]


def test_cli_rejects_malformed_input_and_requires_correction_file(tmp_path, capsys) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("[]", encoding="utf-8")
    database = tmp_path / "memories.sqlite3"
    assert main(["--database", str(database), "add", str(bad_path)]) == 1
    capsys.readouterr()
    assert main(["--database", str(database), "review", "unknown", "correct"]) == 1


def test_retrieval_rejects_empty_query_and_invalid_limit(tmp_path) -> None:
    database = tmp_path / "memories.sqlite3"
    with pytest.raises(ValueError, match="searchable"):
        retrieve_memories(database, "   ", "repository")
    with pytest.raises(ValueError, match="at least 1"):
        retrieve_memories(database, "python", "repository", limit=0)
