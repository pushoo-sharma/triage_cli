# AI Message Triage

Small Python app for triaging property-management inbound messages.

## Interactive menu (`triage-menu.sh`)

The usual starting point in a shell is the **interactive launcher** at the repo root. After [setup](#setup) (venv activated and dependencies installed), run:

```bash
bash triage-menu.sh
```

**Optional UI:** If **[Charm `gum`](https://github.com/charmbracelet/gum)** is installed, the menu uses styled prompts. On Windows, `winget install charmbracelet.gum` is enough; the script also looks in common WinGet install paths if `gum` is not on `PATH` yet. On macOS use `brew install gum`; on Debian/Ubuntu, `sudo apt install gum`.

**No `gum`:** The same actions are available through a simple numeric **bash** menu (no extra tools).

**Actions** (roughly): run local (rules) triage to `output/normal/triage_output.json`, run AI (LangChain) triage to `output/ai/langchain_output.json`, run the full test suite, evaluate routes against `data/sample_messages.json`, open the `output/` folder in the system file manager (Explorer / Finder / `xdg-open`), or quit.

For a short description of every shell script, including the ones the menu calls, see [Shell scripts](#shell-scripts).

## Overview

It supports two run modes:

- `Local (rule-based)`: deterministic, no network/API key required, entrypoint `python -m triage.runner`
- `AI (LangChain + Gemini)`: model-based triage using Google Gemini, entrypoint `python -m triage_langchain`

## New additions

- **New AI CLI tool:** Added AI triage CLI entrypoint at `python -m triage_langchain` for model-based routing from the command line.
- **LangChain integration:** Added LangChain-based workflow integration for prompt-driven triage and structured model outputs.
- **Agent integration:** Added agent orchestration in the AI pipeline for end-to-end message analysis and route decision generation.

## Prerequisites

- Python `3.10+`
- `pip`
- Optional for AI mode: Google Gemini API key

## Setup

### Automated install (recommended)

From repo root, using Git Bash, WSL, macOS, or Linux:

```bash
bash install.sh
```

This script:

- creates `.venv` if it does not exist
- upgrades `pip` / `setuptools` / `wheel`, then runs `pip install -e ".[dev,langchain]"`
- copies `.env.example` to `.env` when `.env` is missing (edit `.env` for AI mode; see [Environment variables](#environment-variables-env))

Venv layout differs by OS: on Windows, activation is `source .venv/Scripts/activate` in Git Bash; on Unix, `source .venv/bin/activate`. The script detects both and prints the right `source` line when it finishes.

Override the venv location:

```bash
VENV_DIR=/path/to/venv bash install.sh
```

### Manual setup

From repo root:

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Windows (cmd): .venv\Scripts\activate
# macOS/Linux/Git Bash: source .venv/bin/activate
```

### Install dependencies

Install base + test tooling (enough for local mode and tests):

```bash
pip install -e ".[dev]"
```

Install AI mode extras:

```bash
pip install -e ".[langchain]"
```

Install everything at once:

```bash
pip install -e ".[dev,langchain]"
```

## Environment variables (`.env`)

Environment setup is only required for AI mode.

1. If you do not already have a `.env` file, create one. If you use [`install.sh`](#automated-install-recommended), a missing `.env` is created from `.env.example` automatically. Otherwise:

```bash
cp .env.example .env
```

2. In `.env` (or your environment), set one of:

- `GOOGLE_API_KEY=...`
- or `GEMINI_API_KEY=...`

3. Optional: model override in `.env` or the shell:

- `TRIAGE_LANGCHAIN_MODEL=google_genai:gemini-3.1-flash-lite-preview`

Notes:

- `.env` is gitignored.
- Variables already present in your shell are not overridden by `.env`.

## Run the app

### 1) Local mode (rule-based, no API key)

Run against sample data (JSON array or JSONL):

```bash
python -m triage.runner data/sample_messages.json
```

Write output to file:

```bash
python -m triage.runner data/sample_messages.json -o output/local/triage_output.json
```

Evaluate against `expected_route` labels:

```bash
python -m triage.runner eval data/sample_messages.json
```

Evaluation exits with:

- `0` when all labeled rows match
- `1` when any labeled row mismatches

### 2) AI mode (LangChain + Gemini)

Run from repository root:

```bash
python -m triage_langchain data/sample_messages.json -o output/ai/langchain_output.json
```

Optional helper script (Git Bash/WSL/macOS/Linux):

```bash
bash scripts/run_langchain.sh
```

This writes to `output/ai/langchain_output.json`.

AI mode exits with:

- `0` success
- `1` input parse/read error or agent-build failure (for example missing API key)
- `2` CLI usage/argument error

## Run tests

Run full test suite:

```bash
python -m pytest -q
```

Tips:

- For local-only development, `pip install -e ".[dev]"` is sufficient.
- For LangChain-related tests, install `.[langchain]` (or `.[dev,langchain]`) so those tests do not get skipped.
- `bash install.sh` installs `[dev,langchain]` in one step (see [Setup](#setup)).

## Project entrypoints

- Local runner: `src/triage/runner.py`
- AI runner: `src/triage_langchain/__main__.py`
- AI workflow + env loading: `src/triage_langchain/workflow.py`

## Shell scripts

Bash helpers for Git Bash, WSL, macOS, and Linux. `triage-menu.sh` is the interactive front end; the others are run directly or from that menu.

| Script | Purpose |
| --- | --- |
| [`triage-menu.sh`](triage-menu.sh) | Interactive launcher: optional `gum` UI or fallback bash menu; runs local/AI triage, tests, eval, or opens `output/`. Stays in a loop until you quit. |
| [`install.sh`](install.sh) | One-shot setup: creates `.venv`, upgrades pip tooling, `pip install -e ".[dev,langchain]"`, copies `.env` from `.env.example` if missing. See [Automated install](#automated-install-recommended). |
| [`scripts/run.sh`](scripts/run.sh) | **Local (rules) triage:** `python -m triage.runner` on `data/sample_messages.jsonl`, writes `output/normal/triage_output.json`. |
| [`scripts/run_to_json.sh`](scripts/run_to_json.sh) | Same command and output as `run.sh` (local triage to `output/normal/triage_output.json` from `data/sample_messages.jsonl`). Use whichever name you prefer. |
| [`scripts/run_langchain.sh`](scripts/run_langchain.sh) | **AI triage:** sources [`scripts/_ui.sh`](scripts/_ui.sh), shows a small banner and API-key hint, then `python -m triage_langchain` on `data/sample_messages.json` → `output/ai/langchain_output.json`. |
| [`scripts/run_tests.sh`](scripts/run_tests.sh) | Runs `python -m pytest -v` from the repo root with simple timestamps in the log. |
| [`scripts/_ui.sh`](scripts/_ui.sh) | **Not executed on its own.** Sourced by scripts that need shared terminal UI helpers (`ui_banner`, `ui_kv`, `ui_run`, etc.), with `gum` or plain ANSI. |

## Output format update

Compared with `old_output.json`, we updated output shape for both current pipelines:

- `output/normal/triage_output.json` now returns a top-level `results` array with both original `input` and normalized `output`, plus a `summary` block for evaluation metrics.
- `output/ai/langchain_output.json` follows the same `results` structure for consistency, and adds AI-specific details like `usage` token counts and richer `result` reasoning fields.

Why this changed:

- A consistent schema across normal and AI modes makes downstream parsing, debugging, and comparisons much easier.
- Keeping both `input` and `output` together improves traceability for audits and triage reviews.
- Adding explicit metrics/metadata (`summary`, `usage`, triggers/reasons) helps explain routing decisions and monitor model cost/performance.

## Next product improvements

1. **Human-in-the-loop review queue**
  Add a confidence score and automatic escalation for borderline cases, so low-confidence messages are flagged for manual review before final routing.
2. **Active learning feedback loop**
  Capture reviewer corrections (`predicted_route` vs. final route) and feed them back into regular prompt/rules updates and regression tests to improve accuracy over time.
3. **Operations dashboard for quality + cost**
  Introduce a simple dashboard/report for route distribution, mismatch trends, and AI token usage to track triage quality and control spend as volume grows.

## Authorship and AI assistance statement

- **Personally written (human-authored):**
  - Core project code and structure in the local triage and evaluation flow.
  - The rule-based pipeline and CLI surface in `src/triage/runner.py` (and related `src/triage` modules that support it).

- **Adapted/generated with AI help:**
  - **AI mode:** the `python -m triage_langchain` entrypoint (`src/triage_langchain/__main__.py`), LangChain wiring, and agent behavior in `src/triage_langchain/workflow.py`.
  - **CLI and shell UX:** helper scripts in `scripts/` (for example `run.sh`, `run_langchain.sh`, `run_tests.sh`, and shared `scripts/_ui.sh`), the root one-step `install.sh`, and the interactive `triage-menu.sh` launcher (optional Charm `gum` with a bash fallback) so common work is a menu choice instead of a long command line.
  - **Documentation:** drafting and refinement in `README.md` and `docs/langchain_readme.md`.

- **This update specifically:**
  - The `Next product improvements` and `New additions` sections in this document.
  - This authorship statement, including the CLI, menu, and install story.
  - Other README changes tied to setup, shell scripts, and navigation (for example the [Shell scripts](#shell-scripts) table).
  - All of the above were produced with AI assistance, then reviewed and edited by a human before commit.

## Additional docs

- Detailed AI mode guide: [`docs/langchain_readme.md`](docs/langchain_readme.md)

