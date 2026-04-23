# shellcheck shell=bash
# Shared terminal-UI helpers for scripts/ — source this file, don't run it.
#
# Primary UI: Charm "gum" (https://github.com/charmbracelet/gum).
#   winget install charmbracelet.gum   # Windows
#   brew install gum                   # macOS
#   sudo apt install gum               # Debian/Ubuntu
#
# Fallback: plain ANSI + Unicode box drawing, no dependencies.

# ---------------------------------------------------------------------------
# Locate gum: prefer PATH, then known winget install locations on Windows.
# Exports the GUM variable (empty string if unavailable).
# ---------------------------------------------------------------------------
_ui_find_gum() {
  if command -v gum >/dev/null 2>&1; then
    GUM="gum"
    return
  fi
  local candidate
  for candidate in \
    "${LOCALAPPDATA:-}/Microsoft/WinGet/Links/gum.exe" \
    "${LOCALAPPDATA:-}"/Microsoft/WinGet/Packages/charmbracelet.gum_*/gum_*_Windows_x86_64/gum.exe
  do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      GUM="$candidate"
      return
    fi
  done
  GUM=""
}
_ui_find_gum

# Detect a usable TTY on stdout — gum's styled output is pointless otherwise.
if [[ -t 1 ]]; then
  UI_TTY=1
else
  UI_TTY=0
  GUM=""   # disable gum when output is piped/redirected
fi

# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
ui_banner() {
  # $1 = title, $2 = subtitle (optional)
  local title="${1:-}"
  local subtitle="${2:-}"
  if [[ -n "$GUM" ]]; then
    if [[ -n "$subtitle" ]]; then
      "$GUM" style \
        --border double --margin "1 2" --padding "1 4" \
        --border-foreground 212 --foreground 213 --bold --align center \
        "$title" "$subtitle"
    else
      "$GUM" style \
        --border double --margin "1 2" --padding "1 4" \
        --border-foreground 212 --foreground 213 --bold --align center \
        "$title"
    fi
  else
    local line
    line="$(printf '─%.0s' {1..54})"
    printf '\n  \e[1;35m┌%s┐\e[0m\n' "$line"
    printf '  \e[1;35m│\e[0m   \e[1;95m%-48s\e[0m   \e[1;35m│\e[0m\n' "$title"
    [[ -n "$subtitle" ]] && \
      printf '  \e[1;35m│\e[0m   \e[2m%-48s\e[0m   \e[1;35m│\e[0m\n' "$subtitle"
    printf '  \e[1;35m└%s┘\e[0m\n\n' "$line"
  fi
}

ui_step() {
  # Section heading inside a running script, e.g. ui_step "Running pytest"
  if [[ -n "$GUM" ]]; then
    "$GUM" style \
      --border rounded --margin "1 2" --padding "0 2" \
      --border-foreground 39 --foreground 51 --bold \
      "▶  $*"
  else
    printf '\n  \e[1;36m▶  %s\e[0m\n  \e[2m%s\e[0m\n' "$*" "$(printf '─%.0s' {1..56})"
  fi
}

ui_kv() {
  # $1 = key, $2 = value — tidy aligned label / value line.
  if [[ -n "$GUM" ]]; then
    printf '  %s %s\n' \
      "$("$GUM" style --foreground 99 --bold -- "$(printf '%-10s' "$1")")" \
      "$("$GUM" style --foreground 252     -- "$2")"
  else
    printf '  \e[1;34m%-10s\e[0m %s\n' "$1" "$2"
  fi
}

ui_info() { [[ -n "$GUM" ]] && "$GUM" log --level info  -- "$*" || printf '  \e[36m[info]\e[0m %s\n' "$*"; }
ui_warn() { [[ -n "$GUM" ]] && "$GUM" log --level warn  -- "$*" || printf '  \e[33m[warn]\e[0m %s\n' "$*"; }
ui_err()  { [[ -n "$GUM" ]] && "$GUM" log --level error -- "$*" || printf '  \e[31m[err]\e[0m  %s\n' "$*" >&2; }
ui_ok()   { [[ -n "$GUM" ]] && "$GUM" log --level info  -- "$*" || printf '  \e[32m[ok]\e[0m   %s\n' "$*"; }

ui_rule() {
  local line
  line="$(printf '─%.0s' {1..56})"
  printf '  \e[2m%s\e[0m\n' "$line"
}

# ui_run TITLE -- CMD...
#   Prints a step banner, runs the command (streaming output), then prints
#   a colored success / failure summary with elapsed time.
#   Returns the command's exit code.
ui_run() {
  local title="$1"; shift
  [[ "${1:-}" == "--" ]] && shift
  ui_step "$title"
  local start end dur ec=0
  start=$(date +%s)
  "$@" || ec=$?
  end=$(date +%s)
  dur=$((end - start))
  echo
  if (( ec == 0 )); then
    ui_ok "Completed in ${dur}s (exit 0)"
  else
    ui_err "Failed after ${dur}s (exit $ec)"
  fi
  return "$ec"
}
