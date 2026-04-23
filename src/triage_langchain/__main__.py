from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .io import load_messages
from .workflow import build_triage_agent, default_model, run_message


def _print_usage() -> None:
    model_name = default_model()
    print(
        "Usage:\n"
        "  python -m triage_langchain <path> [-o out.json] [-q]\n"
        "Options:\n"
        "  -o, --output PATH  write JSON to file (default: stdout)\n"
        "  -q, --quiet        no streaming logs on stderr (model still runs the same)\n"
        "Environment:\n"
        "  GOOGLE_API_KEY or GEMINI_API_KEY  required for Google GenAI\n"
        "  (optional) copy .env.example to .env in the project root\n"
        f"  TRIAGE_LANGCHAIN_MODEL  optional (default: {model_name})\n",
        file=sys.stderr,
    )


def _parse_args(
    argv: list[str],
) -> tuple[Path | None, Path | None, bool, str | None]:
    out: Path | None = None
    quiet = False
    pos: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] in ("-o", "--output"):
            if i + 1 >= len(argv):
                return None, None, False, "Missing path after -o / --output"
            out = Path(argv[i + 1])
            i += 2
            continue
        if argv[i] in ("-q", "--quiet"):
            quiet = True
            i += 1
            continue
        if argv[i].startswith("-"):
            return None, None, False, f"Unknown option: {argv[i]!r}"
        pos.append(argv[i])
        i += 1
    if len(pos) != 1:
        return None, None, False, "Expected exactly one message file path"
    return Path(pos[0]), out, quiet, None


def _usage_from_row(row: dict[str, Any]) -> dict[str, int] | None:
    usage = row.get("usage")
    if not isinstance(usage, dict):
        return None
    keys = ("input_tokens", "output_tokens", "total_tokens")
    if not all(isinstance(usage.get(k), int) for k in keys):
        return None
    return {k: int(usage[k]) for k in keys}


def _sum_session_usage(rows: list[dict[str, Any]]) -> dict[str, int] | None:
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    messages_with_usage = 0
    for row in rows:
        usage = _usage_from_row(row)
        if usage is None:
            continue
        messages_with_usage += 1
        input_tokens += usage["input_tokens"]
        output_tokens += usage["output_tokens"]
        total_tokens += usage["total_tokens"]
    if messages_with_usage == 0:
        return None
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "messages_with_usage": messages_with_usage,
    }


def _render_logo(log: Any, model_name: str, message_count: int) -> None:
    logo = None
    try:
        from pyfiglet import Figlet

        logo = Figlet(font="slant").renderText("TRIAGE")
    except Exception:
        logo = (
            " _______ ____  _____    _    ____ _____\n"
            "|_   _|  _ \\|_   _|  / \\  / ___| ____|\n"
            "  | | | |_) | | |   / _ \\| |  _|  _|\n"
            "  | | |  _ <  | |  / ___ \\ |_| | |___\n"
            "  |_| |_| \\_\\ |_| /_/   \\_\\____|_____|\n"
        )
    log.print(f"[bold cyan]{logo}[/bold cyan]", justify="center")
    log.print(
        f"[dim]AI Message Triage[/dim]  [white]|[/white]  [dim]Model:[/dim] [cyan]{model_name}[/cyan]  "
        f"[white]|[/white]  [dim]Messages:[/dim] [cyan]{message_count}[/cyan]\n",
        justify="center",
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        _print_usage()
        return 2
    path, out, quiet, err = _parse_args(argv)
    if err:
        print(err, file=sys.stderr)
        _print_usage()
        return 2

    log: Any = None
    rule_factory: Any = None
    try:
        from rich.console import Console
        from rich.rule import Rule
        from rich.traceback import install as rich_traceback_install

        rich_traceback_install(show_locals=False)
        log = Console(stderr=True, highlight=False)
        rule_factory = Rule
    except ImportError:
        if not quiet:
            print(
                "Install `rich` for live token logs (e.g. `pip install rich` or project extra `[langchain]`). "
                "Running without stream.",
                file=sys.stderr,
            )

    use_stream = not quiet and log is not None

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

    if use_stream and log is not None:
        _render_logo(log, default_model(), len(messages))

    results: list[dict] = []
    for msg in messages:
        mid = msg.get("id", "?")
        if use_stream and log is not None and rule_factory is not None:
            log.print(
                rule_factory(f"[bold cyan]Triage - message[/] [white]{mid}[/]", style="dim"),
            )
        row = run_message(
            agent,
            msg,
            stream_logs=use_stream,
            log_console=log if use_stream else None,
        )
        results.append(row)
        if use_stream and log is not None:
            if row.get("error"):
                log.print(f"[bold red]x Failed:[/bold red] {row['error']}")
            else:
                route = (row.get("result") or {}).get("route", "unknown")
                usage = _usage_from_row(row)
                if usage is None:
                    log.print(f"[bold green]OK[/bold green] route=[cyan]{route}[/cyan]")
                else:
                    log.print(
                        "[bold green]OK[/bold green] "
                        f"route=[cyan]{route}[/cyan] "
                        f"tokens(in/out/total)=[magenta]{usage['input_tokens']}/{usage['output_tokens']}/{usage['total_tokens']}[/magenta]"
                    )
            log.print()

    session_usage = _sum_session_usage(results)
    if use_stream and log is not None:
        if rule_factory is not None:
            log.print(rule_factory("[bold cyan]Session usage[/]", style="dim"))
        if session_usage is None:
            log.print("[yellow]Token usage unavailable from provider metadata.[/yellow]\n")
        else:
            log.print(
                "[bold]Total tokens[/bold] "
                f"[magenta]{session_usage['total_tokens']}[/magenta]  "
                f"(input [cyan]{session_usage['input_tokens']}[/cyan], "
                f"output [green]{session_usage['output_tokens']}[/green])  "
                f"across [white]{session_usage['messages_with_usage']}[/white] message(s)\n"
            )

    payload = {"results": results}
    text = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
