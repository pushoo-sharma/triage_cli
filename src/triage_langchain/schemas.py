from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AgentTriageResult(BaseModel):
    """Structured output from the LLM for one inbound message."""

    route: str = Field(
        description="Routing decision: typically 'auto_draft' or 'human_review'."
    )
    category: str = Field(
        description="High-level category (e.g. leasing, maintenance, legal, payment)."
    )
    confidence: int = Field(ge=0, le=100, description="Model confidence as a percentage (0-100).")
    reason: str = Field(description="Short justification for the routing decision.")
    review_recommended: bool = Field(
        default=False,
        description="Whether a human should review before any automated reply.",
    )
    review_triggers: list[str] = Field(
        default_factory=list,
        description="Short codes for why review is needed, if any.",
    )

    @field_validator("route")
    @classmethod
    def route_non_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("route must be non-empty")
        return s
