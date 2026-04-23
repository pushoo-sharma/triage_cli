from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .core import triage_message


@dataclass
class EvalRow:
    id: str | None
    expected: str | None
    actual: str
    match: bool | None
    category: str
    confidence: float
    has_label: bool


@dataclass
class EvalReport:
    total_messages: int
    labeled: int
    correct: int
    accuracy: float
    rows: list[EvalRow]
    all_labeled_match: bool


def evaluate_dataset(messages: list[dict[str, Any]]) -> EvalReport:
    """Compare ``expected_route`` in each message to the triage route, when present."""
    rows: list[EvalRow] = []
    correct = 0
    labeled = 0

    for m in messages:
        exp = m.get("expected_route")
        r = triage_message(m)
        has_label = exp is not None
        mid = m.get("id")
        eid: str | None = None if mid is None else str(mid)
        ex_s: str | None
        if has_label:
            ex_s = str(exp) if exp is not None else None
        else:
            ex_s = None
        is_match: bool | None
        if has_label:
            labeled += 1
            is_match = ex_s == r.route
            if is_match:
                correct += 1
        else:
            is_match = None
        rows.append(
            EvalRow(
                id=eid,
                expected=ex_s,
                actual=r.route,
                match=is_match,
                category=r.category,
                confidence=r.confidence,
                has_label=has_label,
            )
        )

    acc = (correct / labeled) if labeled else 0.0
    all_ok = (correct == labeled) if labeled else True

    return EvalReport(
        total_messages=len(rows),
        labeled=labeled,
        correct=correct,
        accuracy=acc,
        rows=rows,
        all_labeled_match=all_ok,
    )
