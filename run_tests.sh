#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[tests] Started at $(date '+%Y-%m-%d %H:%M:%S')"
echo "[tests] Working directory: $SCRIPT_DIR"
echo "[tests] Running: python -m pytest -v"

python -m pytest -v

echo "[tests] Completed at $(date '+%Y-%m-%d %H:%M:%S')"
