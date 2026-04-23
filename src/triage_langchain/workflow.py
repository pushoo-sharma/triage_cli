from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage

from .schemas import AgentTriageResult

SYSTEM_PROMPT = """You are an assistant for property-management inbound message triage.
Read each message and produce a single structured assessment.
Use route 'human_review' when the message involves legal matters, fair housing, threats, \
money/payment disputes, maintenance emergencies, unknown senders, or anything requiring \
staff judgment. Use 'auto_draft' only for routine leasing inquiries that appear safe to \
acknowledge generically.
Set confidence as an integer percentage from 0 to 100 (not 0-1).
Do not invent property addresses, account balances, or lease facts not stated in the message.
Be conservative: when unsure, choose human_review."""

_DEFAULT_MODEL = "google_genai:gemini-3.1-flash-lite-preview"


def default_model() -> str:
    return os.environ.get("TRIAGE_LANGCHAIN_MODEL", _DEFAULT_MODEL)


def _load_env_from_dotfile() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # CWD (e.g. project root when using scripts/run_langchain.sh)
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


def _message_chunk_to_log_text(message: Any) -> str:
    """Extract printable text from streamed graph messages (typically AI chunks)."""
    if not isinstance(message, BaseMessage):
        return ""
    mtype = getattr(message, "type", None) or type(message).__name__
    if mtype in ("human", "system", "tool"):
        return ""
    content: Any = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[str] = []
        for block in content:
            if isinstance(block, str):
                out.append(block)
            elif isinstance(block, dict) and "text" in block:
                out.append(str(block["text"]))
        return "".join(out)
    if content is None:
        return ""
    return str(content)


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _normalize_usage(candidate: Any) -> dict[str, int] | None:
    """Normalize provider-specific token usage payloads into a stable shape."""
    if not isinstance(candidate, dict):
        return None
    input_tokens = _coerce_int(
        candidate.get("input_tokens", candidate.get("prompt_tokens", 0))
    )
    output_tokens = _coerce_int(
        candidate.get("output_tokens", candidate.get("completion_tokens", 0))
    )
    total_tokens = _coerce_int(candidate.get("total_tokens", input_tokens + output_tokens))
    if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
        return None
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _extract_usage(out: dict[str, Any]) -> dict[str, int] | None:
    """Read token usage from final state and message metadata when available."""
    candidates: list[Any] = []
    candidates.append(out.get("usage_metadata"))
    response_meta = out.get("response_metadata")
    if isinstance(response_meta, dict):
        candidates.append(response_meta.get("token_usage"))
        candidates.append(response_meta.get("usage_metadata"))

    messages = out.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if isinstance(message, BaseMessage):
                usage = getattr(message, "usage_metadata", None)
                if usage is not None:
                    candidates.append(usage)
                rmeta = getattr(message, "response_metadata", None)
                if isinstance(rmeta, dict):
                    candidates.append(rmeta.get("token_usage"))
                    candidates.append(rmeta.get("usage_metadata"))
            elif isinstance(message, dict):
                candidates.append(message.get("usage_metadata"))
                message_meta = message.get("response_metadata")
                if isinstance(message_meta, dict):
                    candidates.append(message_meta.get("token_usage"))
                    candidates.append(message_meta.get("usage_metadata"))

    for candidate in candidates:
        normalized = _normalize_usage(candidate)
        if normalized is not None:
            return normalized
    return None


def _row_from_agent_output(msg_id: Any, out: dict[str, Any]) -> dict[str, Any]:
    """Turn agent invoke/stream final state into a result row for JSON output."""
    usage = _extract_usage(out)
    parsed = out.get("structured_response")
    if parsed is None:
        return {
            "id": msg_id,
            "error": "Agent finished without structured_response",
            "result": None,
            "usage": usage,
        }
    if isinstance(parsed, AgentTriageResult):
        return {"id": msg_id, "error": None, "result": parsed.model_dump(), "usage": usage}
    if hasattr(parsed, "model_dump"):
        return {"id": msg_id, "error": None, "result": parsed.model_dump(), "usage": usage}
    return {
        "id": msg_id,
        "error": f"Unexpected structured_response type: {type(parsed)}",
        "result": None,
        "usage": usage,
    }


def _agent_input(msg: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "user", "content": _format_user_content(msg)},
        ],
    }


def run_message(
    agent: Any,
    msg: dict[str, Any],
    *,
    stream_logs: bool = False,
    log_console: Any | None = None,
) -> dict[str, Any]:
    """Run the agent on one message dict. Returns a row dict for the output JSON file.

    When ``stream_logs`` is True, token-level model output is printed to stderr as it
    arrives (via LangGraph ``stream_mode="messages"``) using Rich if available. The
    final state is taken from the last ``values`` stream event, matching ``invoke``.
    """
    msg_id = msg.get("id")
    if not stream_logs:
        try:
            out = agent.invoke(_agent_input(msg))
        except Exception as e:
            return {"id": msg_id, "error": str(e), "result": None}
        return _row_from_agent_output(msg_id, out)

    try:
        from rich.console import Console
    except ImportError as e:  # pragma: no cover - extra dependency
        raise RuntimeError("Streaming logs require `rich` (install project with [langchain] extra).") from e

    console = log_console or Console(stderr=True, highlight=False)
    inv = _agent_input(msg)
    last_state: dict[str, Any] | None = None
    try:
        for mode, payload in agent.stream(inv, stream_mode=["messages", "values"]):
            if mode == "messages":
                if not isinstance(payload, (tuple, list)) or len(payload) < 2:
                    continue
                message, _meta = payload[0], payload[1]
                text = _message_chunk_to_log_text(message)
                if text:
                    console.print(text, end="")
            elif mode == "values":
                if isinstance(payload, dict):
                    last_state = payload
                elif hasattr(payload, "model_dump") and callable(payload.model_dump):
                    last_state = payload.model_dump()
    except Exception as e:
        return {"id": msg_id, "error": str(e), "result": None}
    console.print()  # newline after streamed tokens
    if last_state is None:
        return {
            "id": msg_id,
            "error": "Agent stream ended without final state",
            "result": None,
        }
    return _row_from_agent_output(msg_id, last_state)
