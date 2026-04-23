from __future__ import annotations

import logging
import re
from typing import Any

from .extraction import extract_message
from .models import Draft, TriageResult

logger = logging.getLogger(__name__)

SYSTEM_SUBJECTS = (
    "weekly activity summary",
    "daily report",
    "system generated",
)

LEGAL_TERMS = (
    "attorney",
    "lawsuit",
    "sue",
    "court",
    "legal action",
    "litigation",
    "cease and desist",
    "discrimination",
    "lawyer",
)

FAIR_HOUSING_TERMS = (
    "section 8",
    "voucher",
    "housing voucher",
    "emotional support animal",
    "service animal",
    "reasonable accommodation",
    "protected class",
    "fair housing",
    "hud",
)

CRISIS_MAINTENANCE_TERMS = (
    "no heat",
    "no hot water",
    "heat has been off",
    "heat is off",
    "without heat",
    "flood",
    "flooding",
    "sparks",
    "fire",
    "smoke",
    "gas leak",
    "carbon monoxide",
    "electrocution",
)

REGULAR_MAINTENANCE_TERMS = (
    "leak",
    "mold",
    "electrical",
    "burst",
    "clog",
    "broken",
    "backed up",
    "overflow",
    "wiring",
    "pilot light",
    "hazardous",
    "hazard",
    "safety",
)

MAINT_URGENCY_MARKERS = (
    "today",
    "tonight",
    "immediately",
    "asap",
    "right away",
    "as soon as",
    "as soon as possible",
    "emergency",
    "very cold",
    "right now",
)

MONEY_TERMS = (
    "invoice",
    "payment",
    "refund",
    "deposit",
    "wire",
    "bank",
    "rent",
    "balance",
    "balance due",
    "late fee",
    "past due",
    "ach",
    "money order",
    "outstanding",
    "reimbursement",
    "billed",
)


def triage_message(message: dict[str, Any]) -> TriageResult:
    """Classify one inbound message and optionally create a safe draft."""
    subject = str(message.get("subject") or "")
    body = str(message.get("body") or "")
    sender = str(message.get("sender") or "")
    combined = f"{subject}\n{body}"
    text = combined.lower()

    extraction = extract_message(message, combined)

    if not sender or "@" not in sender:
        logger.warning("invalid_sender", extra={"message_id": message.get("id")})
        r = TriageResult(
            route="human_review",
            category="invalid_input",
            confidence=0.96,
            reason="Sender is missing or invalid.",
            review_triggers=["invalid_sender"],
            warnings=["invalid_sender"],
            extraction=extraction,
        )
        r.draft = None
        return r

    if any(s in subject.lower() for s in SYSTEM_SUBJECTS):
        return TriageResult(
            route="skip",
            category="system",
            confidence=round(
                _conf_from_hits(1, 0.72),
                2,
            ),
            reason="System notification does not need a response.",
            review_triggers=[],
            warnings=[],
            extraction=extraction,
        )

    legal_hits = _count_hits(text, LEGAL_TERMS)
    fair_hits = _count_hits(text, FAIR_HOUSING_TERMS)
    money_hits = _count_hits(text, MONEY_TERMS)
    crisis = _has_any_phrase(text, CRISIS_MAINTENANCE_TERMS)
    regular = _has_any_phrase(text, REGULAR_MAINTENANCE_TERMS)
    maint_urgent = _has_any_phrase(text, MAINT_URGENCY_MARKERS)
    maint_emerg = bool(crisis or (regular and maint_urgent))
    maint_any = bool(crisis or regular)

    category, reason, rtrig, n_hits, base_conf = _resolve_category(
        legal_hits, fair_hits, money_hits, maint_emerg, maint_any
    )

    confidence = round(min(0.99, _conf_from_hits(n_hits, base_conf)), 2)
    r = TriageResult(
        route=_route_for_category(category),
        category=category,
        confidence=confidence,
        reason=reason,
        review_triggers=rtrig,
        warnings=_warnings_from_triggers(rtrig),
        extraction=extraction,
    )
    r.draft = _build_draft_safe(
        r.route, r.category, r.review_triggers, subject, body, extraction
    )
    return r


def _resolve_category(
    legal_hits: int,
    fair_hits: int,
    money_hits: int,
    maint_emerg: bool,
    maint_any: bool,
) -> tuple[str, str, list[str], int, float]:
    if legal_hits:
        n = min(4, max(1, legal_hits))
        return (
            "legal",
            f"Legal-related language detected ({legal_hits} cue(s)).",
            ["legal"],
            n,
            0.52,
        )
    if fair_hits:
        n = min(4, max(1, fair_hits))
        return (
            "fair_housing",
            f"Sensitive housing, voucher, or accommodation topic ({fair_hits} cue(s)).",
            ["fair_housing"],
            n,
            0.5,
        )
    if maint_emerg:
        return (
            "maintenance_emergency",
            "Urgent or crisis-level maintenance or safety language.",
            ["maintenance_emergency"],
            2,
            0.55,
        )
    if maint_any:
        n = 2
        return (
            "maintenance",
            "Maintenance or property-condition language (non-emergency routing).",
            ["maintenance"],
            n,
            0.45,
        )
    if money_hits:
        n = min(4, max(1, money_hits))
        return (
            "money",
            f"Payment, invoice, or money-related language ({money_hits} cue(s)).",
            ["payment"],
            n,
            0.48,
        )
    return (
        "leasing_general",
        "General leasing message; no high-risk cues matched.",
        [],
        1,
        0.38,
    )


def _route_for_category(category: str) -> str:
    if category in (
        "legal",
        "fair_housing",
        "maintenance_emergency",
        "maintenance",
        "money",
    ):
        return "human_review"
    if category == "system":
        return "skip"
    if category == "invalid_input":
        return "human_review"
    if category == "leasing_general":
        return "auto_draft"
    return "human_review"


def _has_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    for t in phrases:
        if " " in t or len(t) > 10:
            if t.lower() in text:
                return True
        else:
            if re.search(rf"(?i)\b{re.escape(t)}\b", text):
                return True
    return False


def _count_hits(text: str, terms: tuple[str, ...]) -> int:
    n = 0
    for t in terms:
        if " " in t or len(t) > 10:
            if t.lower() in text:
                n += 1
        else:
            if re.search(rf"(?i)\b{re.escape(t)}\b", text):
                n += 1
    return n


def _conf_from_hits(effective_hits: int, base: float) -> float:
    bump = 0.1 * min(effective_hits, 5) + 0.04 * max(0, effective_hits - 5)
    return min(0.99, base + bump)


def _warnings_from_triggers(rtrig: list[str]) -> list[str]:
    w: list[str] = []
    m = {
        "legal": "legal_review_required",
        "fair_housing": "policy_review_required",
        "maintenance_emergency": "maintenance_emergency",
        "maintenance": "maintenance_review_required",
        "payment": "payment_review_required",
        "invalid_sender": "invalid_sender",
    }
    for t in rtrig:
        if t in m:
            w.append(m[t])
    return w


def _build_draft_safe(
    route: str,
    category: str,
    review_triggers: list[str],
    subject: str,
    body: str,
    extraction: Any,
) -> Draft | None:
    from .drafting import build_draft

    return build_draft(
        route, category, review_triggers, subject, body, extraction
    )
