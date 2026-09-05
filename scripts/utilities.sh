#!/bin/bash
# Shared color/UI helpers for scripts/*.sh — colors, section headers, spinners,
# step counters, and progress bars, so scripts share one visual language
# instead of each defining its own ANSI escapes ad hoc (#551).
# Source this file in other scripts: source "$(dirname "$0")/utilities.sh"

# Colors — blank when $NO_COLOR is set (https://no-color.org) or stdout isn't
# a TTY (piped to a log file, cron, systemd journal). Every script that
# sources this file gets that fallback for free.
#
# Terminal-safe 8-color approximation of the Fair Weather brand tokens
# (docs/designs/FAIR_WEATHER_BRAND_BOOK.md): GREEN~--success, YELLOW~--warning,
# RED~--danger, CYAN~--accent (cobalt, structural chrome). Coral (--accent-warm)
# has no 8-color analog and isn't used here — it's a single-CTA UI accent, not
# a status color.
if [[ -n "${NO_COLOR:-}" ]] || [[ ! -t 1 ]]; then
    export RED='' GREEN='' YELLOW='' BLUE='' CYAN='' NC='' BOLD='' DIM=''
    export _PLAIN_OUTPUT=1
else
    export RED='\033[0;31m'
    export GREEN='\033[0;32m'
    export YELLOW='\033[1;33m'
    export BLUE='\033[0;34m'
    export CYAN='\033[0;36m'
    export NC='\033[0m'
    export BOLD='\033[1m'
    export DIM='\033[2m'
    export _PLAIN_OUTPUT=0
fi

# ── Progress & Status UI ─────────────────────────────────────────────────────
#
#  section "Title" [emoji]          — recipe-card section header
#  steps_init <n>                   — start a numbered step sequence
#  step "description"               — print next step (auto-increments)
#  start_spinner "message"          — animated braille spinner in background
#  stop_spinner [ok|fail]           — stop spinner, print ✓ or ✗
#  progress_bar <n> <total> [label] — inline progress bar (call in a loop)
#  timer_start / timer_end          — elapsed-time bookends
#  wait_for "desc" <timeout> <interval> <cmd> [args...]
#                                   — spin + poll until cmd succeeds or times out
# ─────────────────────────────────────────────────────────────────────────────

# Print a recipe-card style section header with an underline rule.
# Usage: section "Heading" [emoji]
section() {
    local title="$1"
    local emoji="${2:-🚲}"
    echo ""
    echo -e "${CYAN}  ${emoji}  ${BOLD}${title}${NC}"
    echo -e "${CYAN}  ──────────────────────────────────────────────${NC}"
}

# Initialise a numbered step counter.
# Usage: steps_init <total>
_STEP_CURRENT=0
_STEP_TOTAL=0
steps_init() {
    _STEP_TOTAL="${1:-0}"
    _STEP_CURRENT=0
}

# Print the next numbered step.
# Usage: step "Description"
step() {
    _STEP_CURRENT=$(( _STEP_CURRENT + 1 ))
    local label="$1"
    if [[ "$_STEP_TOTAL" -gt 0 ]]; then
        echo -e "  ${CYAN}▸${NC} ${BOLD}[$_STEP_CURRENT/$_STEP_TOTAL]${NC} $label"
    else
        echo -e "  ${CYAN}▸${NC} $label"
    fi
}

# Start an animated braille spinner in the background.
# Usage: start_spinner "message"
_SPINNER_PID=""
_SPINNER_MSG=""
_SPINNER_ACTIVE=0
start_spinner() {
    [[ "${_SPINNER_ACTIVE:-0}" == "1" ]] && return
    local msg="${1:-Working...}"
    _SPINNER_MSG="$msg"
    _SPINNER_ACTIVE=1
    if [[ "${_PLAIN_OUTPUT:-0}" == "1" ]]; then
        # No TTY / NO_COLOR: an animated line would just leave raw \r noise
        # in a log file, so print the message once and let stop_spinner
        # print the final glyph on its own line instead.
        printf "  %s... " "$msg"
        return
    fi
    (
        local i=0
        local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
        while true; do
            printf "\r  \033[0;36m%s\033[0m  %s " "${frames[$i]}" "$msg"
            i=$(( (i + 1) % 10 ))
            sleep 0.1
        done
    ) &
    _SPINNER_PID=$!
    disown "$_SPINNER_PID" 2>/dev/null || true
}

# Stop the spinner and print ✓ (ok) or ✗ (fail) on the cleared line.
# Usage: stop_spinner [ok|fail]
stop_spinner() {
    local status="${1:-ok}"
    _SPINNER_ACTIVE=0
    if [[ -n "${_SPINNER_PID:-}" ]]; then
        kill "$_SPINNER_PID" 2>/dev/null || true
        _SPINNER_PID=""
    fi
    if [[ "${_PLAIN_OUTPUT:-0}" == "1" ]]; then
        # Nothing was animated, so nothing to clear — just land the glyph.
        if [[ "$status" == "fail" ]]; then
            echo "✗  ${_SPINNER_MSG}"
        else
            echo "✓  ${_SPINNER_MSG}"
        fi
        return
    fi
    printf "\r\033[2K"
    if [[ "$status" == "fail" ]]; then
        echo -e "  ${RED}✗${NC}  ${_SPINNER_MSG}"
    else
        echo -e "  ${GREEN}✓${NC}  ${_SPINNER_MSG}"
    fi
}

# Render an inline progress bar. Call once per iteration inside a loop.
# Prints a newline automatically on the final step.
# Usage: progress_bar <current> <total> [label]
progress_bar() {
    local current=$1
    local total=$2
    local label="${3:-}"
    local width=28
    local filled=$(( total > 0 ? current * width / total : 0 ))
    local empty=$(( width - filled ))
    local bar="" i
    for (( i=0; i<filled; i++ )); do bar+="█"; done
    for (( i=0; i<empty; i++ )); do bar+="░"; done
    local pct=$(( total > 0 ? current * 100 / total : 0 ))
    printf "\r  %-22s ${GREEN}%s${NC} %3d%%" "${label}" "$bar" "$pct"
    [[ "$current" -ge "$total" ]] && echo ""
}

# Mark the start of a timed section. Pair with timer_end.
_TIMER_START=0
timer_start() { _TIMER_START=$SECONDS; }

# Print elapsed time since timer_start.
timer_end() {
    local elapsed=$(( SECONDS - _TIMER_START ))
    local mins=$(( elapsed / 60 ))
    local secs=$(( elapsed % 60 ))
    if [[ $mins -gt 0 ]]; then
        echo -e "  ${DIM}⏱  Done in ${mins}m ${secs}s${NC}"
    else
        echo -e "  ${DIM}⏱  Done in ${secs}s${NC}"
    fi
}

# Poll an external command until it succeeds or the timeout expires,
# showing an animated spinner throughout.
# Usage: wait_for "description" <timeout_sec> <interval_sec> <command> [args...]
# Returns 0 on success, 1 on timeout.
wait_for() {
    local desc="$1"
    local timeout="$2"
    local interval="$3"
    shift 3
    local waited=0
    start_spinner "$desc"
    while [[ $waited -lt $timeout ]]; do
        if "$@" &>/dev/null 2>&1; then
            stop_spinner ok
            return 0
        fi
        sleep "$interval"
        waited=$(( waited + interval ))
    done
    stop_spinner fail
    return 1
}
