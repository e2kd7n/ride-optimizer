#!/bin/bash
# Weekly Error-Log Triage
#
# Runs cron/log_triage.py inside the app container to cluster recurring
# ERROR/WARNING lines out of logs/cron_*.log, dedupes the resulting
# candidates against every existing `auto-log-triage` GitHub issue (open AND
# closed, so a fixed or wontfix'd problem is never re-filed) via a
# fingerprint marker embedded in each issue body, and files real
# `gh issue create` calls for genuinely new/recurring problems only —
# capped per run to avoid spam, with anything over the cap carried over to
# next week's run instead of dropped. See #550.
#
# This is additive to cron/system_health.py's existing checks and to the
# real-time ntfy alerts in src/ntfy_notifier.py — those tell you something
# is wrong *now*; this makes sure a recurring problem doesn't get lost if
# nobody happens to be watching when it happens.
#
# Usage: ./scripts/log-triage.sh [--dry-run]
#   --dry-run   run the full pipeline (including the real `gh issue list`
#               dedup fetch) but log "would create" instead of filing
#
# Installed weekly via cron/crontab.template, timed to run before
# scripts/rotate-logs.sh rotates the logs this reads.

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Same self-contained .env loading as scripts/weekly-maintenance.sh — no
# ambient `gh auth login` session on unattended Pi cron.
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi

CONTAINER_NAME="${RIDE_OPTIMIZER_CONTAINER:-ride-optimizer}"

# logs/ (not data/) for state — it's already proven writable by both the
# host cron user and the container's rootless-Podman subuid (the crontab
# redirects `>> logs/cron.log` from the host side), whereas data/ is
# subuid-owned and host writes there can hit the ACL-mask PermissionError
# from #543.
LOG_DIR="$PROJECT_ROOT/logs"
STATUS_FILE="$LOG_DIR/log-triage-status.json"
CARRYOVER_FILE="$LOG_DIR/log-triage-carryover.json"
mkdir -p "$LOG_DIR"

MAX_ISSUES_PER_RUN="${MAX_ISSUES_PER_RUN:-5}"
DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

