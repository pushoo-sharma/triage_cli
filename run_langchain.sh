#!/usr/bin/env bash
# Optional LangChain triage: requires pip install -e ".[langchain]"
#   Copy .env.example to .env and set GOOGLE_API_KEY (or export it in the shell)
#   TRIAGE_LANGCHAIN_MODEL overrides the default (google_genai:gemini-2.0-flash)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python -m triage_langchain data/sample_messages.json -o langchain_output.json
echo "Wrote langchain output to langchain_output.json"
