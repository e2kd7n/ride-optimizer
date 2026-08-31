#!/bin/bash
# Weekly Maintenance Script
# Runs documentation sync, issue management, and creates backups
# Usage: ./scripts/weekly-maintenance.sh
#
# Safe to run interactively on a dev machine (existing `gh auth login` session)
# or unattended via the Pi cron entry in cron/crontab.template, which sets
# AUTO_COMMIT_MAINTENANCE=true — see docs/releases/maintenance/WEEKLY_MAINTENANCE.md.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# Store the original working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Self-contained token loading for unattended cron (no `gh auth login` session
# there) — same .env pattern as scripts/backup-env.sh. Falls through to
# ambient `gh` auth when .env isn't present (e.g. a dev machine already
# logged in). Exports everything in .env, including GH_TOKEN, to every `gh`
# call below and to the subprocesses this script shells out to.
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi

CONTAINER_NAME="${RIDE_OPTIMIZER_CONTAINER:-ride-optimizer}"

BACKUP_DIR="$PROJECT_ROOT/backups/maintenance"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
MAINTENANCE_LOG="$LOG_DIR/maintenance-$TIMESTAMP.log"

# Create directories if they don't exist
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

# Create log file immediately
touch "$MAINTENANCE_LOG"

echo -e "${BLUE}=== Weekly Maintenance - $(date -u +"%Y-%m-%d %H:%M UTC") ===${NC}"
echo "Log file: $MAINTENANCE_LOG"
echo ""

# Function to log messages
log() {
    echo "[$(date +%H:%M:%S)] $1" | tee -a "$MAINTENANCE_LOG"
}

log_section() {
    echo "" | tee -a "$MAINTENANCE_LOG"
    echo -e "${GREEN}=== $1 ===${NC}" | tee -a "$MAINTENANCE_LOG"
}

# 1. Create backups
log_section "Creating Backups"
log "Backing up critical files..."

# Backup ISSUE_PRIORITIES.md
if [ -f "ISSUE_PRIORITIES.md" ]; then
    cp ISSUE_PRIORITIES.md "$BACKUP_DIR/ISSUE_PRIORITIES-$TIMESTAMP.md"
    log "✓ Backed up ISSUE_PRIORITIES.md"
fi

# Backup documentation
tar -czf "$BACKUP_DIR/docs-$TIMESTAMP.tar.gz" docs/ 2>/dev/null || true
log "✓ Backed up docs/ directory"

# Backup plans
tar -czf "$BACKUP_DIR/plans-$TIMESTAMP.tar.gz" plans/ 2>/dev/null || true
log "✓ Backed up plans/ directory"

# Clean up old backups (keep last 10)
log "Cleaning up old backups (keeping last 10)..."
ls -t "$BACKUP_DIR"/ISSUE_PRIORITIES-*.md 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
ls -t "$BACKUP_DIR"/docs-*.tar.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
ls -t "$BACKUP_DIR"/plans-*.tar.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
log "✓ Cleanup complete"

# Push backups to GitHub
log_section "Pushing Backups to GitHub"
BACKUP_REPO="https://github.com/e2kd7n/backups.git"
# Embed GH_TOKEN in the clone URL when present so this works unattended (no
# ambient credential helper on Pi cron); falls back to the plain URL so
# interactive runs on a machine with `gh auth setup-git` keep working as-is.
# Never logged — only used as the git remote URL, and the temp clone (whose
# .git/config would carry it) is removed via trap below even on failure.
BACKUP_REPO_AUTH="$BACKUP_REPO"
if [ -n "${GH_TOKEN:-}" ]; then
    BACKUP_REPO_AUTH="https://x-access-token:${GH_TOKEN}@github.com/e2kd7n/backups.git"
