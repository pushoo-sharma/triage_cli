from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# US-style phone: optional +1, separators optional
_PHONE_PATTERNS = [
    re.compile(
        r"(?:\+?1[-.\s]?)?(?:\((\d{3})\)[-.\s]?|(\d{3})[-.\s])(\d{3})[-.\s]?(\d{4})\b"
    ),
    re.compile(r"\b(\d{3})[-.\s](\d{3})[-.\s](\d{4})\b"),
    re.compile(r"\b(\d{3})\.(\d{3})\.(\d{4})\b"),
]

_UNIT_PATTERNS = [
    re.compile(
        r"\b(?:apartment|apt|unit|suite|ste|#)\s*[#.]?\s*([a-z0-9-]+)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\#(\d{1,4}[a-z]?)\b", re.IGNORECASE),
]

# Street / property line hints: "on Maple Street", "at 100 Main St"
_STREET_LINE = re.compile(
    r"\b(?:on|at)\s+([0-9]?\s*[A-Za-z][A-Za-z\s'’-]+(?:st\.?|street|ave\.?|avenue|"
    r"rd\.?|road|blvd\.?|boulevard|dr\.?|lane|ln\.?|way|ct\.?|court|plaza))\b",
    re.IGNORECASE,
)

# Named place after at/on: short phrase, capitalized words
_NAMED_PLACE = re.compile(
    r"\b(?:at|on|near)\s+((?:[A-Z][a-z]+(?:\s+|$)){1,4}(?:[A-Z][a-z]+)?)\b"
)


def _word_boundary_contains(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?i)\b{re.escape(phrase)}\b", text))


@dataclass
class MessageExtraction:
    property_hint: str | None = None
    unit: str | None = None
    urgency: str = "unknown"  # "emergency" | "urgent" | "normal" | "unknown"
    callback_number: str | None = None
    requested_action: str | None = None


def extract_message(message: dict[str, Any], combined_text: str) -> MessageExtraction:
    """Heuristic extraction; never invents a full address."""
    text_lower = combined_text.lower()
    full_text = combined_text
    subject = str(message.get("subject") or "")

    prop = _extract_property(full_text, subject, text_lower)
    unit = _extract_unit(combined_text)
    urgency = _classify_urgency(text_lower)
    phone = _extract_phone(combined_text)
    action = _extract_action(text_lower)

    return MessageExtraction(
        property_hint=prop,
        unit=unit,
        urgency=urgency,
        callback_number=phone,
        requested_action=action,
    )


def _classify_urgency(text_lower: str) -> str:
    for phrase in (
        "emergency",
        "asap",
        "immediately",
        "right away",
        "right now",
        "tonight",
        "today",
        "as soon as",
        "very cold",
        "not safe",
        "no heat",
        "no hot water",
    ):
        if phrase in text_lower:
            return "emergency"
    for phrase in ("flood", "sparks", "fire", "gas leak", "smoke"):
        if _word_boundary_contains(text_lower, phrase) or phrase in text_lower:
            return "emergency"
    if "urgent" in text_lower or "please come" in text_lower:
        return "urgent"
    if re.search(
        r"\b(issue|problem|leak|repair|fix|mold|clog|request)\b", text_lower
    ):
        return "normal"
    return "unknown"


def _extract_property(
    full_text: str, subject: str, text_lower: str
) -> str | None:
    m = _STREET_LINE.search(full_text)
    if m:
        return m.group(1).strip()[:200]
    m2 = _NAMED_PLACE.search(full_text)
    if m2:
        return m2.group(1).strip()[:200]
    m3 = re.search(
        r"(?:2\s*bedroom\s+apartment|apartment|unit|place)\s+on\s+"
        r"([A-Z][A-Za-z\s'’-]+?)(?=\s+still|\s+available|[.,]|$)",
        full_text,
        re.IGNORECASE,
    )
    if m3:
        return f"on {m3.group(1).strip()}"
    return None


def _extract_unit(text: str) -> str | None:
    for pat in _UNIT_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1)[:32]
    return None


def _extract_phone(text: str) -> str | None:
    for pat in _PHONE_PATTERNS:
        m = pat.search(text)
        if m:
            digits = re.sub(r"\D", "", m.group(0))
            if len(digits) >= 10:
                d = digits[-10:]
                return f"({d[0:3]}) {d[3:6]}-{d[6:10]}"
    return None


def _extract_action(text_lower: str) -> str | None:
    m = re.search(
        r"\bcan someone\s+(.+?)(?:[.?!]|$)", text_lower, re.IGNORECASE
    )
    if m:
        frag = m.group(1)[:100].strip()
        if len(frag) > 2:
            return f"request_service: {frag[:120]}"
    m2 = re.search(
        r"\bplease (?:send|have|get)\s+(.+?)(?:[.?!]|$)", text_lower, re.IGNORECASE
    )
    if m2:
        return f"request: {m2.group(1)[:120]}"
    if "tour" in text_lower and (
        "tour" in text_lower[:120] or "tour" in text_lower
    ):
        if "tour" in text_lower:
            return "schedule_tour"
    if "application" in text_lower and "submitted" in text_lower:
        return "application_status"
    if re.search(
        r"\b(leak|mold|heat|repair|fix|request)\b", text_lower
    ) and re.search(
        r"\b(come|fix|send|plumber|technician|today)\b", text_lower
    ):
        return "maintenance_request"
    return None
