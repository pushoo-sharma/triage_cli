import json
from pathlib import Path

from triage.evaluate import evaluate_dataset


def test_evaluate_sample_dataset_is_perfect():
    data = json.loads(Path("data/sample_messages.json").read_text(encoding="utf-8"))
    rep = evaluate_dataset(data)
    assert rep.labeled == 10
    assert rep.correct == 10
    assert rep.accuracy == 1.0
    assert rep.all_labeled_match is True
    for row in rep.rows:
        assert row.has_label
        assert row.match is True


def test_evaluate_mismatch_row():
    rep = evaluate_dataset(
        [
            {
                "id": "bad",
                "sender": "a@b.com",
                "subject": "X",
                "body": "y",
                "expected_route": "skip",  # will be auto_draft
            }
        ]
    )
    assert rep.correct == 0
    assert rep.all_labeled_match is False
    assert rep.accuracy == 0.0
