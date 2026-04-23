from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from .core import triage_message
from .evaluate import evaluate_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_messages(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    lead = raw.lstrip()
    if lead.startswith("["):
        return json.loads(raw)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  python -m triage.runner <path> [-o out.json]   # triage: JSONL to stdout, or -o to write one JSON file\n"
        "  python -m triage.runner eval <path>         # report accuracy vs expected_route",
        file=sys.stderr,
    )


def _parse_triage_path_and_output(argv: list[str]) -> tuple[Path | None, Path | None, str | None]:
    """Parse a single message file path and optional -o / --output. Return (path, out, error)."""
    out: Path | None = None
    pos: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] in ("-o", "--output"):
            if i + 1 >= len(argv):
                return None, None, "Missing path after -o / --output"
            out = Path(argv[i + 1])
            i += 2
            continue
        if argv[i].startswith("-"):
            return None, None, f"Unknown option: {argv[i]!r}"
        pos.append(argv[i])
        i += 1
    if len(pos) != 1:
        return None, None, "Expected exactly one message file path"
    return Path(pos[0]), out, None


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        _print_usage()
        return 2

    if argv[0] == "eval":
        if len(argv) < 2:
            _print_usage()
            return 2
        path = Path(argv[1])
        messages = load_messages(path)
        report = evaluate_dataset(messages)
        for row in report.rows:
            print(
                json.dumps(
                    {
                        "id": row.id,
                        "expected": row.expected,
                        "actual": row.actual,
                        "match": row.match,
                        "category": row.category,
                        "confidence": row.confidence,
                        "urgency_score": row.urgency_score,
                        "priority_bucket": row.priority_bucket,
                        "has_label": row.has_label,
                    },
                    sort_keys=True,
                )
            )
        print(
            json.dumps(
                {
                    "accuracy": report.accuracy,
                    "correct": report.correct,
                    "labeled": report.labeled,
                    "total_messages": report.total_messages,
                    "all_labeled_match": report.all_labeled_match,
                },
                sort_keys=True,
            )
        )
        return 0 if report.all_labeled_match else 1

    path, out_path, parse_err = _parse_triage_path_and_output(argv)
    if parse_err is not None:
        print(f"Error: {parse_err}", file=sys.stderr)
        _print_usage()
        return 2

    messages = load_messages(path)

    results: list[dict[str, Any]] = []
    total = 0
    correct = 0
    labeled = 0
    for message in messages:
        result = triage_message(message)
        total += 1
        expected = message.get("expected_route")
        if expected is not None:
            labeled += 1
            correct += int(expected == result.route)
        row = {
            "id": message.get("id"),
            "expected": expected,
            "route": result.route,
            "category": result.category,
            "confidence": result.confidence,
            "urgency_score": result.urgency_score,
            "priority_bucket": result.priority_bucket,
            "reason": result.reason,
            "human_review_reason": (
                result.reason if result.route == "human_review" else None
            ),
            "review_triggers": result.review_triggers,
            "warnings": result.warnings,
        }
        results.append(row)
        if out_path is None:
            print(json.dumps(row, sort_keys=True))

    if total:
        acc = (correct / labeled) if labeled else 0.0
        summary: dict[str, Any] = {
            "accuracy": acc,
            "correct": correct,
            "total": total,
            "labeled": labeled,
        }
        if out_path is None:
            print(json.dumps(summary, sort_keys=True))
    else:
        summary = None

    if out_path is not None:
        payload: dict[str, Any] = {"results": results}
        if total:
            assert summary is not None
            payload["summary"] = summary
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