fi
TEMP_BACKUP_CLONE=$(mktemp -d)
trap 'rm -rf "$TEMP_BACKUP_CLONE"' EXIT
log "Cloning backup repository..."
if git clone "$BACKUP_REPO_AUTH" "$TEMP_BACKUP_CLONE" 2>/dev/null; then
    mkdir -p "$TEMP_BACKUP_CLONE/ride-optimizer"
    cp "$BACKUP_DIR"/ISSUE_PRIORITIES-"$TIMESTAMP".md "$TEMP_BACKUP_CLONE/ride-optimizer/" 2>/dev/null || true
    cp "$BACKUP_DIR"/docs-"$TIMESTAMP".tar.gz "$TEMP_BACKUP_CLONE/ride-optimizer/" 2>/dev/null || true
    cp "$BACKUP_DIR"/plans-"$TIMESTAMP".tar.gz "$TEMP_BACKUP_CLONE/ride-optimizer/" 2>/dev/null || true
    cd "$TEMP_BACKUP_CLONE"
    git add -A
    if git commit -m "ride-optimizer backup $TIMESTAMP" 2>/dev/null; then
        if git push origin main 2>/dev/null || git push origin master 2>/dev/null; then
            log "✓ Backups pushed to $BACKUP_REPO"
        else
            log "⚠️  Failed to push backups to GitHub"
        fi
    else
        log "✓ No new backup files to push"
    fi
    cd - > /dev/null
else
    log "⚠️  Could not clone $BACKUP_REPO — skipping remote backup"
fi
# Cleanup handled by the trap set above (covers early-exit paths too).

# 2. Git status check
log_section "Git Status Check"
log "Checking for uncommitted changes..."
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Warning: Uncommitted changes detected${NC}" | tee -a "$MAINTENANCE_LOG"
    git status --short | tee -a "$MAINTENANCE_LOG"
else
    log "✓ Working directory clean"
fi

# 3. Recent activity summary
log_section "Recent Activity (Last 7 Days)"
log "Recent commits:"
git log --since="7 days ago" --oneline --no-merges | head -10 | tee -a "$MAINTENANCE_LOG"

# 4. Branch evaluation
log_section "Branch Evaluation"
log "Checking for open branches and PRs..."

# Check for open PRs
OPEN_PRS=$(gh pr list --state open --json number,title,headRefName 2>/dev/null || echo "[]")
PR_COUNT=$(echo "$OPEN_PRS" | jq '. | length' 2>/dev/null || echo "0")

if [ "$PR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $PR_COUNT open PR(s):${NC}" | tee -a "$MAINTENANCE_LOG"
    echo "$OPEN_PRS" | jq -r '.[] | "  #\(.number): \(.title) (\(.headRefName))"' | tee -a "$MAINTENANCE_LOG"
    log "  Action: Review PRs for merge readiness"
else
    log "✓ No open PRs"
fi

# Check for stale branches (not merged, older than 7 days)
log "Checking for stale branches..."
git fetch --prune origin 2>/dev/null || true

STALE_BRANCHES=$(git for-each-ref --sort=-committerdate refs/remotes/origin/ --format='%(refname:short)|%(committerdate:relative)|%(authorname)' | \
    grep -v 'origin/HEAD\|origin/main' | \
    while IFS='|' read -r branch date author; do
        # Check if branch is merged
        if ! git branch -r --merged origin/main | grep -q "$branch"; then
            # Check if older than 7 days
            if echo "$date" | grep -qE '(week|month|year)'; then
                echo "$branch|$date|$author"
            fi
        fi
    done)

if [ -n "$STALE_BRANCHES" ]; then
    echo -e "${YELLOW}⚠️  Found stale unmerged branches:${NC}" | tee -a "$MAINTENANCE_LOG"
    echo "$STALE_BRANCHES" | while IFS='|' read -r branch date author; do
        BRANCH_NAME=$(echo "$branch" | sed 's|origin/||')
        COMMITS_BEHIND=$(git rev-list --count origin/main...$branch 2>/dev/null || echo "?")
        echo "  - $BRANCH_NAME (last commit: $date, $COMMITS_BEHIND commits behind main)" | tee -a "$MAINTENANCE_LOG"
    done
    log "  Action: Review stale branches for closure or rebase"
else
    log "✓ No stale branches found"
fi

# 4b. Worktree hygiene
log_section "Worktree Hygiene"
log "Checking for stale git worktrees (merged/closed PR, no uncommitted or unpushed work)..."
if [ -f "./scripts/prune-worktrees.sh" ]; then
    ./scripts/prune-worktrees.sh "$PROJECT_ROOT" --apply 2>&1 | tee -a "$MAINTENANCE_LOG"
else
    log "⚠️  prune-worktrees.sh not found, skipping"
fi

# 5. Start issue management in background
log_section "Issue Management (Background Task)"
ISSUE_LOG="$LOG_DIR/issue-update-$TIMESTAMP.log"
log "Starting issue priorities update in background..."
log "Log file: $ISSUE_LOG"

# Run issue update in background
if [ -f "./scripts/update-issue-priorities.sh" ]; then
    ./scripts/update-issue-priorities.sh > "$ISSUE_LOG" 2>&1 &
    ISSUE_PID=$!
    echo $ISSUE_PID > /tmp/maintenance-issue-update.pid
    log "✓ Issue update started (PID: $ISSUE_PID)"
    log "  Monitor with: tail -f $ISSUE_LOG"
    log "  Check status: ps -p $ISSUE_PID"
else
    log "⚠️  Issue update script not found, skipping"
fi

# 6. Documentation review checklist
log_section "Documentation Review Checklist"
echo "" | tee -a "$MAINTENANCE_LOG"
echo "Please review the following:" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] docs/VERSIONING_PLAN.md - Version scheme current?" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] docs/TECHNICAL_SPEC.md - Architecture up to date?" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] README.md - Setup instructions accurate?" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] GitHub Milestones - Are open milestones and their issues current? (gh milestone list)" | tee -a "$MAINTENANCE_LOG"
echo "" | tee -a "$MAINTENANCE_LOG"

