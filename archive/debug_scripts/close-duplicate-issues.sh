#!/bin/bash

# Script to close duplicate issues, keeping the lowest numbered one

echo "Finding and closing duplicate issues..."

# Get all open issues
gh issue list --state open --json number,title --limit 100 > /tmp/issues.json

# Find duplicates and close higher numbered ones
cat /tmp/issues.json | jq -r '.[] | "\(.title)|\(.number)"' | sort | \
awk -F'|' '{
  if (titles[$1]) {
    # This is a duplicate, store for closing
    duplicates[++dup_count] = $2 "|" $1 "|" titles[$1]
  } else {
    # First occurrence, remember it
    titles[$1] = $2
  }
}
END {
  for (i=1; i<=dup_count; i++) {
    split(duplicates[i], parts, "|")
    print parts[1] "|" parts[2] "|" parts[3]
  }
}' | while IFS='|' read -r dup_number title keep_number; do
  echo "Closing #$dup_number (duplicate of #$keep_number): $title"
  gh issue close "$dup_number" --reason "not planned" --comment "Duplicate of #$keep_number"
done

echo "Done!"

# Made with Bob
