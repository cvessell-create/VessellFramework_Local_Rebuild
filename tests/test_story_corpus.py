from vessell import story_corpus as sc


def test_every_exported_line_is_verbatim_and_hashed():
    corpus = sc.extract()
    assert corpus["lines"]
    assert sc.verify(corpus) == []


def test_tampered_line_is_detected():
    corpus = sc.extract()
    corpus["lines"][0] = dict(corpus["lines"][0], text=corpus["lines"][0]["text"] + " edited")
    assert sc.verify(corpus)


def test_personal_incident_section_and_references_are_excluded():
    paper = [l for l in sc.extract()["lines"] if l["role"] == "author-paper"]
    assert paper
    assert not any(l["section"].startswith(("1.", "References")) for l in paper)
    assert all(l["line_start"] > 36 for l in paper)


def test_all_six_stages_have_owner_lines():
    corpus = sc.extract()
    assert [s["id"] for s in corpus["stages"]] == [
        "intake", "corroboration", "gate", "status", "dependents", "correction"]
    for stage in corpus["stages"]:
        assert any(l["stage"] == stage["id"] for l in corpus["lines"]), stage["id"]
