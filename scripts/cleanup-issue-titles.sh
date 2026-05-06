#!/bin/bash

# Script to remove priority prefixes from issue titles
# Priority should be indicated by labels, not title prefixes

echo "Cleaning up issue titles..."

# Get all open issues and clean up various priority prefix patterns
gh issue list --state open --json number,title --limit 100 | \
jq -r '.[] | "\(.number)|\(.title)"' | \
while IFS='|' read -r number title; do
  # Remove various priority prefix patterns:
  # [P#] prefix (e.g., "[P2] Title")
  # P#: prefix (e.g., "P2: Title")
  new_title=$(echo "$title" | sed -E 's/^(\[P[0-4]\] |P[0-4]: )//')
  
  if [ "$title" != "$new_title" ]; then
    echo "Issue #$number: '$title' -> '$new_title'"
    gh issue edit "$number" --title "$new_title"
  fi
done

echo "Done!"

# Made with Bob
