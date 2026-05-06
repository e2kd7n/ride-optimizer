#!/bin/bash

# Script to align GitHub labels across ride-optimizer and mealplanner projects
# Ensures consistent labeling system

set -e

echo "🏷️  Aligning GitHub Labels Across Projects"
echo "=========================================="
echo ""

# Core labels that should exist in both projects
CORE_LABELS=(
  "bug:Something isn't working:#d73a4a"
  "documentation:Improvements or additions to documentation:#0075ca"
  "duplicate:This issue or pull request already exists:#cfd3d7"
  "enhancement:New feature or request:#a2eeef"
  "good first issue:Good for newcomers:#7057ff"
  "help wanted:Extra attention is needed:#008672"
  "invalid:This doesn't seem right:#e4e669"
  "question:Further information is requested:#d876e3"
  "wontfix:This will not be worked on:#ffffff"
)

# Priority labels (P0-P4)
PRIORITY_LABELS=(
  "P0-critical:Critical priority - immediate attention:#B60205"
  "P1-high:High priority - next sprint:#D93F0B"
  "P2-medium:Medium priority - backlog:#FBCA04"
  "P3-low:Low priority - nice to have:#0E8A16"
  "P4-future:Future consideration:#C5DEF5"
)

# Category labels
CATEGORY_LABELS=(
  "architecture:Architecture and infrastructure changes:#0E8A16"
  "performance:Performance improvements:#FBCA04"
  "testing:Testing and QA:#D4C5F9"
  "security:Security vulnerabilities and hardening:#B60205"
  "accessibility:Accessibility improvements:#D93F0B"
  "backend:Backend changes:#1D76DB"
  "frontend:Frontend changes:#1D76DB"
  "design:Design and UI:#0E8A16"
  "ux:User experience improvements:#FBCA04"
)

# Infrastructure labels
INFRA_LABELS=(
  "deployment:Deployment and DevOps:#1D76DB"
  "docker:Docker and containerization:#0052cc"
  "ci/cd:Continuous Integration/Continuous Deployment:#1d76db"
  "infrastructure:Infrastructure and system resources:#5319e7"
  "raspberry-pi:Raspberry Pi specific:#D93F0B"
)

# Special labels
SPECIAL_LABELS=(
  "blocking-launch:Cannot launch without fixing this:#B60205"
  "quick-win:Quick win - high impact, low effort:#0E8A16"
  "data-loss-prevention:Prevents user data loss:#B60205"
)

# Function to create or update label
create_or_update_label() {
  local label_def=$1
  local name=$(echo "$label_def" | cut -d: -f1)
  local description=$(echo "$label_def" | cut -d: -f2)
  local color=$(echo "$label_def" | cut -d: -f3)
  
  if gh label list | grep -q "^$name"; then
    echo "  ↻ Updating: $name"
    gh label edit "$name" --description "$description" --color "$color" 2>/dev/null || true
  else
    echo "  + Creating: $name"
    gh label create "$name" --description "$description" --color "$color" 2>/dev/null || true
  fi
}

# Function to delete label
delete_label() {
  local name=$1
  if gh label list | grep -q "^$name"; then
    echo "  - Deleting: $name"
    gh label delete "$name" --yes 2>/dev/null || true
  fi
}

echo "Processing ride-optimizer..."
echo ""

# Delete duplicate/unnecessary labels in ride-optimizer
delete_label "a11y"  # Use accessibility instead
delete_label "ui/ux"  # Split into ux and design
delete_label "feature"  # Use enhancement instead
delete_label "api"  # Too generic, use backend/frontend
delete_label "visualization"  # Use frontend + enhancement
delete_label "integration"  # Use testing

# Create/update all standard labels
for label in "${CORE_LABELS[@]}" "${PRIORITY_LABELS[@]}" "${CATEGORY_LABELS[@]}" "${INFRA_LABELS[@]}" "${SPECIAL_LABELS[@]}"; do
  create_or_update_label "$label"
done

echo ""
echo "Processing mealplanner..."
echo ""

cd /Users/erik/dev/mealplanner

# Delete duplicate/unnecessary labels in mealplanner
delete_label "a11y"  # Use accessibility instead
delete_label "user-testing-2026-03-22"  # Specific date label, not needed
delete_label "devops"  # Use ci/cd and deployment instead
delete_label "monitoring"  # Use infrastructure
delete_label "nginx"  # Too specific
delete_label "observability"  # Use infrastructure
delete_label "reliability"  # Use performance or infrastructure
delete_label "optimization"  # Use performance
delete_label "fullstack"  # Use backend + frontend

# Create/update all standard labels
for label in "${CORE_LABELS[@]}" "${PRIORITY_LABELS[@]}" "${CATEGORY_LABELS[@]}" "${INFRA_LABELS[@]}" "${SPECIAL_LABELS[@]}"; do
  create_or_update_label "$label"
done

# Keep mealplanner-specific labels
MEALPLANNER_SPECIFIC=(
  "user-testing:Issues found during user testing sessions:#D4C5F9"
  "design-review:From design review process:#0E8A16"
  "vp-decision:Priority set by VP of Product:#5319E7"
  "error-recovery:Error handling and recovery:#FBCA04"
  "mobile:Mobile-specific issues:#1D76DB"
  "beta-testing:Issues from beta testing:#E99695"
  "ftue:First Time User Experience:#0E8A16"
  "collaboration:Collaboration features:#1D76DB"
  "user-retention:Critical for user retention:#B60205"
  "safety:Safety-critical feature:#B60205"
  "database:Database related:#d4c5f9"
)

for label in "${MEALPLANNER_SPECIFIC[@]}"; do
  create_or_update_label "$label"
done

cd /Users/erik/dev/ride-optimizer

echo ""
echo "✅ Label alignment complete!"
echo ""
echo "Standard labels now available in both projects:"
echo "  - Core: bug, enhancement, documentation, etc."
echo "  - Priority: P0-critical through P4-future"
echo "  - Category: architecture, performance, testing, security, accessibility"
echo "  - Tech: backend, frontend, design, ux"
echo "  - Infrastructure: deployment, docker, ci/cd, raspberry-pi"
echo "  - Special: blocking-launch, quick-win, data-loss-prevention"

# Made with Bob
