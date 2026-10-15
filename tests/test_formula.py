import itertools

import pytest

from vessell.formula import case_gate, case_state, correct_case, evaluate, transform_case


def test_ascii_states_and_lowercase_compliance():
    assert [case_state(c) for c in "Az0$"] == [1, 0, None, None]
    assert case_gate("Review", {1: 0}) == 0
    result = correct_case("Review", {1: 0})
    assert result == {"text": "review", "initial_product": 0, "product": 1,
                      "state": "PASS", "mismatches_before": 1, "correction_passes": 1}
    assert correct_case("review", {1: 0})["correction_passes"] == 0
    assert case_gate("review", {1: 0}) == 1


def test_empty_case_mask_is_vacuously_compliant_not_a_runtime_evidence_pass():
    for text in ("", "Ab0!"):
        assert case_gate(text, {}) == 1
        assert transform_case(text, {}) == text
        assert correct_case(text, {})["correction_passes"] == 0
    assert evaluate([], [], "r")["state"] == "DOWN"


@pytest.mark.parametrize("text,mask", [
    ("Ab", {0: 1}), ("Ab", {3: 1}), ("Ab", {True: 1}), ("Ab", {1.0: 1}),
    ("Ab", {1: True}), ("Ab", {1: 2}), ("Ab", {1: "0"}), ("Ab", {"1": 0}),
    ("A0", {2: 0}), ("A!", {2: 1}), ("é", {}), ("ß", {1: 1}), ("", {1: 1}),
    ("İ", {}), ("😀", {}), ("Ab", None), (None, {}),
])
def test_invalid_case_policies_are_explicit_errors(text, mask):
    for operation in (case_gate, transform_case, correct_case):
        with pytest.raises((ValueError, TypeError)):
            operation(text, mask)


@pytest.mark.parametrize("character", ["", "AB", "é", "ß", "İ", "😀", None])
def test_case_state_rejects_non_ascii_or_non_character_values(character):
    with pytest.raises((ValueError, TypeError)):
        case_state(character)


def test_exhaustive_9330_case_policies_and_minimum_changes():
    count = 0
    for size in range(1, 6):
        for bits in itertools.product((0, 1), repeat=size):
            text = "".join("A" if bit else "a" for bit in bits)
            for choices in itertools.product((None, 0, 1), repeat=size):
                mask = {i + 1: bit for i, bit in enumerate(choices) if bit is not None}
                original_mask = dict(mask)
                output = transform_case(text, mask)
                mismatches = sum(bits[i - 1] != required for i, required in mask.items())
                result = correct_case(text, mask)
                assert case_gate(output, mask) == 1
                assert transform_case(output, mask) == output
                assert (case_gate(text, mask) == 1) == (output == text)
                assert result["mismatches_before"] == mismatches
                assert result["correction_passes"] == int(mismatches > 0)
                assert result["text"] == output
                assert sum(a != b for a, b in zip(text, output)) == mismatches
                assert all(output[i - 1] == text[i - 1]
                           for i in range(1, size + 1) if i not in mask)
                assert mask == original_mask
                count += 1
    assert count == 9330


def test_neutral_and_unmasked_characters_stay_at_the_same_positions():
    text = "A0$b!Z"
    assert transform_case(text, {1: 0, 4: 1}) == "a0$B!Z"
    assert len(transform_case(text, {1: 0, 4: 1})) == len(text)


def test_all_binary_vectors():
    for size in range(1, 9):
        ids = [str(i) for i in range(size)]
        for bits in itertools.product((False, True), repeat=size):
            result = evaluate(ids, [{"id": i, "run_id": "r", "passed": b}
                                    for i, b in zip(ids, bits)], "r")
            assert (result["state"] == "UP") == all(bits)


def test_missing_duplicate_wrong_run_unknown_and_empty_fail():
    good = {"id": "a", "run_id": "r", "passed": True}
    for ids, rows, run in [
        ([], [], "r"), (["a"], [], "r"), (["a"], [good, good], "r"),
        (["a"], [good], "other"), (["a"], [{**good, "passed": None}], "r"),
        (["a"], [{**good, "passed": 1}], "r"), (["a"], [good], ""),
    ]:
        assert evaluate(ids, rows, run)["state"] == "DOWN"
