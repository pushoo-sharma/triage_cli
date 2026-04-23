#!/usr/bin/env bash
# Pretty interactive launcher for the Triage project.
#
# Primary UI: Charm "gum" (https://github.com/charmbracelet/gum)
#   winget install charmbracelet.gum        # Windows
#   brew install gum                        # macOS
#   sudo apt install gum                    # Debian/Ubuntu
#
# Fallback UI: bash `select` menu (no extra dependencies).
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Locate `gum` — prefer PATH, then the winget install location (the PATH
# entry is only added after a new shell is opened after install).
# ---------------------------------------------------------------------------
GUM=""
if command -v gum >/dev/null 2>&1; then
  GUM="gum"
else
  for candidate in \
    "$LOCALAPPDATA/Microsoft/WinGet/Links/gum.exe" \
    "$LOCALAPPDATA/Microsoft/WinGet/Packages/charmbracelet.gum_Microsoft.Winget.Source_8wekyb3d8bbwe/gum_0.17.0_Windows_x86_64/gum.exe"
  do
    if [[ -n "${candidate:-}" && -x "$candidate" ]]; then
      GUM="$candidate"
      break
    fi
  done
  # Glob-style fallback for any future gum version installed via winget
  if [[ -z "$GUM" ]]; then
    for candidate in "$LOCALAPPDATA"/Microsoft/WinGet/Packages/charmbracelet.gum_*/gum_*_Windows_x86_64/gum.exe; do
      [[ -x "$candidate" ]] && { GUM="$candidate"; break; }
    done
  fi
fi

# ---------------------------------------------------------------------------
# Menu definition: label → command to run. Keep arrays in lockstep.
# ---------------------------------------------------------------------------
LABELS=(
  "Local triage (rules)  ·  writes output/normal/triage_output.json"
  "AI triage (LangChain) ·  writes output/ai/langchain_output.json"
  "Run full test suite   ·  pytest -v"
  "Evaluate routes       ·  python -m triage.runner eval data/sample_messages.json"
  "Open output folder"
  "Quit"
)
COMMANDS=(
  "run_script scripts/run.sh"
  "run_script scripts/run_langchain.sh"
  "run_script scripts/run_tests.sh"
  "run_eval"
  "open_output"
  "quit"
)

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
clear_screen() { printf '\033[H\033[2J\033[3J'; }

header() {
  if [[ -n "$GUM" ]]; then
    "$GUM" style \
      --border double --margin "1 2" --padding "1 4" \
      --border-foreground 212 --foreground 213 --bold --align center \
      "AI Message Triage" "Interactive launcher"
    "$GUM" style --faint --margin "0 2" "repo: $REPO_ROOT"
  else
    local line
    line="$(printf '─%.0s' {1..54})"
    printf '\n  \e[1;35m┌%s┐\e[0m\n' "$line"
    printf '  \e[1;35m│\e[0m   \e[1;95m%-48s\e[0m   \e[1;35m│\e[0m\n' "AI Message Triage — Interactive launcher"
    printf '  \e[1;35m│\e[0m   \e[2m%-48s\e[0m   \e[1;35m│\e[0m\n' "repo: $REPO_ROOT"
    printf '  \e[1;35m└%s┘\e[0m\n\n' "$line"
  fi
}

info()  { [[ -n "$GUM" ]] && "$GUM" log --level info  -- "$@" || printf '  \e[36m[info]\e[0m %s\n' "$*"; }
warn()  { [[ -n "$GUM" ]] && "$GUM" log --level warn  -- "$@" || printf '  \e[33m[warn]\e[0m %s\n' "$*"; }
err()   { [[ -n "$GUM" ]] && "$GUM" log --level error -- "$@" || printf '  \e[31m[err]\e[0m  %s\n' "$*" >&2; }
okay()  { [[ -n "$GUM" ]] && "$GUM" log --level info  -- "$@" || printf '  \e[32m[ok]\e[0m   %s\n' "$*"; }

press_enter() {
  echo
  if [[ -n "$GUM" ]]; then
    "$GUM" input --placeholder "Press Enter to return to menu..." >/dev/null || true
  else
    read -r -p "  Press Enter to return to menu..." _ || true
  fi
}

# ---------------------------------------------------------------------------
# Menu — sets global SELECTED_INDEX (0-based) or 255 for quit/escape.
# ---------------------------------------------------------------------------
SELECTED_INDEX=255

menu() {
  SELECTED_INDEX=255
  if [[ -n "$GUM" ]]; then
    local choice
    # --no-limit=false (single-select); show cursor; color selected item
    choice="$(
      "$GUM" choose \
        --header "  What would you like to run?" \
        --cursor "  ➤ " --cursor.foreground 212 \
        --header.foreground 99 \
        --selected.foreground 212 \
        --height "$(( ${#LABELS[@]} + 4 ))" \
        "${LABELS[@]}"
    )" || { SELECTED_INDEX=255; return; }

    local i
    for i in "${!LABELS[@]}"; do
      if [[ "${LABELS[$i]}" == "$choice" ]]; then
        SELECTED_INDEX=$i
        return
      fi
    done
    return
  fi

  printf '  \e[1mChoose an action:\e[0m\n\n'
  local i
  for i in "${!LABELS[@]}"; do
    printf '    \e[32m%2d\e[0m  %s\n' $((i + 1)) "${LABELS[$i]}"
  done
  echo
  local n
  while :; do
    read -r -p "  >  " n || { SELECTED_INDEX=255; return; }
    n="${n//[[:space:]$'\r']/}"
    [[ "$n" == "q" || "$n" == "Q" ]] && { SELECTED_INDEX=$((${#LABELS[@]} - 1)); return; }
    if [[ "$n" =~ ^[0-9]+$ ]] && (( n >= 1 && n <= ${#LABELS[@]} )); then
      SELECTED_INDEX=$((n - 1))
      return
    fi
    warn "Enter a number between 1 and ${#LABELS[@]}, or q to quit."
  done
}

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
banner_for() {
  local title="$1"
  clear_screen
  if [[ -n "$GUM" ]]; then
    "$GUM" style \
      --border rounded --margin "1 2" --padding "0 2" \
      --border-foreground 39 --foreground 51 --bold \
      "▶  $title"
  else
    printf '\n  \e[1;36m▶  %s\e[0m\n  \e[2m%s\e[0m\n' "$title" "$(printf '─%.0s' {1..56})"
  fi
}

run_script() {
  local script_path="$1"
  local title="${script_path}"
  banner_for "Running: $title"
  if [[ ! -f "$script_path" ]]; then
    err "Script not found: $script_path"
    press_enter
    return
  fi
  local start end dur ec=0
  start=$(date +%s)
  bash "$script_path" || ec=$?
  end=$(date +%s)
  dur=$(( end - start ))
  echo
  if (( ec == 0 )); then
    okay "Completed in ${dur}s (exit 0)"
  else
    err "Failed after ${dur}s (exit $ec)"
  fi
  press_enter
}

run_eval() {
  banner_for "Running: python -m triage.runner eval"
  local ec=0
  python -m triage.runner eval data/sample_messages.json || ec=$?
  echo
  if (( ec == 0 )); then
    okay "All labeled rows matched (exit 0)"
  elif (( ec == 1 )); then
    warn "Mismatches found (exit 1)"
  else
    err "Evaluation error (exit $ec)"
  fi
  press_enter
}

open_output() {
  local target="$REPO_ROOT/output"
  mkdir -p "$target"
  banner_for "Opening: $target"
  if command -v explorer.exe >/dev/null 2>&1; then
    # Windows path so Explorer understands it.
    explorer.exe "$(cygpath -w "$target" 2>/dev/null || echo "$target")" >/dev/null 2>&1 || true
    okay "Launched Windows Explorer"
  elif command -v open >/dev/null 2>&1; then
    open "$target"
    okay "Launched Finder"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$target" >/dev/null 2>&1 || true
    okay "Launched file manager"
  else
    warn "No file-manager opener found. Path: $target"
  fi
  press_enter
}

quit() {
  if [[ -n "$GUM" ]]; then
    "$GUM" style --foreground 212 --margin "1 2" "Goodbye."
  else
    printf '\n  \e[95mGoodbye.\e[0m\n\n'
  fi
  exit 0
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
main() {
  while :; do
    clear_screen
    header
    menu
    if (( SELECTED_INDEX >= ${#COMMANDS[@]} )); then
      quit
    fi
    # Dispatch: the action strings are safe literals we control.
    eval "${COMMANDS[$SELECTED_INDEX]}"
  done
}

main "$@"
