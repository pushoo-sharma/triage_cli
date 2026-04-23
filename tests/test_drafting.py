from triage.core import triage_message
from triage.drafting import build_draft
from triage.extraction import MessageExtraction


def test_auto_draft_does_not_fabricate_address():
    r = triage_message(
        {
            "sender": "x@y.com",
            "subject": "Parking",
            "body": "Is parking included?",
        }
    )
    assert r.draft is not None
    assert "123 Main" not in (r.draft.body or "")
    assert "This is an automated acknowledgment" in (r.draft.body or "")


def test_human_review_draft_lists_flags_and_disclaimer():
    ex = MessageExtraction(
        property_hint=None,
        unit=None,
        urgency="emergency",
        callback_number=None,
        requested_action="maintenance_request",
    )
    d = build_draft(
        "human_review",
        "legal",
        ["legal"],
        "Problem",
        "My attorney will sue.",
        ex,
    )
    assert d is not None
    assert "human response" in d.body.lower()
    assert "legal" in d.body.lower() or "dispute" in d.body.lower()
    assert "automated holding" in d.body.lower()
    assert "We are not using this automated note to state facts" in d.body
    assert "A human response is required because" in d.body


def test_invalid_input_gets_no_draft():
    r = triage_message(
        {
            "sender": "",
            "subject": "Q",
            "body": "Hi",
        }
    )
    assert r.draft is None
