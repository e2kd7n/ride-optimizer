#!/bin/bash

# Detect if output is being redirected to a file
# If so, disable colors to avoid ANSI codes in the file
if [ -t 1 ]; then
  # Output is to terminal, use colors
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  NC='\033[0m' # No Color
else
  # Output is redirected, no colors
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  NC=''
fi

# Function to log actions (to stderr so it doesn't pollute markdown output)
log_action() {
  echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1" >&2
}

log_success() {
  echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} ✅ $1" >&2
}

log_warning() {
  echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} ⚠️  $1" >&2
}

log_error() {
  echo -e "${RED}[$(date +%H:%M:%S)]${NC} ❌ $1" >&2
}

# Function to detect duplicate issues
detect_duplicate_issues() {
  log_action "Checking for duplicate issues..."
  
  local temp_file=$(mktemp)
  gh issue list --state open --json number,title,body --limit 200 > "$temp_file"
  
  # Find issues with similar titles (using fuzzy matching)
  local duplicates=$(jq -r '
    group_by(.title | ascii_downcase | gsub("[^a-z0-9 ]"; "")) |
    map(select(length > 1)) |
    .[] |
    "Potential duplicates: " + (map("#\(.number) - \(.title)") | join(" | "))
  ' "$temp_file")
  
  if [ -n "$duplicates" ]; then
    log_warning "Found potential duplicate issues:"
    echo "$duplicates" >&2
    echo "" >&2
  else
    log_success "No duplicate issues detected"
  fi
  
  rm -f "$temp_file"
}

# Function to auto-close completed issues based on documentation
auto_close_completed_issues() {
  log_action "Checking for completed issues that should be closed..."
  
  local closed_count=0
  
  # Check P1_ISSUES_COMPLETED.md for completed issues
  if [ -f "P1_ISSUES_COMPLETED.md" ]; then
    local completed_issues=$(grep -oE '#[0-9]+' P1_ISSUES_COMPLETED.md | sort -u | sed 's/#//')
    
    for issue_num in $completed_issues; do
      # Check if issue is still open
      local is_open=$(gh issue view "$issue_num" --json state --jq '.state' 2>/dev/null)
      
      if [ "$is_open" = "OPEN" ]; then
        log_action "Closing completed issue #$issue_num..."
        gh issue close "$issue_num" --comment "Auto-closed: Marked as completed in P1_ISSUES_COMPLETED.md" 2>/dev/null
        if [ $? -eq 0 ]; then
          ((closed_count++))
          log_success "Closed issue #$issue_num"
        fi
      fi
    done
  fi
  
  # Check for issues mentioned in completion/summary documents
  for doc in *_COMPLETE*.md *_SUMMARY.md *_IMPLEMENTATION_SUMMARY.md P0_*.md; do
    if [ -f "$doc" ]; then
      local doc_issues=$(grep -oE '#[0-9]+' "$doc" | sort -u | sed 's/#//')
      
      for issue_num in $doc_issues; do
        local is_open=$(gh issue view "$issue_num" --json state --jq '.state' 2>/dev/null)
        
        if [ "$is_open" = "OPEN" ]; then
          # Check if document indicates completion
          if grep -qi "complete\|implemented\|fixed\|resolved" "$doc"; then
            log_action "Issue #$issue_num mentioned in completion doc: $doc"
            echo "  Consider closing if work is complete" >&2
          fi
        fi
      done
    fi
  done
  
  if [ $closed_count -gt 0 ]; then
    log_success "Auto-closed $closed_count completed issues"
  else
    log_success "No issues needed auto-closing"
  fi
  echo "" >&2
}

# Enhanced function to check recent commits for completed work
check_commits_for_completed_work() {
  log_action "Checking recent commits for completed work..."
  
  local closed_count=0
  local temp_file=$(mktemp)
  local commit_details=$(mktemp)
  
  # Get last 50 commits with full messages (increased from 20)
  git log --format="%H|%s|%b" -50 --no-merges 2>/dev/null > "$commit_details"
  
  if [ ! -s "$commit_details" ]; then
    log_warning "No recent git history found"
    rm -f "$temp_file" "$commit_details"
    return
  fi
  
  # Extract all issue numbers from commits (subject + body)
  grep -oE '#[0-9]+' "$commit_details" | sort -u | sed 's/#//' > "$temp_file"
  
  if [ ! -s "$temp_file" ]; then
    log_success "No issue references found in recent commits"
    rm -f "$temp_file" "$commit_details"
    return
  fi
  
  # Check each referenced issue
  while read -r issue_num; do
    local is_open=$(gh issue view "$issue_num" --json state --jq '.state' 2>/dev/null)
    
    if [ "$is_open" = "OPEN" ]; then
      # Get all commits that mention this issue
      local issue_commits=$(grep "#$issue_num" "$commit_details")
      
      # Enhanced completion detection patterns
      local completion_patterns=(
        "fix.*#$issue_num"
        "close.*#$issue_num"
        "resolve.*#$issue_num"
        "complete.*#$issue_num"
        "implement.*#$issue_num"
        "#$issue_num.*fix"
        "#$issue_num.*close"
        "#$issue_num.*resolve"
        "#$issue_num.*complete"
        "#$issue_num.*implement"
        "Resolves #$issue_num"
        "Fixes #$issue_num"
        "Closes #$issue_num"
      )
      
      local should_close=false
      local matching_pattern=""
      
      # Check if any commit message matches completion patterns
      for pattern in "${completion_patterns[@]}"; do
        if echo "$issue_commits" | grep -qiE "$pattern"; then
          should_close=true
          matching_pattern="$pattern"
          break
        fi
      done
      
      # Additional check: if issue appears in commit with "feat:" or "fix:" prefix
      # and the commit body contains the issue number, it's likely resolved
      if echo "$issue_commits" | grep -qE "^[a-f0-9]+\|(feat|fix):.*#$issue_num"; then
        should_close=true
        matching_pattern="conventional commit with issue reference"
      fi
      
      if [ "$should_close" = true ]; then
        local commit_summary=$(echo "$issue_commits" | head -1 | cut -d'|' -f2 | cut -c1-80)
        log_action "Issue #$issue_num appears resolved (pattern: $matching_pattern)"
        
        if [ "$AUTO_CLOSE" = true ] && [ "$DRY_RUN" = false ]; then
          log_action "Auto-closing issue #$issue_num based on commit analysis"
          gh issue close "$issue_num" --comment "Auto-closed: Issue appears resolved in recent commits. Last relevant commit: $commit_summary" 2>/dev/null
          if [ $? -eq 0 ]; then
            ((closed_count++))
            log_success "Closed issue #$issue_num"
          fi
        else
          echo "  Would close #$issue_num (use --auto-close to enable)" >&2
          echo "  Commit: $commit_summary" >&2
        fi
      else
        # Issue mentioned but not with completion keywords - just log it
        local commit_summary=$(echo "$issue_commits" | head -1 | cut -d'|' -f2 | cut -c1-60)
        log_action "Issue #$issue_num mentioned in commits but not marked as resolved"
        echo "  Last mention: $commit_summary" >&2
      fi
    fi
  done < "$temp_file"
  
  rm -f "$temp_file" "$commit_details"
  
  if [ $closed_count -gt 0 ]; then
    log_success "Auto-closed $closed_count issues based on commits"
  fi
  echo "" >&2
}

# Function to suggest priority updates based on recent activity
suggest_priority_updates() {
  log_action "Analyzing recent development activity for priority updates..."
  
  # Get recently modified files
  local recent_files=$(git diff --name-only HEAD~10 HEAD 2>/dev/null | head -20)
  
  if [ -z "$recent_files" ]; then
    log_warning "No recent git history found"
    return
  fi
  
  # Check if critical files were modified
  local critical_modified=false
  echo "$recent_files" | grep -qE "(auth|security|database|migration)" && critical_modified=true
  
  if [ "$critical_modified" = true ]; then
    log_warning "Critical files modified recently - review P0/P1 issues for updates"
  fi
  
  # Check for test files
  local tests_modified=$(echo "$recent_files" | grep -c "test\|spec")
  if [ "$tests_modified" -gt 5 ]; then
    log_success "Significant test activity detected ($tests_modified test files)"
  fi
  
  echo "" >&2
}

# Function to create issues from TODO comments
create_issues_from_todos() {
  log_action "Checking for TODO comments that should become issues..."
  
  local created_count=0
  local temp_file=$(mktemp)
  
  # Find TODO comments with issue markers
  grep -rn --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" \
    --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=build \
    --exclude-dir=coverage --exclude-dir=.next --exclude-dir=test-results \
    -E "TODO.*#issue|FIXME.*#issue|TODO.*\[create-issue\]|FIXME.*\[create-issue\]" . 2>/dev/null > "$temp_file"
  
  if [ -s "$temp_file" ]; then
    log_warning "Found TODO comments marked for issue creation:"
    cat "$temp_file" >&2
    echo "" >&2
    echo "Run with --create-todos flag to automatically create these issues" >&2
  else
    log_success "No TODO comments marked for issue creation"
  fi
  
  rm -f "$temp_file"
  echo "" >&2
}

# Function to update issue labels based on keywords
update_issue_labels() {
  log_action "Checking for issues that need label updates..."
  
  local updated_count=0
  
  # Get all open issues
  local issues=$(gh issue list --state open --json number,title,body,labels --limit 100)
  
  # Check for security-related issues without security label
  echo "$issues" | jq -r '.[] | select(.title | test("security|vulnerability|auth|csrf|xss|sql"; "i")) | select(.labels | map(.name) | index("security") | not) | .number' | while read -r issue_num; do
    log_action "Adding 'security' label to issue #$issue_num"
    gh issue edit "$issue_num" --add-label "security" 2>/dev/null
    ((updated_count++))
  done
  
  # Check for bug issues without bug label
  echo "$issues" | jq -r '.[] | select(.title | test("bug|error|fail|broken"; "i")) | select(.labels | map(.name) | index("bug") | not) | .number' | while read -r issue_num; do
    log_action "Adding 'bug' label to issue #$issue_num"
    gh issue edit "$issue_num" --add-label "bug" 2>/dev/null
    ((updated_count++))
  done
  
  if [ $updated_count -gt 0 ]; then
    log_success "Updated labels on $updated_count issues"
  else
    log_success "All issue labels are up to date"
  fi
  echo "" >&2
}

# Function to scan for code TODOs and tasks
scan_workspace_todos() {
  echo "## 📝 Workspace TODOs & Tasks"
  echo "Code comments and inline tasks found in the workspace that may need attention."
  echo ""
  
  # Search for TODO, FIXME, HACK, XXX, NOTE comments in source files
  # Exclude node_modules, .git, dist, build, and other generated directories
  local todo_count=0
  local temp_file=$(mktemp)
  
  # Search patterns
  grep -rn --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" \
    --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=build \
    --exclude-dir=coverage --exclude-dir=.next --exclude-dir=test-results \
    -E "(TODO|FIXME|HACK|XXX|NOTE):" . 2>/dev/null | \
    sed 's/:/ - /' | \
    awk -F' - ' '{
      file=$1
      gsub(/^\.\//, "", file)
      rest=$2
      for(i=3; i<=NF; i++) rest = rest " - " $i
      print "- `" file "` - " rest
    }' > "$temp_file"
  
  todo_count=$(wc -l < "$temp_file" | tr -d ' ')
  
  if [ "$todo_count" -gt 0 ]; then
    echo "Found **$todo_count** code comments requiring attention:"
    echo ""
    cat "$temp_file"
  else
    echo "**No TODO/FIXME comments found in code** ✅"
  fi
  
  rm -f "$temp_file"
  echo ""
}

# Parse command line arguments
DRY_RUN=false
AUTO_CLOSE=false
DETECT_DUPLICATES=true
UPDATE_LABELS=true
ANALYZE_ACTIVITY=true

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --auto-close)
      AUTO_CLOSE=true
      shift
      ;;
    --no-duplicates)
      DETECT_DUPLICATES=false
      shift
      ;;
    --no-labels)
      UPDATE_LABELS=false
      shift
      ;;
    --no-analysis)
      ANALYZE_ACTIVITY=false
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry-run          Show what would be done without making changes"
      echo "  --auto-close       Automatically close completed issues"
      echo "  --no-duplicates    Skip duplicate detection"
      echo "  --no-labels        Skip automatic label updates"
      echo "  --no-analysis      Skip development activity analysis"
      echo "  --help             Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                           # Normal run with all checks"
      echo "  $0 --auto-close              # Auto-close completed issues"
      echo "  $0 --dry-run --auto-close    # Preview what would be closed"
      echo ""
      echo "Enhanced Features:"
      echo "  - Analyzes last 50 commits (up from 20)"
      echo "  - Detects conventional commit patterns (feat:, fix:)"
      echo "  - Recognizes 'Resolves #N', 'Fixes #N', 'Closes #N' patterns"
      echo "  - Checks both commit subject and body for issue references"
      echo "  - Scans completion documents (P0_*.md, *_COMPLETE*.md, etc.)"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Run intelligent issue management functions
