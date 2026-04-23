import json
from pathlib import Path

from triage.extraction import extract_message


def test_extracts_phone_and_unit():
    m = {
        "id": "t1",
        "sender": "a@b.com",
        "subject": "Unit 4B",
        "body": "Call me at 415-555-1212 about the leak.",
    }
    ext = extract_message(m, f"{m['subject']}\n{m['body']}")
    assert ext.callback_number == "(415) 555-1212"
    assert ext.unit == "4B"


def test_urgency_emergency_from_today_and_leak():
    m = {
        "sender": "t@t.com",
        "subject": "Leak",
        "body": "There is a leak and I need someone today.",
    }
    text = f"{m['subject']}\n{m['body']}"
    ext = extract_message(m, text)
    assert ext.urgency == "emergency"


def test_property_hint_from_street_phrase():
    m = {
        "sender": "p@p.com",
        "subject": "Tour",
        "body": "Is the 2 bedroom apartment on Maple Street still available?",
    }
    ext = extract_message(m, f"{m['subject']}\n{m['body']}")
    assert ext.property_hint is not None
    assert "maple" in ext.property_hint.lower()


def test_sample_msg_001_extraction_has_maple():
    data = json.loads(Path("data/sample_messages.json").read_text(encoding="utf-8"))
    row = next(x for x in data if x["id"] == "msg_001")
    text = f"{row['subject']}\n{row['body']}"
    ext = extract_message(row, text)
    assert ext.property_hint is not None
    assert "maple" in (ext.property_hint or "").lower()
