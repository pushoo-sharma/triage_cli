from __future__ import annotations

import re

from .extraction import MessageExtraction
from .models import Draft

_RE_WORD = re.compile(r"[a-z0-9']+", re.IGNORECASE)

# Human-review copy: no invented facts, no promises, no fake phone numbers
_HUMAN_REVIEW_FOOTER = (
    "This is an automated holding message. A team member must review the thread before "
    "we can provide policy, financial, legal, or emergency response details. We cannot "
    "verify facts or make commitments from this system."
)

# Causal “why” — what automation cannot do; does not assert tenant-specific facts
_HUMAN_REVIEW_WHY = (
    "A human response is required because these topics need correct account and property "
    "context, policy judgment, and (where relevant) compliance or safety handling. "
    "This system only did keyword triage; it does not know your file, your lease, or what "
    "action is appropriate in your case."
)

_AUTO_FOOTER = (
    "This is an automated acknowledgment and may be incomplete. If you have more details "
    "to add, you can reply to this thread."
)

_TRIGGER_BLURBS: dict[str, str] = {
    "legal": "legal or dispute language may need a qualified person to respond correctly",
    "fair_housing": "fair housing, accommodation, or voucher questions need policy accuracy",
    "maintenance_emergency": "urgent or safety-related maintenance should not be triaged to a generic auto-reply",
    "maintenance": "maintenance or property-condition items need the right trade and follow-up",
    "payment": "payment or money questions need accurate accounting and the right person",
    "invalid_sender": "a technical issue with the sender information",
}


def build_draft(
    route: str,
    category: str,
    review_triggers: list[str],
    subject: str,
    body: str,
    extraction: MessageExtraction,
) -> Draft | None:
    subj = (subject or "").strip() or "Your message"
    if route == "skip" or category == "invalid_input":
        return None  # no outbound template for system noise or invalid senders
    if route == "human_review":
        return _draft_human_review(
            subj, review_triggers, category, extraction
        )
    if route == "auto_draft":
        return _draft_auto(subj, body, extraction)
    return None


def _draft_human_review(
    subject: str,
    review_triggers: list[str],
    category: str,
    extraction: MessageExtraction,
) -> Draft:
    subj_out = _reply_subject(subject)
    parts: list[str] = [
        "Thank you for your message. It was not answered automatically because this system "
        "flagged it in one or more sensitive areas (for example: policy, financial, legal, "
        "or possible maintenance or safety urgency).",
        "",
        _HUMAN_REVIEW_WHY,
        "",
    ]
    seen: set[str] = set()
    lines: list[str] = []
    for code in review_triggers:
        if code in seen:
            continue
        seen.add(code)
        blurb = _TRIGGER_BLURBS.get(code)
        if blurb:
            lines.append(f"- {blurb}.")
    if not lines and category in _TRIGGER_BLURBS:
        lines.append(f"- {_TRIGGER_BLURBS[category]}.")
    if lines:
        parts.append("What triggered that (this is triage, not a decision about you):")
        parts.extend(lines)
        parts.append("")
    parts.append(
        "We are not using this automated note to state facts about your account, property, or "
        "lease—only a staff member can do that after they review the thread."
    )
    parts.append("")
    parts.append(_HUMAN_REVIEW_FOOTER)
    # Only append detected hints that came from parsing (never invent)
    extra: list[str] = []
    if extraction.property_hint:
        extra.append(f"Detected location hint: {extraction.property_hint}")
    if extraction.unit:
        extra.append(f"Detected unit reference: {extraction.unit}")
    if extraction.callback_number:
        extra.append(
            f"Callback number found in the message: {extraction.callback_number}"
        )
    if extraction.requested_action and extraction.urgency in (
        "emergency",
        "urgent",
        "normal",
    ):
        extra.append(f"Requested action (best effort): {extraction.requested_action}")
    if extra:
        parts.append("")
        parts.append("Information extracted for staff (verify before relying on it):")
        parts.extend(f"- {s}" for s in extra)
    return Draft(subject=subj_out, body="\n".join(parts))


def _draft_auto(
    subject: str, body: str, extraction: MessageExtraction
) -> Draft:
    subj_out = _reply_subject(subject)
    body_lower = (body or "").lower()
    topic_line = _optional_topic_line(subject, body_lower)
    main = [
        "Hi, thanks for reaching out.",
    ]
    if topic_line:
        main.append(topic_line)
    else:
        main.append("We received your message.")
    main.append("We will follow up with the next step from our team.")
    main.append("")
    main.append(_AUTO_FOOTER)
    return Draft(subject=subj_out, body="\n".join(main))


def _optional_topic_line(subject: str, body_lower: str) -> str:
    for word in _RE_WORD.findall((subject or "").lower()):
        if len(word) < 4:
            continue
        if word in ("re", "the", "your", "our", "fw", "fwd"):
            continue
        if word in body_lower:
            return f"We noted the topic “{word}” appears in your message."
    return ""


def _reply_subject(subject: str) -> str:
    s = (subject or "").strip() or "Your message"
    if s.lower().startswith("re:"):
        return s
    return f"Re: {s}"
