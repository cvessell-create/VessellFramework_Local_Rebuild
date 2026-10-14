import itertools

from vessell.formula import evaluate


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
