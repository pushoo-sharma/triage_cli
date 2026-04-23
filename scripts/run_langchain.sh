#!/usr/bin/env bash
# LangChain AI triage.
#   pip install -e ".[langchain]"
#   copy .env.example to .env and set GOOGLE_API_KEY / GEMINI_API_KEY
#   TRIAGE_LANGCHAIN_MODEL overrides the default (google_genai:gemini-2.0-flash)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# shellcheck source=./_ui.sh
source "$SCRIPT_DIR/_ui.sh"

IN_FILE="data/sample_messages.json"
OUT_DIR="output/ai"
OUT_FILE="$OUT_DIR/langchain_output.json"
mkdir -p "$OUT_DIR"

ui_banner "LangChain AI Triage" "Gemini-backed routing"

ui_kv "input"  "$IN_FILE"
ui_kv "output" "$OUT_FILE"
ui_kv "model"  "${TRIAGE_LANGCHAIN_MODEL:-google_genai:gemini-2.0-flash (default)}"

# Resolve which API key is visible to the child process (without printing it).
_env_key=""
if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
  _env_key="GOOGLE_API_KEY"
elif [[ -n "${GEMINI_API_KEY:-}" ]]; then
  _env_key="GEMINI_API_KEY"
elif [[ -f "$REPO_ROOT/.env" ]] \
     && grep -Eq '^(GOOGLE_API_KEY|GEMINI_API_KEY)=' "$REPO_ROOT/.env"; then
  _env_key=".env file"
fi

if [[ -n "$_env_key" ]]; then
  ui_kv "api key" "detected via $_env_key"
else
  ui_kv "api key" "not detected"
  ui_warn "No GOOGLE_API_KEY / GEMINI_API_KEY in env or .env — the agent build will likely fail (exit 1)."
fi

if [[ ! -f "$IN_FILE" ]]; then
  ui_err "Input file not found: $IN_FILE"
  exit 2
fi

echo
ec=0
ui_run "python -m triage_langchain  →  $OUT_FILE" -- \
  python -m triage_langchain "$IN_FILE" -o "$OUT_FILE"
ec=$?

echo
if (( ec == 0 )) && [[ -f "$OUT_FILE" ]]; then
  size="$(wc -c <"$OUT_FILE" 2>/dev/null | tr -d ' ' || echo '?')"
  ui_ok  "Wrote langchain output  ·  ${size} bytes"
  ui_kv "file" "$OUT_FILE"
else
  case "$ec" in
    1) ui_err "Input parse/read error or agent-build failure (exit 1) — check your API key or .env." ;;
    2) ui_err "CLI usage / argument error (exit 2)." ;;
    *) ui_err "Process failed with exit $ec." ;;
  esac
fi

exit "$ec"
