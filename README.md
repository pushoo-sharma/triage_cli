# AI Message Triage

Small Python app for triaging property-management inbound messages.

It supports two run modes:

- `Local (rule-based)`: deterministic, no network/API key required, entrypoint `python -m triage.runner`
- `AI (LangChain + Gemini)`: model-based triage using Google Gemini, entrypoint `python -m triage_langchain`

## Prerequisites

- Python `3.10+`
- `pip`
- Optional for AI mode: Google Gemini API key

## Setup

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

1. Copy the example file:

```bash
cp .env.example .env
```

2. Set one of:

- `GOOGLE_API_KEY=...`
- or `GEMINI_API_KEY=...`

3. Optional model override:

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
bash run_langchain.sh
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

## Project entrypoints

- Local runner: `src/triage/runner.py`
- AI runner: `src/triage_langchain/__main__.py`
- AI workflow + env loading: `src/triage_langchain/workflow.py`

## Additional docs

- Detailed AI mode guide: `langchain_readme.md`