log() { echo -e "[$(date -u +%H:%M:%S)] $1"; }
update_status() {
    cat > "$STATUS_FILE" <<EOF
{"status": "$1", "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "message": "$2"}
EOF
}

echo -e "${BLUE}=== Error-Log Triage - $(date -u +"%Y-%m-%d %H:%M UTC") ===${NC}"

# ── Preflight ────────────────────────────────────────────────────────────
for cmd in gh jq podman; do
    if ! command -v "$cmd" &>/dev/null; then
        log "${RED}ERROR: required command '$cmd' not found on PATH.${NC}"
        update_status "failed" "'$cmd' not installed"
        exit 2
    fi
done

if ! podman ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    log "${RED}ERROR: container '$CONTAINER_NAME' is not running.${NC}"
    update_status "failed" "container '$CONTAINER_NAME' not running"
    exit 2
fi

if [ -z "${GH_TOKEN:-}" ] && [ -z "${GITHUB_TOKEN:-}" ] && ! gh auth status &>/dev/null; then
    log "${RED}ERROR: no GitHub auth available (GH_TOKEN in .env, or 'gh auth login').${NC}"
    update_status "failed" "no GitHub auth available"
    exit 2
fi

update_status "running" "Log triage in progress"

# One-time idempotent bootstrap — safe to run every week.
gh label create auto-log-triage --color "5319e7" \
    --description "Auto-filed by scripts/log-triage.sh (#550)" 2>/dev/null || true

# ── Step 1: cluster candidates inside the container ────────────────────────
CANDIDATES_FILE="$TMP_DIR/candidates.jsonl"
log "Scanning logs/cron_*.log for recurring ERROR/WARNING clusters..."
if ! podman exec "$CONTAINER_NAME" python cron/log_triage.py \
        > "$CANDIDATES_FILE" 2>"$TMP_DIR/log_triage.err"; then
    log "${RED}ERROR: cron/log_triage.py failed:${NC}"
    cat "$TMP_DIR/log_triage.err"
    update_status "failed" "log_triage.py failed — see output above"
    exit 1
fi
[ -s "$TMP_DIR/log_triage.err" ] && cat "$TMP_DIR/log_triage.err" >&2

CANDIDATE_COUNT=$(wc -l < "$CANDIDATES_FILE" | tr -d ' ')
if [ "$CANDIDATE_COUNT" -eq 0 ]; then
    log "${GREEN}Nothing to triage this week.${NC}"
    update_status "complete" "No candidates this run"
    exit 0
fi
log "Found $CANDIDATE_COUNT candidate(s)."

# ── Step 2: merge in carryover from a prior run's spam-guard cap ──────────
# Fresh data supersedes a stale carryover entry with the same fingerprint —
# this run's own version (updated occurrence count) is more accurate.
COMBINED_FILE="$TMP_DIR/combined.jsonl"
: > "$COMBINED_FILE"
if [ -s "$CARRYOVER_FILE" ]; then
    NEW_FP_FILE="$TMP_DIR/new-fingerprints.txt"
    jq -r '.fingerprint' "$CANDIDATES_FILE" | sort -u > "$NEW_FP_FILE"
    CARRIED=0
    while IFS= read -r item; do
        fp=$(echo "$item" | jq -r '.fingerprint')
        grep -qxF "$fp" "$NEW_FP_FILE" && continue
        echo "$item" >> "$COMBINED_FILE"
        CARRIED=$((CARRIED + 1))
    done < <(jq -c '.[]' "$CARRYOVER_FILE" 2>/dev/null)
    [ "$CARRIED" -gt 0 ] && log "Re-considering $CARRIED candidate(s) carried over from a prior capped run."
fi
cat "$CANDIDATES_FILE" >> "$COMBINED_FILE"

# ── Step 3: fetch existing auto-log-triage issues once, dedupe locally ────
EXISTING_FILE="$TMP_DIR/existing.json"
if ! gh issue list --state all --label auto-log-triage \
        --json number,title,body,state --limit 1000 > "$EXISTING_FILE" 2>"$TMP_DIR/gh.err"; then
    log "${RED}ERROR: gh issue list failed — cannot safely dedupe. Aborting before filing anything.${NC}"
    cat "$TMP_DIR/gh.err"
    update_status "failed" "gh issue list (dedup fetch) failed"
    exit 1
fi

is_duplicate() {
    jq -e --arg fp "$1" 'any(.[]; .body // "" | test("fingerprint=" + $fp))' \
        "$EXISTING_FILE" >/dev/null 2>&1
}

# ── Step 4: file (or preview) each candidate, respecting the spam guard ───
FILED=0
DUPLICATES=0
PARTIAL_FAILURE=false
SUPPRESSED_FILE="$TMP_DIR/suppressed.jsonl"
: > "$SUPPRESSED_FILE"

while IFS= read -r item; do
    [ -z "$item" ] && continue
    fingerprint=$(echo "$item" | jq -r '.fingerprint')

    if is_duplicate "$fingerprint"; then
        DUPLICATES=$((DUPLICATES + 1))
        log "Skipping duplicate of an existing auto-log-triage issue (fingerprint $fingerprint)"
        continue
    fi

    if [ "$FILED" -ge "$MAX_ISSUES_PER_RUN" ]; then
        echo "$item" >> "$SUPPRESSED_FILE"
        continue
    fi
    FILED=$((FILED + 1))

    title=$(echo "$item" | jq -r '.title')
    body=$(echo "$item" | jq -r '.body')
    labels=$(echo "$item" | jq -r '.labels | join(",")')

    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN: would create issue: [$labels] $title"
    else
        if gh issue create --title "$title" --body "$body" --label "$labels" >/dev/null 2>"$TMP_DIR/create.err"; then
            log "${GREEN}Filed issue: $title${NC}"
        else
            log "${RED}ERROR: gh issue create failed for: $title${NC}"
            cat "$TMP_DIR/create.err"
            PARTIAL_FAILURE=true
        fi
    fi
done < "$COMBINED_FILE"

SUPPRESSED_COUNT=$(wc -l < "$SUPPRESSED_FILE" | tr -d ' ')
if [ "$SUPPRESSED_COUNT" -gt 0 ]; then
    jq -s '.' "$SUPPRESSED_FILE" > "$CARRYOVER_FILE"
    log "${YELLOW}Carried over $SUPPRESSED_COUNT candidate(s) suppressed by MAX_ISSUES_PER_RUN=$MAX_ISSUES_PER_RUN to next run.${NC}"
else
    echo '[]' > "$CARRYOVER_FILE"
fi

SUMMARY="candidates=$CANDIDATE_COUNT filed=$FILED duplicates=$DUPLICATES suppressed=$SUPPRESSED_COUNT dry_run=$DRY_RUN"
log "=== Done: $SUMMARY ==="

if [ "$PARTIAL_FAILURE" = true ]; then
    update_status "failed" "Partial failure — some gh issue create calls failed ($SUMMARY)"
    exit 3
fi

update_status "complete" "$SUMMARY"
exit 0
