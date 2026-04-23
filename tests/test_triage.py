import json
from pathlib import Path

from triage.core import triage_message


def test_general_leasing_message_gets_draft():
    result = triage_message(
        {
            "sender": "prospect@example.com",
            "subject": "Parking",
            "body": "Is parking included with the apartment?",
        }
    )

    assert result.route == "auto_draft"
    assert result.draft is not None
    assert result.draft.subject == "Re: Parking"
    assert result.review_triggers == []


def test_legal_threat_requires_human_review():
    result = triage_message(
        {
            "sender": "tenant@example.com",
            "subject": "Problem",
            "body": "My attorney said we should sue if this is not fixed.",
        }
    )

    assert result.route == "human_review"
    assert result.category == "legal"
    assert "legal" in result.review_triggers
    assert "legal_review_required" in result.warnings


def test_sensitive_housing_topic_requires_human_review():
    result = triage_message(
        {
            "sender": "prospect@example.com",
            "subject": "Voucher",
            "body": "Do you accept Section 8 vouchers?",
        }
    )

    assert result.route == "human_review"
    assert result.category == "fair_housing"


def test_system_summary_is_skipped():
    result = triage_message(
        {
            "sender": "noreply@example.com",
            "subject": "Weekly activity summary",
            "body": "Generated report.",
        }
    )

    assert result.route == "skip"
    assert result.draft is None


def test_invalid_sender_fails_closed():
    result = triage_message(
        {
            "sender": "",
            "subject": "Question",
            "body": "Can I apply?",
        }
    )

    assert result.route == "human_review"
    assert result.category == "invalid_input"
    assert result.draft is None


def test_legal_wins_over_maintenance_when_both_present():
    result = triage_message(
        {
            "sender": "t@t.com",
            "subject": "Mold",
            "body": "There is mold and my attorney says I will sue if not fixed.",
        }
    )
    assert result.category == "legal"
    assert result.route == "human_review"


def test_maintenance_non_emergency_without_urgency():
    result = triage_message(
        {
            "sender": "t@t.com",
            "subject": "Question",
            "body": "The hallway light has a minor electrical issue when it rains.",
        }
    )
    assert result.route == "human_review"
    assert result.category == "maintenance"
    assert "maintenance" in result.review_triggers
    assert "maintenance_emergency" not in result.review_triggers


def test_maintenance_emergency_no_heat():
    result = triage_message(
        {
            "sender": "t@t.com",
            "subject": "Heat",
            "body": "The heat has been off since last night and it is very cold.",
        }
    )
    assert result.category == "maintenance_emergency"
    assert "maintenance_emergency" in result.warnings


def test_sample_json_routes_match_expected():
    data = json.loads(Path("data/sample_messages.json").read_text(encoding="utf-8"))
    for row in data:
        r = triage_message(row)
        assert r.route == row["expected_route"], (row["id"], r.route, row["expected_route"])
