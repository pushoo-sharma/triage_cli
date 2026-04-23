from __future__ import annotations

import json
import sys
from pathlib import Path

from .io import load_messages
from .workflow import build_triage_agent, run_message


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  python -m triage_langchain <path> [-o out.json]\n"
        "Environment:\n"
        "  GOOGLE_API_KEY or GEMINI_API_KEY  required for Google GenAI\n"
        "  (optional) copy .env.example to .env in the project root\n"
        "  TRIAGE_LANGCHAIN_MODEL  optional (default: google_genai:gemini-2.0-flash)\n",
        file=sys.stderr,
    )


def _parse_args(argv: list[str]) -> tuple[Path | None, Path | None, str | None]:
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
    path, out, err = _parse_args(argv)
    if err:
        print(err, file=sys.stderr)
        _print_usage()
        return 2

    try:
        messages = load_messages(path)
    except OSError as e:
        print(f"Failed to read {path}: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {path}: {e}", file=sys.stderr)
        return 1

    try:
        agent = build_triage_agent()
    except Exception as e:
        print(f"Failed to build agent (check API key and model): {e}", file=sys.stderr)
        return 1

    results: list[dict] = []
    for msg in messages:
        results.append(run_message(agent, msg))

    payload = {"results": results}
    text = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    if out is not None:
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
