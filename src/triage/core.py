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

URGENCY_TIME_TERMS = (
    "right now",
    "asap",
    "immediately",
    "urgent",
    "today",
    "tonight",
    "as soon as possible",
)

URGENCY_SEVERITY_TERMS = (
    "flood",
    "flooding",
    "fire",
    "smoke",
    "gas leak",
    "no heat",
    "no hot water",
    "no power",
    "sparks",
)

URGENCY_VULNERABILITY_TERMS = (
    "elderly",
    "senior",
    "child",
    "children",
    "disabled",
    "disability",
    "wheelchair",
    "medical condition",
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
        urgency_score, priority_bucket = _compute_urgency(
            text=text,
            category="invalid_input",
            legal_hits=0,
            fair_hits=0,
            money_hits=0,
            crisis=False,
            regular=False,
            maint_urgent=False,
            extraction_urgency=extraction.urgency,
        )
        r = TriageResult(
            route="human_review",
            category="invalid_input",
            confidence=0.96,
            urgency_score=urgency_score,
            priority_bucket=priority_bucket,
            reason="Sender is missing or invalid.",
            review_triggers=["invalid_sender"],
            warnings=["invalid_sender"],
            extraction=extraction,
        )
        r.draft = None
        return r

    if any(s in subject.lower() for s in SYSTEM_SUBJECTS):
        urgency_score, priority_bucket = _compute_urgency(
            text=text,
            category="system",
            legal_hits=0,
            fair_hits=0,
            money_hits=0,
            crisis=False,
            regular=False,
            maint_urgent=False,
            extraction_urgency=extraction.urgency,
        )
        return TriageResult(
            route="skip",
            category="system",
            confidence=round(
                _conf_from_hits(1, 0.72),
                2,
            ),
            urgency_score=urgency_score,
            priority_bucket=priority_bucket,
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

    urgency_score, priority_bucket = _compute_urgency(
        text=text,
        category=category,
        legal_hits=legal_hits,
        fair_hits=fair_hits,
        money_hits=money_hits,
        crisis=crisis,
        regular=regular,
        maint_urgent=maint_urgent,
        extraction_urgency=extraction.urgency,
    )
    confidence = round(min(0.99, _conf_from_hits(n_hits, base_conf)), 2)
    r = TriageResult(
        route=_route_for_category(category),
        category=category,
        confidence=confidence,
        urgency_score=urgency_score,
        priority_bucket=priority_bucket,
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


def _compute_urgency(
    *,
    text: str,
    category: str,
    legal_hits: int,
    fair_hits: int,
    money_hits: int,
    crisis: bool,
    regular: bool,
    maint_urgent: bool,
    extraction_urgency: str,
) -> tuple[int, str]:
    if category == "system":
        return 0, "low"

    score = 5
    if category == "invalid_input":
        score += 10

    if crisis:
        score += 45
    if regular:
        score += 20
    if maint_urgent:
        score += 20

    score += min(20, legal_hits * 10)
    score += min(15, fair_hits * 8)
    score += min(10, money_hits * 4)

    time_hits = _count_hits(text, URGENCY_TIME_TERMS)
    severity_hits = _count_hits(text, URGENCY_SEVERITY_TERMS)
    vulnerability_hits = _count_hits(text, URGENCY_VULNERABILITY_TERMS)

    score += min(18, time_hits * 6)
    score += min(35, severity_hits * 12)
    score += min(20, vulnerability_hits * 10)

    urgency_map = {
        "emergency": 20,
        "urgent": 12,
        "normal": 4,
        "unknown": 0,
    }
    score += urgency_map.get(extraction_urgency, 0)

    bounded = max(0, min(100, score))
    return bounded, _priority_bucket_for_score(bounded)


def _priority_bucket_for_score(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


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