# 7. Quick stats
log_section "Repository Statistics"
log "Documentation files: $(find docs -name '*.md' | wc -l | tr -d ' ')"
log "Python modules: $(find src app -name '*.py' 2>/dev/null | wc -l | tr -d ' ')"
log "Test files: $(find tests -name 'test_*.py' 2>/dev/null | wc -l | tr -d ' ')"
log "Total commits: $(git rev-list --count HEAD)"

# 8. Update weekly maintenance log
log_section "Updating Weekly Maintenance Log"
WEEKLY_LOG="docs/releases/maintenance/WEEKLY_MAINTENANCE.md"
if [ -f "$WEEKLY_LOG" ]; then
    # Create a temporary file with the new entry
    TEMP_FILE=$(mktemp)
    
    # Extract the header up to "Last Sync Date"
    sed -n '1,/^## Last Sync Date/p' "$WEEKLY_LOG" > "$TEMP_FILE"
    
    # Add new sync entry
    cat >> "$TEMP_FILE" << EOF

**Last Documentation Sync:** $(date -u +"%Y-%m-%d %H:%M UTC")
**Next Scheduled Sync:** $(date -u -v+7d +"%Y-%m-%d" 2>/dev/null || date -u -d "+7 days" +"%Y-%m-%d")
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: ${ISSUE_PID:-N/A})
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
EOF
    
    # Append the rest of the file (skip the old "Last Sync Date" section)
    sed -n '/^**Last Documentation Sync:/,/^**Previous Sync/p' "$WEEKLY_LOG" | tail -n +2 >> "$TEMP_FILE"
    sed -n '/^**Previous Sync/,$p' "$WEEKLY_LOG" | tail -n +2 >> "$TEMP_FILE"
    
    # Replace the original file
    mv "$TEMP_FILE" "$WEEKLY_LOG"
    log "✓ Updated $WEEKLY_LOG"
else
    log "⚠️  Weekly maintenance log not found"
fi

# 9. Summary
log_section "Maintenance Summary"
echo "" | tee -a "$MAINTENANCE_LOG"
echo -e "${GREEN}✓ Backups created in $BACKUP_DIR (and pushed to github.com/e2kd7n/backups)${NC}" | tee -a "$MAINTENANCE_LOG"
echo -e "${GREEN}✓ Issue management running in background${NC}" | tee -a "$MAINTENANCE_LOG"
echo -e "${GREEN}✓ Maintenance log: $MAINTENANCE_LOG${NC}" | tee -a "$MAINTENANCE_LOG"
echo "" | tee -a "$MAINTENANCE_LOG"

