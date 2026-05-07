#!/bin/bash

# verify-issue-closures.sh
# Verify all issues referenced in recent commits are properly closed
# This script helps prevent the issue closure breakdown that occurred with #228-234

# Colors for output
if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  NC='\033[0m'
else
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  NC=''
fi

# Logging functions
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

# Parse command line arguments
COMMIT_COUNT=10
AUTO_CLOSE=false
CHECK_COMPLETION_DOCS=true

while [[ $# -gt 0 ]]; do
  case $1 in
    --commits)
      COMMIT_COUNT="$2"
      shift 2
      ;;
    --auto-close)
      AUTO_CLOSE=true
      shift
      ;;
    --no-docs)
      CHECK_COMPLETION_DOCS=false
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Verify all issues referenced in recent commits are properly closed."
      echo ""
      echo "Options:"
      echo "  --commits N        Check last N commits (default: 10)"
      echo "  --auto-close       Automatically close issues that appear complete"
      echo "  --no-docs          Skip checking completion documentation"
      echo "  --help             Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                      # Check last 10 commits"
      echo "  $0 --commits 20         # Check last 20 commits"
      echo "  $0 --auto-close         # Auto-close completed issues"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo ""
log_action "🔍 Verifying Issue Closures..."
echo ""

# Get issues from recent commits
log_action "Scanning last $COMMIT_COUNT commits for issue references..."
RECENT_ISSUES=$(git log -${COMMIT_COUNT} --format="%s %b" 2>/dev/null | grep -oE '#[0-9]+' | sort -u)

if [ -z "$RECENT_ISSUES" ]; then
  log_success "No issue references found in recent commits"
  exit 0
fi

# Check completion documentation if enabled
COMPLETION_DOC_ISSUES=""
if [ "$CHECK_COMPLETION_DOCS" = true ] && [ -d "docs/archive/completed_work" ]; then
  log_action "Scanning completion reports for resolved issues..."
  COMPLETION_DOC_ISSUES=$(find docs/archive/completed_work -type f \( -name "*COMPLETE*.md" -o -name "*COMPLETION*.md" -o -name "*RESOLVED*.md" \) 2>/dev/null | \
    xargs grep -hE "(✅|COMPLETE|CLOSED).*#[0-9]+|#[0-9]+.*(✅|COMPLETE|CLOSED)" 2>/dev/null | \
    grep -oE '#[0-9]+' | sort -u)
fi

# Combine issues from commits and completion docs
ALL_ISSUES=$(echo -e "$RECENT_ISSUES\n$COMPLETION_DOC_ISSUES" | sort -u | grep -v '^$')

# Track statistics
OPEN_COUNT=0
CLOSED_COUNT=0
SHOULD_CLOSE_COUNT=0

# Check each issue
for issue in $ALL_ISSUES; do
  issue_num=${issue#\#}
  
  # Get issue status
  status=$(gh issue view $issue_num --json state --jq '.state' 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    log_warning "Issue #$issue_num not found (may have been deleted)"
    continue
  fi
  
  if [ "$status" = "OPEN" ]; then
    ((OPEN_COUNT++))
    
    # Check if issue appears in completion docs
    in_completion_doc=false
    if echo "$COMPLETION_DOC_ISSUES" | grep -q "#$issue_num"; then
      in_completion_doc=true
    fi
    
    # Get commit messages mentioning this issue
    commit_messages=$(git log -${COMMIT_COUNT} --format="%s %b" 2>/dev/null | grep "#$issue_num")
    
    # Check for completion patterns
    completion_patterns=(
      "fix.*#$issue_num"
      "close.*#$issue_num"
      "resolve.*#$issue_num"
      "complete.*#$issue_num"
      "implement.*#$issue_num"
      "Fixes #$issue_num"
      "Closes #$issue_num"
      "Resolves #$issue_num"
      "Completes #$issue_num"
    )
    
    should_close=false
    matching_pattern=""
    
    for pattern in "${completion_patterns[@]}"; do
      if echo "$commit_messages" | grep -qiE "$pattern"; then
        should_close=true
        matching_pattern="$pattern"
        break
      fi
    done
    
    # If in completion doc, definitely should close
    if [ "$in_completion_doc" = true ]; then
      should_close=true
      matching_pattern="found in completion documentation"
    fi
    
    if [ "$should_close" = true ]; then
      ((SHOULD_CLOSE_COUNT++))
      log_warning "Issue #$issue_num is OPEN but appears complete"
      echo "   Pattern: $matching_pattern" >&2
      
      if [ "$AUTO_CLOSE" = true ]; then
        log_action "Auto-closing issue #$issue_num..."
        close_comment="Auto-closed: Issue appears resolved"
        if [ "$in_completion_doc" = true ]; then
          close_comment="$close_comment (found in completion documentation)"
        else
          close_comment="$close_comment in recent commits"
        fi
        
        gh issue close "$issue_num" --comment "$close_comment" 2>/dev/null
        if [ $? -eq 0 ]; then
          log_success "Closed issue #$issue_num"
        else
          log_error "Failed to close issue #$issue_num"
        fi
      else
        echo "   Run with --auto-close to close automatically" >&2
        echo "   Or close manually: gh issue close $issue_num --comment \"[your comment]\"" >&2
      fi
      echo "" >&2
    else
      log_action "Issue #$issue_num is OPEN (mentioned in commits but not marked complete)"
      echo "   Review and close if work is complete" >&2
      echo "" >&2
    fi
  else
    ((CLOSED_COUNT++))
  fi
done

# Summary
echo ""
log_action "📊 Summary:"
echo "   Total issues referenced: $(echo "$ALL_ISSUES" | wc -l | tr -d ' ')" >&2
echo "   Already closed: $CLOSED_COUNT" >&2
echo "   Still open: $OPEN_COUNT" >&2
echo "   Should be closed: $SHOULD_CLOSE_COUNT" >&2
echo ""

if [ $SHOULD_CLOSE_COUNT -gt 0 ]; then
  if [ "$AUTO_CLOSE" = false ]; then
    log_warning "Found $SHOULD_CLOSE_COUNT issues that should be closed"
    echo "Run with --auto-close to close them automatically" >&2
    echo "Or close manually with detailed completion comments" >&2
    exit 1
  else
    log_success "Processed $SHOULD_CLOSE_COUNT issues"
  fi
else
  log_success "All referenced issues are properly closed"
fi

echo ""

# Made with Bob
