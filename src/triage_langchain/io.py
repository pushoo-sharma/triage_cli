from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_messages(path: Path) -> list[dict[str, Any]]:
    """Load messages from a JSON array file or JSONL (same behavior as triage.runner)."""
    raw = path.read_text(encoding="utf-8")
    lead = raw.lstrip()
    if lead.startswith("["):
        return json.loads(raw)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]
