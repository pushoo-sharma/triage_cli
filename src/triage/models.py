from __future__ import annotations

from dataclasses import dataclass, field

from .extraction import MessageExtraction


@dataclass
class Draft:
    subject: str
    body: str


@dataclass
class TriageResult:
    route: str
    category: str
    confidence: float
    urgency_score: int
    priority_bucket: str
    reason: str
    draft: Draft | None = None
    warnings: list[str] = field(default_factory=list)
    review_triggers: list[str] = field(default_factory=list)
    extraction: MessageExtraction = field(default_factory=MessageExtraction)
