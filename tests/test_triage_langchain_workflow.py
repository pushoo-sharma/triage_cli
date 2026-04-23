from __future__ import annotations

import pytest

pytest.importorskip("langchain", reason="workflow tests need langchain installed")

from unittest.mock import MagicMock  # noqa: E402

from triage_langchain.schemas import AgentTriageResult  # noqa: E402
from triage_langchain import workflow  # noqa: E402


def test_run_message_success() -> None:
    agent = MagicMock()
    agent.invoke.return_value = {
        "structured_response": AgentTriageResult(
            route="auto_draft",
            category="leasing",
            confidence=0.4,
            reason="Routine inquiry",
            review_recommended=False,
        )
    }
    row = workflow.run_message(
        agent,
        {"id": "msg_001", "subject": "Hi", "body": "Tour?"},
    )
    assert row["id"] == "msg_001"
    assert row["error"] is None
    assert row["result"] is not None
    assert row["result"]["route"] == "auto_draft"


def test_run_message_error_from_invoke() -> None:
    agent = MagicMock()
    agent.invoke.side_effect = RuntimeError("api down")
    row = workflow.run_message(agent, {"id": "x", "body": "y"})
    assert row["id"] == "x"
    assert row["error"] == "api down"
    assert row["result"] is None
