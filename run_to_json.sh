#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python -m triage.runner data/sample_messages.jsonl -o triage_output.json
echo "Wrote triage output to triage_output.json"
