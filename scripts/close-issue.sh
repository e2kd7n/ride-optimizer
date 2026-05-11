#!/bin/bash
# Helper script to close GitHub issues with properly formatted comments
# Usage: ./scripts/close-issue.sh <issue_number> <comment_file>
#   or:  ./scripts/close-issue.sh <issue_number> (reads from stdin)

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <issue_number> [comment_file]"
    echo "  If comment_file is not provided, reads from stdin"
    exit 1
fi

ISSUE_NUMBER="$1"
COMMENT_FILE="${2:-}"

# If comment file is provided, use it; otherwise read from stdin
if [ -n "$COMMENT_FILE" ]; then
    if [ ! -f "$COMMENT_FILE" ]; then
        echo "Error: Comment file '$COMMENT_FILE' not found"
        exit 1
    fi
    COMMENT=$(cat "$COMMENT_FILE")
else
    # Read from stdin
    COMMENT=$(cat)
fi

# Close the issue with the comment using gh CLI
# The --comment flag properly handles multiline strings and special characters
gh issue close "$ISSUE_NUMBER" --comment "$COMMENT"

echo "✓ Successfully closed issue #$ISSUE_NUMBER"

# Made with Bob
