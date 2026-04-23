# AI Message Triage

Small Python app for triaging property-management inbound messages.

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

1. Set one of:

- `GOOGLE_API_KEY=...`
- or `GEMINI_API_KEY=...`

1. Optional model override:

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
Core project code and structure in local triage and evaluation flow, including `src/triage/runner.py`.
- **Adapted/generated with AI help:**
Newly added AI CLI tool (`src/triage_langchain/__main__.py`), LangChain integration, and agent integration logic (`src/triage_langchain/workflow.py`), plus documentation drafting/refinement in `Readme.md` and `langchain_readme.md`.
- **This update specifically:**
The `Next product improvements`, `New additions`, and this authorship statement were drafted with AI assistance and committed after human review/editing.

## Additional docs

- Detailed AI mode guide: `langchain_readme.md`

