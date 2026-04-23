from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain.agents import create_agent

from .schemas import AgentTriageResult

SYSTEM_PROMPT = """You are an assistant for property-management inbound message triage.
Read each message and produce a single structured assessment.
Use route 'human_review' when the message involves legal matters, fair housing, threats, \
money/payment disputes, maintenance emergencies, unknown senders, or anything requiring \
staff judgment. Use 'auto_draft' only for routine leasing inquiries that appear safe to \
acknowledge generically.
Do not invent property addresses, account balances, or lease facts not stated in the message.
Be conservative: when unsure, choose human_review."""

_DEFAULT_MODEL = "google_genai:gemini-2.0-flash"


def default_model() -> str:
    return os.environ.get("TRIAGE_LANGCHAIN_MODEL", _DEFAULT_MODEL)


def _load_env_from_dotfile() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # CWD (e.g. project root when using run_langchain.sh)
    load_dotenv(override=False)
    # Also: `src/triage_langchain/workflow.py` -> repo root / .env
    project_root = Path(__file__).resolve().parents[2]
    project_env = project_root / ".env"
    if project_env.is_file():
        load_dotenv(project_env, override=False)


def build_triage_agent(
    model: str | None = None,
) -> Any:
    """Build a LangChain agent that returns `AgentTriageResult` in `structured_response`."""
    _load_env_from_dotfile()
    m = model or default_model()
    return create_agent(
        model=m,
        tools=[],
        system_prompt=SYSTEM_PROMPT,
        response_format=AgentTriageResult,
    )


def _format_user_content(msg: dict[str, Any]) -> str:
    parts: list[str] = []
    if mid := msg.get("id"):
        parts.append(f"message_id: {mid}")
    if s := msg.get("sender"):
        parts.append(f"sender: {s}")
    if s := msg.get("subject"):
        parts.append(f"subject: {s}")
    if b := msg.get("body"):
        parts.append(f"body:\n{b}")
    if not parts:
        return json.dumps(msg, ensure_ascii=True)
    return "\n".join(parts)


def run_message(agent: Any, msg: dict[str, Any]) -> dict[str, Any]:
    """Run the agent on one message dict. Returns a row dict for the output JSON file."""
    msg_id = msg.get("id")
    try:
        out = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": _format_user_content(msg)},
                ],
            }
        )
        parsed = out.get("structured_response")
        if parsed is None:
            return {
                "id": msg_id,
                "error": "Agent finished without structured_response",
                "result": None,
            }
        if isinstance(parsed, AgentTriageResult):
            return {"id": msg_id, "error": None, "result": parsed.model_dump()}
        if hasattr(parsed, "model_dump"):
            return {"id": msg_id, "error": None, "result": parsed.model_dump()}
        return {
            "id": msg_id,
            "error": f"Unexpected structured_response type: {type(parsed)}",
            "result": None,
        }
    except Exception as e:
        return {"id": msg_id, "error": str(e), "result": None}
