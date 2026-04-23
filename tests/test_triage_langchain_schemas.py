from __future__ import annotations

import pytest

pytest.importorskip("pydantic", reason="triage_langchain schemas need pydantic")

from triage_langchain.schemas import AgentTriageResult  # noqa: E402


def test_agent_triage_result_round_trip() -> None:
    r = AgentTriageResult(
        route="human_review",
        category="maintenance",
        confidence=0.7,
        reason="Possible emergency",
        review_recommended=True,
        review_triggers=["maintenance"],
    )
    d = r.model_dump()
    r2 = AgentTriageResult.model_validate(d)
    assert r2 == r


def test_agent_triage_result_rejects_empty_route() -> None:
    with pytest.raises(ValueError):
        AgentTriageResult(
            route="  ",
            category="x",
            confidence=0.5,
            reason="y",
        )
