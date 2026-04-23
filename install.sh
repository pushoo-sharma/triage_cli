#!/usr/bin/env bash
# Install Python dependencies for a fresh clone (venv + editable install with dev + langchain extras).
# Run from Git Bash, WSL, or macOS/Linux:  bash install.sh
# (On Windows, Python venvs use Scripts/activate; on Unix, bin/activate — both are handled.)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 &>/dev/null; then
  PYTHON=python3
elif command -v python &>/dev/null; then
  PYTHON=python
else
  echo "error: need Python 3.10+ (python3 or python not found)" >&2
  exit 1
fi

if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  ver="$("$PYTHON" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null || echo unknown)"
  echo "error: Python 3.10+ required (found $ver)" >&2
  exit 1
fi

VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating venv: $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
fi

ACTIVATE=""
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  ACTIVATE="$VENV_DIR/bin/activate"
elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
  ACTIVATE="$VENV_DIR/Scripts/activate"
else
  echo "error: venv at $VENV_DIR has no activate script (re-create venv?)" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$ACTIVATE"
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[dev,langchain]"

if [[ -f .env.example ]] && [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (edit for AI mode: GOOGLE_API_KEY or GEMINI_API_KEY)"
fi

echo
echo "Done. Activate the venv in this shell:"
echo "  source \"$ACTIVATE\""
