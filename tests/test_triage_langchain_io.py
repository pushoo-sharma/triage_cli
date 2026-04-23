from __future__ import annotations

import json
from pathlib import Path

import pytest

from triage_langchain.io import load_messages


def test_load_messages_json_array(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps([{"id": "a", "body": "x"}]),
        encoding="utf-8",
    )
    rows = load_messages(p)
    assert rows == [{"id": "a", "body": "x"}]


def test_load_messages_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "m.jsonl"
    p.write_text('{"id": "1"}\n{"id": "2"}\n', encoding="utf-8")
    rows = load_messages(p)
    assert rows == [{"id": "1"}, {"id": "2"}]
