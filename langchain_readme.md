# LangChain message triage (`triage_langchain`)

This document describes the **optional** LLM-based workflow in [`src/triage_langchain/`](src/triage_langchain/). It is **separate** from the rule-based `python -m triage.runner` pipeline: same style of input files (JSON array or JSONL), but classification is done by a Google Gemini model via LangChain, not by `triage.core`.

## Prerequisites

- Python 3.10+
- A **Google AI Studio / Gemini API key** ([Google AI Studio](https://aistudio.google.com/apikey)) for the default model provider.

## 1. Install

From the repository root:

```bash
python3 -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -e ".[langchain]"
```

The `langchain` extra installs: `langchain`, `langchain-google-genai`, `pydantic`, and `python-dotenv`.

## 2. API key and optional `.env`

**Option A — `.env` file (recommended for local dev)**

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set at least one of:

   - `GOOGLE_API_KEY=...`
   - or `GEMINI_API_KEY=...`

3. Keep `.env` out of version control (it is listed in [`.gitignore`](.gitignore)).

The app loads environment variables from:

- the current working directory (standard `python-dotenv` behavior), and
- **`<repo>/.env`** next to the project root (so the key is found even if your shell is not the repo root).

Variables already set in the environment are **not** overridden by `.env` (`override=False`).

**Option B — shell only**

```bash
export GOOGLE_API_KEY="your-key"
# Windows (cmd): set GOOGLE_API_KEY=your-key
# Windows (PowerShell): $env:GOOGLE_API_KEY="your-key"
```

## 3. Run

**CLI (cross-platform)**

```bash
# From repository root; writes JSON to stdout
python -m triage_langchain data/sample_messages.json

# Write results to a file
python -m triage_langchain data/sample_messages.json -o langchain_output.json
python -m triage_langchain data/sample_messages.jsonl -o langchain_output.json
```

**Helper script (Git Bash / WSL / macOS / Linux)**

```bash
bash run_langchain.sh
```

This `cd`s to the repo root and runs the sample file to `langchain_output.json`.

**Help / usage**

```bash
python -m triage_langchain
# prints usage to stderr and exits with code 2
```

## 4. Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Yes (for real calls) | Gemini API key for `langchain-google-genai`. |
| `TRIAGE_LANGCHAIN_MODEL` | No | Model id string. Default: `google_genai:gemini-2.0-flash`. |

## 5. Output format

The command writes a single JSON object to stdout or to `-o`:

```json
{
  "results": [
    {
      "input": {
        "id": "msg_001",
        "sender": "resident",
        "subject": "Tour",
        "body": "Can I schedule a tour?"
      },
      "output": {
        "id": "msg_001",
        "error": null,
        "result": {
          "route": "auto_draft",
          "category": "leasing_general",
          "confidence": 50,
          "reason": "...",
          "review_recommended": false,
          "review_triggers": []
        }
      }
    },
    {
      "input": {
        "id": "msg_002",
        "body": "..."
      },
      "output": {
        "id": "msg_002",
        "error": "…",
        "result": null
      }
    }
  ]
}
```

- Each `results` item now has:
  - `input`: the original input message object
  - `output`: the triage outcome payload for that input
- `output.id` comes from the input message’s `id` when present.
- `output.result` is the structured model output (`AgentTriageResult` in [`src/triage_langchain/schemas.py`](src/triage_langchain/schemas.py)) when the run succeeds.
- `confidence` is an integer percentage from `0` to `100`.
- `output.error` is set when a per-message call fails; other rows may still succeed.

## 6. Exit codes

- `0` — finished writing output.
- `1` — input read/parse error, or agent could not be built (e.g. missing API key).
- `2` — bad/missing CLI arguments; usage printed to stderr.

## 7. How this differs from `triage.runner`

| | Rule-based triage | LangChain (`triage_langchain`) |
|---|-------------------|---------------------------------|
| Entry | `python -m triage.runner <path> [-o …]` | `python -m triage_langchain <path> [-o …]` |
| Network | None (deterministic) | Yes (calls Gemini) |
| Dependencies | Base / `dev` | `pip install -e ".[langchain]"` |

## 8. Tests

To run unit tests that cover the LangChain package (IO, schema, mocked workflow), install both extras and run pytest:

```bash
pip install -e ".[dev,langchain]"
python -m pytest -q
```

Schema and workflow tests are skipped if `pydantic` or `langchain` are not installed, respectively.

## 9. Code layout (reference)

| Path | Role |
|------|------|
| [`src/triage_langchain/workflow.py`](src/triage_langchain/workflow.py) | Model id, dotenv load, `create_agent` + `AgentTriageResult` |
| [`src/triage_langchain/__main__.py`](src/triage_langchain/__main__.py) | CLI |
| [`src/triage_langchain/io.py`](src/triage_langchain/io.py) | JSON array or JSONL loader (mirrors triage behavior, no import from `triage`) |
| [`run_langchain.sh`](run_langchain.sh) | Optional bash wrapper |
| [`.env.example`](.env.example) | Template for `GOOGLE_API_KEY` and optional `TRIAGE_LANGCHAIN_MODEL` |

The top-level [Readme.md](Readme.md) describes the main trial and the rule-based triage commands; this file is the add-on for the LangChain path.
