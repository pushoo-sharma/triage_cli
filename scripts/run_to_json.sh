#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUT_DIR="output/normal"
OUT_FILE="$OUT_DIR/triage_output.json"
mkdir -p "$OUT_DIR"

python -m triage.runner data/sample_messages.jsonl -o "$OUT_FILE"
echo "Wrote triage output to $OUT_FILE"
