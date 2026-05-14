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

# Function to sanitize comments for gh issue close
# Escapes backticks to prevent shell command substitution
sanitize_comment() {
  echo "$1" | sed 's/`/\\`/g'
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
        gh issue close "$issue_num" --comment "$(sanitize_comment "Auto-closed: Marked as completed in P1_ISSUES_COMPLETED.md")" 2>/dev/null
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
  local SHOULD_CLOSE_COUNT=0
  local temp_file=$(mktemp)
  local commit_details=$(mktemp)
  local completion_docs=$(mktemp)
  
  # Get last 50 commits with full messages (increased from 20)
  git log --format="%H|%s|%b" -50 --no-merges 2>/dev/null > "$commit_details"
  
  if [ ! -s "$commit_details" ]; then
    log_warning "No recent git history found"
    rm -f "$temp_file" "$commit_details" "$completion_docs"
    return
  fi
  
  # ENHANCEMENT 1: Check completion reports in docs/archive/completed_work/
  if [ -d "docs/archive/completed_work" ]; then
    log_action "Scanning completion reports for resolved issues..."
    # Only look at files with COMPLETE, COMPLETION, or RESOLVED in the name
    find docs/archive/completed_work -type f -name "*COMPLETE*.md" -o -name "*COMPLETION*.md" -o -name "*RESOLVED*.md" 2>/dev/null | while read -r doc; do
      # Only extract issues if the document explicitly marks them as complete
      # Look for patterns like "✅ Issue #123" or "Issue #123: COMPLETE"
      grep -E "(✅|COMPLETE|CLOSED).*#[0-9]+|#[0-9]+.*(✅|COMPLETE|CLOSED)" "$doc" | grep -oE '#[0-9]+' | sed 's/#//' | sort -u >> "$completion_docs"
    done
  fi
  
  # Extract all issue numbers from commits (subject + body)
  grep -oE '#[0-9]+' "$commit_details" | sort -u | sed 's/#//' > "$temp_file"
  
  # Add issues from completion docs
  if [ -s "$completion_docs" ]; then
    cat "$completion_docs" | sort -u >> "$temp_file"
    sort -u "$temp_file" -o "$temp_file"
  fi
  
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
      
      # ENHANCEMENT 2: Check if issue is mentioned in completion reports
      local in_completion_doc=false
      if [ -s "$completion_docs" ]; then
        if grep -q "^$issue_num$" "$completion_docs"; then
          in_completion_doc=true
          log_action "Issue #$issue_num found in completion documentation"
        fi
      fi
      
      # Enhanced completion detection patterns
      local completion_patterns=(
        "fix.*#$issue_num"
        "close.*#$issue_num"
        "resolve.*#$issue_num"
        "complete.*#$issue_num"
        "implement.*#$issue_num"
        "finish.*#$issue_num"
        "done.*#$issue_num"
        "#$issue_num.*fix"
        "#$issue_num.*close"
        "#$issue_num.*resolve"
        "#$issue_num.*complete"
        "#$issue_num.*implement"
        "#$issue_num.*finish"
        "#$issue_num.*done"
        "Resolves #$issue_num"
        "Fixes #$issue_num"
        "Closes #$issue_num"
        "Completes #$issue_num"
        "Implements #$issue_num"
        "Phase.*complete.*#$issue_num"
        "Issue #$issue_num.*complete"
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
      
      # ENHANCEMENT 3: If issue is in completion docs, mark it for closure
      if [ "$in_completion_doc" = true ]; then
        should_close=true
        matching_pattern="found in completion documentation"
      fi
      
      if [ "$should_close" = true ]; then
        ((SHOULD_CLOSE_COUNT++))
        local commit_summary=$(echo "$issue_commits" | head -1 | cut -d'|' -f2 | cut -c1-80)
        log_action "Issue #$issue_num appears resolved (pattern: $matching_pattern)"
        
        if [ "$AUTO_CLOSE" = true ] && [ "$DRY_RUN" = false ]; then
          local close_comment="Auto-closed: Issue appears resolved"
          if [ "$in_completion_doc" = true ]; then
            close_comment="$close_comment (found in completion documentation)"
          else
            close_comment="$close_comment in recent commits. Last relevant commit: $commit_summary"
          fi
          
          log_action "Auto-closing issue #$issue_num based on analysis"
          gh issue close "$issue_num" --comment "$(sanitize_comment "$close_comment")" 2>/dev/null
          if [ $? -eq 0 ]; then
            ((closed_count++))
            log_success "Closed issue #$issue_num"
          fi
        else
          echo "  Would close #$issue_num (use --auto-close to enable)" >&2
          if [ "$in_completion_doc" = true ]; then
            echo "  Reason: Found in completion documentation" >&2
          else
            echo "  Commit: $commit_summary" >&2
          fi
        fi
      else
        # Issue mentioned but not with completion keywords - just log it
        local commit_summary=$(echo "$issue_commits" | head -1 | cut -d'|' -f2 | cut -c1-60)
        log_action "Issue #$issue_num mentioned in commits but not marked as resolved"
        echo "  Last mention: $commit_summary" >&2
      fi
    fi
  done < "$temp_file"
  
  rm -f "$temp_file" "$commit_details" "$completion_docs"
  
  if [ $closed_count -gt 0 ]; then
    log_success "Auto-closed $closed_count issues based on analysis"
  fi
  
  # ENHANCEMENT: Prompt for immediate action if issues found but not auto-closed
  if [ "$AUTO_CLOSE" = false ] && [ $SHOULD_CLOSE_COUNT -gt 0 ]; then
    echo "" >&2
    log_warning "Found $SHOULD_CLOSE_COUNT issues that appear complete but are still open"
    echo "Run with --auto-close to close them automatically" >&2
    echo "Or close manually with detailed completion comments" >&2
    echo "" >&2
    echo "Example closure command:" >&2
    echo "  gh issue close <issue_num> --comment \"Completed in commit <hash> - <description>\"" >&2
    echo "" >&2
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
echo "This file reflects the current state of GitHub issues organized by release milestone and priority within each release."
echo ""
echo "**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases."
echo ""

# Get current release from RELEASE_ROADMAP.md
CURRENT_RELEASE=$(grep -A 1 "^\*\*Current Release:\*\*" RELEASE_ROADMAP.md 2>/dev/null | tail -1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
NEXT_RELEASE=$(grep -A 1 "^\*\*Next Release:\*\*" RELEASE_ROADMAP.md 2>/dev/null | tail -1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)

if [ -z "$CURRENT_RELEASE" ]; then
  CURRENT_RELEASE="v0.10.0"
fi
if [ -z "$NEXT_RELEASE" ]; then
  NEXT_RELEASE="v0.11.0"
fi

log_action "Current Release: $CURRENT_RELEASE, Next Release: $NEXT_RELEASE" >&2

# Function to display issues for a milestone and priority
display_milestone_priority() {
  local milestone="$1"
  local priority_label="$2"
  local priority_name="$3"
  
  local issues=$(gh issue list --state open --milestone "$milestone" --label "$priority_label" --json number,title 2>/dev/null | jq -r '.[] | "- #\(.number) - \(.title)"')
  
  if [ -n "$issues" ]; then
    echo "$issues"
  fi
}

# Function to get issue count for milestone and priority
get_issue_count() {
  local milestone="$1"
  local priority_label="$2"
  
  gh issue list --state open --milestone "$milestone" --label "$priority_label" --json number 2>/dev/null | jq '. | length'
}

# Get all unique milestones, sorted by version number
MILESTONES=$(gh issue list --state open --json milestone --limit 200 2>/dev/null | jq -r '.[].milestone.title // empty' | sort -u -V)

# Separate milestones into next and future
# The FIRST milestone (lowest version) is the "next release"
# All others are "future releases"
NEXT_MILESTONE=""
FUTURE_MILESTONES=""

first_milestone=true
for milestone in $MILESTONES; do
  if [ "$first_milestone" = true ]; then
    NEXT_MILESTONE="$milestone"
    first_milestone=false
  else
    FUTURE_MILESTONES="$FUTURE_MILESTONES $milestone"
  fi
done

# Update NEXT_RELEASE to match actual next milestone
if [ -n "$NEXT_MILESTONE" ]; then
  NEXT_RELEASE="$NEXT_MILESTONE"
fi

echo "## 📍 Release Context"
echo ""
echo "- **Current Release:** $CURRENT_RELEASE (deployed)"
echo "- **Next Release:** $NEXT_RELEASE (in development)"
echo "- **Future Releases:** $(echo $FUTURE_MILESTONES | tr ' ' ', ' | sed 's/,$//')"
echo ""
echo "---"
echo ""

# Display issues for NEXT RELEASE (highest priority)
if [ -n "$NEXT_MILESTONE" ]; then
  echo "## 🎯 $NEXT_MILESTONE (Next Release - IN DEVELOPMENT)"
  echo ""
  echo "**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**"
  echo ""
  
  # P0 for next release
  echo "### 🔴 P0 - CRITICAL"
  p0_count=$(get_issue_count "$NEXT_MILESTONE" "P0-critical")
  if [ "$p0_count" -gt 0 ]; then
    display_milestone_priority "$NEXT_MILESTONE" "P0-critical" "P0"
  else
    echo "**No P0 issues** ✅"
  fi
  echo ""
  
  # P1 for next release
  echo "### 🔴 P1 - HIGH"
  p1_count=$(get_issue_count "$NEXT_MILESTONE" "P1-high")
  if [ "$p1_count" -gt 0 ]; then
    display_milestone_priority "$NEXT_MILESTONE" "P1-high" "P1"
  else
    echo "**No P1 issues** ✅"
  fi
  echo ""
  
  # P2 for next release
  echo "### 🟡 P2 - MEDIUM"
  p2_count=$(get_issue_count "$NEXT_MILESTONE" "P2-medium")
  if [ "$p2_count" -gt 0 ]; then
    display_milestone_priority "$NEXT_MILESTONE" "P2-medium" "P2"
  else
    echo "**No P2 issues** ✅"
  fi
  echo ""
  
  # P3 for next release
  echo "### 🟢 P3 - LOW"
  p3_count=$(get_issue_count "$NEXT_MILESTONE" "P3-low")
  if [ "$p3_count" -gt 0 ]; then
    display_milestone_priority "$NEXT_MILESTONE" "P3-low" "P3"
  else
    echo "**No P3 issues** ✅"
  fi
  echo ""
  
  # P4 for next release
  echo "### 📋 P4 - FUTURE"
  p4_count=$(get_issue_count "$NEXT_MILESTONE" "P4-future")
  if [ "$p4_count" -gt 0 ]; then
    display_milestone_priority "$NEXT_MILESTONE" "P4-future" "P4"
  else
    echo "**No P4 issues** ✅"
  fi
  echo ""
  
  echo "---"
  echo ""
fi

# Display issues for FUTURE RELEASES
for milestone in $FUTURE_MILESTONES; do
  echo "## 📅 $milestone (Future Release)"
  echo ""
  
  # Get all issues for this milestone grouped by priority
  all_issues=$(gh issue list --state open --milestone "$milestone" --json number,title,labels 2>/dev/null)
  
  if [ -z "$all_issues" ] || [ "$all_issues" = "[]" ]; then
    echo "**No issues planned for this release yet**"
    echo ""
    echo "---"
    echo ""
    continue
  fi
  
  # P0
  p0_issues=$(echo "$all_issues" | jq -r '.[] | select(.labels | map(.name) | index("P0-critical")) | "- #\(.number) - \(.title)"')
  if [ -n "$p0_issues" ]; then
    echo "### 🔴 P0 - CRITICAL"
    echo "$p0_issues"
    echo ""
  fi
  
  # P1
  p1_issues=$(echo "$all_issues" | jq -r '.[] | select(.labels | map(.name) | index("P1-high")) | "- #\(.number) - \(.title)"')
  if [ -n "$p1_issues" ]; then
    echo "### 🔴 P1 - HIGH"
    echo "$p1_issues"
    echo ""
  fi
  
  # P2
  p2_issues=$(echo "$all_issues" | jq -r '.[] | select(.labels | map(.name) | index("P2-medium")) | "- #\(.number) - \(.title)"')
  if [ -n "$p2_issues" ]; then
    echo "### 🟡 P2 - MEDIUM"
    echo "$p2_issues"
    echo ""
  fi
  
  # P3
  p3_issues=$(echo "$all_issues" | jq -r '.[] | select(.labels | map(.name) | index("P3-low")) | "- #\(.number) - \(.title)"')
  if [ -n "$p3_issues" ]; then
    echo "### 🟢 P3 - LOW"
    echo "$p3_issues"
    echo ""
  fi
  
  # P4
  p4_issues=$(echo "$all_issues" | jq -r '.[] | select(.labels | map(.name) | index("P4-future")) | "- #\(.number) - \(.title)"')
  if [ -n "$p4_issues" ]; then
    echo "### 📋 P4 - FUTURE"
    echo "$p4_issues"
    echo ""
  fi
  
  echo "---"
  echo ""
done

# Display issues WITHOUT milestone (need triage)
echo "## ⚠️ Issues Without Release Assignment"
echo ""
echo "These issues need to be assigned to a release milestone and prioritized."
echo ""

no_milestone_issues=$(gh issue list --state open --json number,title,labels,milestone --limit 200 2>/dev/null | jq -r '.[] | select(.milestone == null)')

if [ -z "$no_milestone_issues" ] || [ "$no_milestone_issues" = "" ]; then
  echo "**All issues are assigned to releases** ✅"
  echo ""
else
  # Group by priority
  echo "### 🔴 P0 - CRITICAL"
  p0_no_milestone=$(echo "$no_milestone_issues" | jq -r 'select(.labels | map(.name) | index("P0-critical")) | "- #\(.number) - \(.title)"')
  if [ -n "$p0_no_milestone" ]; then
    echo "$p0_no_milestone"
  else
    echo "None"
  fi
  echo ""
  
  echo "### 🔴 P1 - HIGH"
  p1_no_milestone=$(echo "$no_milestone_issues" | jq -r 'select(.labels | map(.name) | index("P1-high")) | "- #\(.number) - \(.title)"')
  if [ -n "$p1_no_milestone" ]; then
    echo "$p1_no_milestone"
  else
    echo "None"
  fi
  echo ""
  
  echo "### 🟡 P2 - MEDIUM"
  p2_no_milestone=$(echo "$no_milestone_issues" | jq -r 'select(.labels | map(.name) | index("P2-medium")) | "- #\(.number) - \(.title)"')
  if [ -n "$p2_no_milestone" ]; then
    echo "$p2_no_milestone"
  else
    echo "None"
  fi
  echo ""
  
  echo "### 🟢 P3 - LOW"
  p3_no_milestone=$(echo "$no_milestone_issues" | jq -r 'select(.labels | map(.name) | index("P3-low")) | "- #\(.number) - \(.title)"')
  if [ -n "$p3_no_milestone" ]; then
    echo "$p3_no_milestone"
  else
    echo "None"
  fi
  echo ""
  
  echo "### 📋 P4 - FUTURE"
  p4_no_milestone=$(echo "$no_milestone_issues" | jq -r 'select(.labels | map(.name) | index("P4-future")) | "- #\(.number) - \(.title)"')
  if [ -n "$p4_no_milestone" ]; then
    echo "$p4_no_milestone"
  else
    echo "None"
  fi
  echo ""
  
  echo "### ⚠️ Unprioritized (No P-label)"
  unprioritized=$(echo "$no_milestone_issues" | jq -r 'select(.labels | map(.name | startswith("P")) | any | not) | "- #\(.number) - \(.title)"')
  if [ -n "$unprioritized" ]; then
    echo "$unprioritized"
  else
    echo "None"
  fi
  echo ""
fi

echo "---"
echo ""

# Scan workspace for TODOs
scan_workspace_todos

echo "## 📖 Priority System (Release-Aware)"
echo ""
echo "**Key Principle:** Priority is now WITHIN a release. A P1 issue in the next release takes precedence over a P0 issue in a future release."
echo ""
echo "### Work Order Priority"
echo ""
echo "1. **Next Release P0** - Drop everything"
echo "2. **Next Release P1** - Current sprint focus"
echo "3. **Next Release P2** - Next sprint planning"
echo "4. **Next Release P3** - Backlog for this release"
echo "5. **Future Release P0** - Plan for future critical work"
echo "6. **Future Release P1+** - Long-term planning"
echo ""
echo "### Priority Definitions (Within a Release)"
echo ""
echo "#### 🔴 P0 - CRITICAL"
echo "- Application is down or unusable"
echo "- Data loss or corruption"
echo "- Security vulnerabilities"
echo "- Blocks release deployment"
echo "- **Action:** Drop everything and fix immediately"
echo ""
echo "#### 🔴 P1 - HIGH"
echo "- Core features broken or severely degraded"
echo "- Significant user pain points"
echo "- Blocks important workflows"
echo "- Must complete before release"
echo "- **Action:** Fix in current sprint (1-2 weeks)"
echo ""
echo "#### 🟡 P2 - MEDIUM"
echo "- Feature improvements"
echo "- Moderate user pain points"
echo "- Quality of life enhancements"
echo "- Should complete for release"
echo "- **Action:** Plan for next sprint (2-4 weeks)"
echo ""
echo "#### 🟢 P3 - LOW"
echo "- Minor UX improvements"
echo "- Edge cases"
echo "- Nice-to-have features"
echo "- Can defer to next release if needed"
echo "- **Action:** Backlog, address when time permits"
echo ""
echo "#### 📋 P4 - FUTURE"
echo "- New features for later releases"
echo "- Major enhancements"
echo "- Long-term improvements"
echo "- Explicitly deferred"
echo "- **Action:** Plan for future releases"
echo ""
echo "## 🔄 How to Update Priorities"
echo ""
echo "### 1. Assign to Release Milestone"
echo "\`\`\`bash"
echo "gh issue edit <issue_num> --milestone \"v0.13.0\""
echo "\`\`\`"
echo ""
echo "### 2. Set Priority Within Release"
echo "\`\`\`bash"
echo "gh issue edit <issue_num> --add-label \"P1-high\""
echo "\`\`\`"
echo ""
echo "### 3. Regenerate This File"
echo "\`\`\`bash"
echo "./scripts/update-issue-priorities.sh"
echo "\`\`\`"
echo ""
echo "### 4. Commit and Communicate"
echo "\`\`\`bash"
echo "git add ISSUE_PRIORITIES.md"
echo "git commit -m \"Update issue priorities for <release>\""
echo "\`\`\`"
echo ""
echo "## 📝 Managing Workspace TODOs"
echo ""
echo "- Review code comments regularly and convert important ones to GitHub issues"
echo "- Use \`TODO:\` for tasks that should become issues"
echo "- Use \`FIXME:\` for bugs that need attention"
echo "- Use \`HACK:\` for temporary solutions that need proper fixes"
echo "- Use \`NOTE:\` for important information or context"
echo ""
echo "## 🎯 Release Planning Guidelines"
echo ""
echo "- **Assign milestones early** - Every issue should have a target release"
echo "- **Prioritize within release** - Focus on P0/P1 issues for next release first"
echo "- **Defer strategically** - Move P3/P4 issues to future releases if needed"
echo "- **Review regularly** - Run this script weekly to track progress"

# Made with Bob