echo "" >&2
log_action "🔍 Running Intelligent Issue Management..."
echo "" >&2

if [ "$DETECT_DUPLICATES" = true ]; then
  detect_duplicate_issues
fi

# Check recent commits for completed work (always run to show what would be closed)
check_commits_for_completed_work

if [ "$AUTO_CLOSE" = true ]; then
  if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN: Would auto-close completed issues"
  else
    auto_close_completed_issues
  fi
fi

if [ "$UPDATE_LABELS" = true ]; then
  if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN: Would update issue labels"
  else
    update_issue_labels
  fi
fi

if [ "$ANALYZE_ACTIVITY" = true ]; then
  suggest_priority_updates
fi

create_issues_from_todos

echo "" >&2
log_action "📊 Generating Issue Priority Report..."
echo "" >&2

# Main script - Generate markdown report
echo "# Issue Prioritization"
echo ""
# Generate timestamp with both UTC and US Central time
TIMESTAMP_UTC=$(date -u +"%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || date +"%Y-%m-%d %H:%M:%S")
TIMESTAMP_CENTRAL=$(TZ="America/Chicago" date +"%Y-%m-%d %H:%M:%S %Z" 2>/dev/null || date +"%Y-%m-%d %H:%M:%S")
echo "**Last Updated:** ${TIMESTAMP_UTC} / ${TIMESTAMP_CENTRAL}"
echo ""
echo "This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future)."
echo ""

echo "## 🔴 P0 - CRITICAL (Drop Everything)"
echo "Issues that make the application unusable or cause data loss."
echo ""
gh issue list --state open --label "P0-critical" --json number,title | jq -r '.[] | "- #\(.number) - \(.title)"'
if [ $(gh issue list --state open --label "P0-critical" --json number | jq '. | length') -eq 0 ]; then
  echo "**No P0 issues currently open** ✅"
fi
echo ""

echo "## 🔴 P1 - HIGH (Current Sprint)"
echo "Issues that significantly impact core functionality or user experience."
echo ""
gh issue list --state open --label "P1-high" --json number,title | jq -r '.[] | "- #\(.number) - \(.title)"'
if [ $(gh issue list --state open --label "P1-high" --json number | jq '. | length') -eq 0 ]; then
  echo "**No P1 issues currently open** ✅"
fi
echo ""

echo "## 🟡 P2 - MEDIUM (Next Sprint)"
echo "Important improvements that enhance functionality but don't block core workflows."
echo ""
gh issue list --state open --label "P2-medium" --json number,title | jq -r '.[] | "- #\(.number) - \(.title)"'
if [ $(gh issue list --state open --label "P2-medium" --json number | jq '. | length') -eq 0 ]; then
  echo "**No P2 issues currently open** ✅"
fi
echo ""

echo "## 🟢 P3 - LOW (Backlog)"
echo "Nice-to-have improvements and minor UX enhancements."
echo ""
gh issue list --state open --label "P3-low" --json number,title | jq -r '.[] | "- #\(.number) - \(.title)"'
if [ $(gh issue list --state open --label "P3-low" --json number | jq '. | length') -eq 0 ]; then
  echo "**No P3 issues currently open** ✅"
fi
echo ""

echo "## 📋 P4 - FUTURE ENHANCEMENTS"
echo "Feature requests and enhancements for future releases."
echo ""
gh issue list --state open --label "P4-future" --json number,title | jq -r '.[] | "- #\(.number) - \(.title)"'
if [ $(gh issue list --state open --label "P4-future" --json number | jq '. | length') -eq 0 ]; then
  echo "**No P4 issues currently open** ✅"
fi
echo ""

echo "## ⚠️ Unprioritized Issues"
echo "Issues without priority labels that need to be triaged."
echo ""
gh issue list --state open --json number,title,labels --limit 100 | jq -r '.[] | select(.labels | map(.name | startswith("P")) | any | not) | "- #\(.number) - \(.title)"'
unprioritized_count=$(gh issue list --state open --json number,labels --limit 100 | jq '[.[] | select(.labels | map(.name | startswith("P")) | any | not)] | length')
if [ "$unprioritized_count" -eq 0 ]; then
  echo "**No unprioritized issues** ✅"
fi
echo ""

# Scan workspace for TODOs
scan_workspace_todos

echo "## Priority Guidelines"
echo ""
echo "### P0 - CRITICAL"
echo "- Application is down or unusable"
echo "- Data loss or corruption"
echo "- Security vulnerabilities"
echo "- **Action:** Drop everything and fix immediately"
echo ""
echo "### P1 - HIGH"
echo "- Core features broken or severely degraded"
echo "- Significant user pain points"
echo "- Blocks important workflows"
echo "- **Action:** Fix in current sprint (1-2 weeks)"
echo ""
echo "### P2 - MEDIUM"
echo "- Feature improvements"
echo "- Moderate user pain points"
echo "- Quality of life enhancements"
echo "- **Action:** Plan for next sprint (2-4 weeks)"
echo ""
echo "### P3 - LOW"
echo "- Minor UX improvements"
echo "- Edge cases"
echo "- Nice-to-have features"
echo "- **Action:** Backlog, address when time permits"
echo ""
echo "### P4 - FUTURE"
echo "- New features"
echo "- Major enhancements"
echo "- Long-term improvements"
echo "- **Action:** Plan for future releases"
echo ""
echo "## How to Update Priorities"
echo ""
echo "1. Use GitHub labels to set priority (P0-critical, P1-high, P2-medium, P3-low, P4-future)"
echo "2. Run \`./scripts/update-issue-priorities.sh\` to regenerate this file"
echo "3. Commit changes with descriptive message"
echo "4. Communicate priority changes to team"
echo ""
echo "## Managing Workspace TODOs"
echo ""
echo "- Review code comments regularly and convert important ones to GitHub issues"
echo "- Use \`TODO:\` for tasks that should become issues"
echo "- Use \`FIXME:\` for bugs that need attention"
echo "- Use \`HACK:\` for temporary solutions that need proper fixes"
echo "- Use \`NOTE:\` for important information or context"

# Made with Bob