if [ -n "${ISSUE_PID:-}" ]; then
    echo -e "${YELLOW}⏳ Waiting for issue management to complete...${NC}" | tee -a "$MAINTENANCE_LOG"
    echo "   You can continue working. Check progress with:" | tee -a "$MAINTENANCE_LOG"
    echo "   tail -f $ISSUE_LOG" | tee -a "$MAINTENANCE_LOG"
    echo "" | tee -a "$MAINTENANCE_LOG"
fi

echo -e "${BLUE}Weekly maintenance tasks initiated successfully!${NC}" | tee -a "$MAINTENANCE_LOG"
echo "Full log: $MAINTENANCE_LOG"

# Optional: Wait for background task to complete
if [ "${WAIT_FOR_COMPLETION:-false}" = "true" ] && [ -n "${ISSUE_PID:-}" ]; then
    log "Waiting for issue management to complete..."
    wait $ISSUE_PID
    log "✓ Issue management complete"
fi

# 9b. Commit and push maintenance file changes (opt-in — off by default so an
# interactive run never surprises a developer with an unexpected commit; the
# Pi cron entry in cron/crontab.template sets AUTO_COMMIT_MAINTENANCE=true).
# Self-sufficient: waits for the background issue-update job itself, so it
# doesn't depend on WAIT_FOR_COMPLETION also being set.
if [ "${AUTO_COMMIT_MAINTENANCE:-false}" = "true" ]; then
    log_section "Committing Maintenance Changes"
    if [ -n "${ISSUE_PID:-}" ] && kill -0 "$ISSUE_PID" 2>/dev/null; then
        log "Waiting for issue management to finish before committing..."
        wait "$ISSUE_PID" 2>/dev/null || true
    fi
    if [ -n "$(git status --porcelain -- ISSUE_PRIORITIES.md "$WEEKLY_LOG" 2>/dev/null)" ]; then
        git add ISSUE_PRIORITIES.md "$WEEKLY_LOG"
        if git commit -m "chore: weekly maintenance sync $(date -u +%Y-%m-%d)" >>"$MAINTENANCE_LOG" 2>&1 && git push >>"$MAINTENANCE_LOG" 2>&1; then
            log "✓ Committed and pushed maintenance changes"
        else
            log "⚠️  Commit/push failed — see log"
        fi
    else
        log "✓ No maintenance file changes to commit"
    fi
fi

# 10. Send maintenance summary notification
log_section "Sending Maintenance Summary"
# grep -c exits 1 (not just nonzero output) when the count is zero, so
# `|| echo 0` would fire *in addition* to the "0" grep already printed,
# yielding "0\n0" and crashing send_maintenance_summary.py's int() parse.
SECURITY_VULNS=$(grep -c "security" "$MAINTENANCE_LOG" 2>/dev/null)
SECURITY_VULNS=${SECURITY_VULNS:-0}
ISSUES_CLOSED=$(gh issue list --state closed --search "closed:>=$(date -u -d '7 days ago' +%Y-%m-%d 2>/dev/null || date -u -v-7d +%Y-%m-%d 2>/dev/null || echo '2000-01-01')" --json number --jq 'length' 2>/dev/null || echo 0)
CACHE_SIZE=$(du -sm "$PROJECT_ROOT/cache" 2>/dev/null | cut -f1 || echo 0)

# send_maintenance_summary.py imports app modules (src/config_manager.py,
# src/ntfy_notifier.py) that bare host Python doesn't have installed — same
# reason the other cron jobs run via podman exec instead of host Python (#543).
# It lives under cron/ (not scripts/) specifically because that's the
# directory the Dockerfile COPYs into the image, so podman exec can reach it.
if command -v podman >/dev/null 2>&1 && podman container exists "$CONTAINER_NAME" 2>/dev/null; then
    podman exec "$CONTAINER_NAME" python cron/send_maintenance_summary.py "$SECURITY_VULNS" "$ISSUES_CLOSED" "$CACHE_SIZE" 2>>"$MAINTENANCE_LOG" || log "⚠️  Failed to send maintenance summary"
else
    log "⚠️  Container '$CONTAINER_NAME' not running — skipping maintenance summary notification"
fi

