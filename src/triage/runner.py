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
        "  python -m triage.runner <path>              # run triage, print JSON per row\n"
        "  python -m triage.runner eval <path>         # report accuracy vs expected_route",
        file=sys.stderr,
    )


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

    path = Path(argv[0])
    messages = load_messages(path)

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
        print(
            json.dumps(
                {
                    "id": message.get("id"),
                    "expected": expected,
                    "route": result.route,
                    "category": result.category,
                    "confidence": result.confidence,
                    "review_triggers": result.review_triggers,
                    "warnings": result.warnings,
                },
                sort_keys=True,
            )
        )

    if total:
        acc = (correct / labeled) if labeled else 0.0
        print(
            json.dumps(
                {
                    "accuracy": acc,
                    "correct": correct,
                    "total": total,
                    "labeled": labeled,
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
