#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "[tests] Started at $(date '+%Y-%m-%d %H:%M:%S')"
echo "[tests] Working directory: $REPO_ROOT"
echo "[tests] Running: python -m pytest -v"

python -m pytest -v

echo "[tests] Completed at $(date '+%Y-%m-%d %H:%M:%S')"
