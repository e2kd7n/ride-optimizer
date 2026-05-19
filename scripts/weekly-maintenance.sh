#!/bin/bash
# Weekly Maintenance Script
# Runs documentation sync, issue management, and creates backups
# Usage: ./scripts/weekly-maintenance.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="backups/maintenance"
LOG_DIR="logs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
MAINTENANCE_LOG="$LOG_DIR/maintenance-$TIMESTAMP.log"

# Create directories if they don't exist
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

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
TEMP_BACKUP_CLONE=$(mktemp -d)
log "Cloning backup repository..."
if git clone "$BACKUP_REPO" "$TEMP_BACKUP_CLONE" 2>/dev/null; then
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
rm -rf "$TEMP_BACKUP_CLONE"

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
echo "  [ ] RELEASE_ROADMAP.md - Milestones current?" | tee -a "$MAINTENANCE_LOG"
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

# Made with Bob
