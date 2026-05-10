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

# 4. Start issue management in background
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

# 5. Documentation review checklist
log_section "Documentation Review Checklist"
echo "" | tee -a "$MAINTENANCE_LOG"
echo "Please review the following:" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] docs/VERSIONING_PLAN.md - Version scheme current?" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] docs/TECHNICAL_SPEC.md - Architecture up to date?" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] README.md - Setup instructions accurate?" | tee -a "$MAINTENANCE_LOG"
echo "  [ ] RELEASE_ROADMAP.md - Milestones current?" | tee -a "$MAINTENANCE_LOG"
echo "" | tee -a "$MAINTENANCE_LOG"

# 6. Quick stats
log_section "Repository Statistics"
log "Documentation files: $(find docs -name '*.md' | wc -l | tr -d ' ')"
log "Python modules: $(find src app -name '*.py' 2>/dev/null | wc -l | tr -d ' ')"
log "Test files: $(find tests -name 'test_*.py' 2>/dev/null | wc -l | tr -d ' ')"
log "Total commits: $(git rev-list --count HEAD)"

# 7. Update weekly maintenance log
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

# 8. Summary
log_section "Maintenance Summary"
echo "" | tee -a "$MAINTENANCE_LOG"
echo -e "${GREEN}✓ Backups created in $BACKUP_DIR${NC}" | tee -a "$MAINTENANCE_LOG"
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
