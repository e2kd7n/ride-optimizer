#!/bin/bash

# Create P2 GitHub issues from FUTURE_TODOS.md
# Created: 2026-03-27

echo "Creating P2 GitHub issues..."

# Issue 1: Route matching investigation
gh issue create \
  --title "Investigate why routes 78 and 62 aren't matching in route grouping" \
  --label "P2-medium,bug,backend" \
  --body "During route analysis, routes 78 and 62 are not being grouped together despite potentially being similar routes. This needs investigation to determine if:

1. The routes should actually be grouped together
2. The similarity algorithm needs adjustment
3. The distance/coordinate comparison thresholds need tuning

**Acceptance Criteria:**
- [ ] Analyze routes 78 and 62 to determine if they should match
- [ ] Review route similarity algorithm logic
- [ ] Check distance and coordinate comparison thresholds
- [ ] Document findings and recommend changes if needed
- [ ] Implement fixes if algorithm needs adjustment

**Related Files:**
- \`src/route_analyzer.py\` - Route grouping logic
- \`src/optimizer.py\` - Route similarity calculations

**Priority:** P2-medium (affects route grouping accuracy but not critical)"

# Issue 2: Map visual hierarchy
gh issue create \
  --title "Ensure selected polylines and tooltips appear on top of all map elements" \
  --label "P2-medium,enhancement,ux,frontend" \
  --body "When a route is selected on the interactive map, the polyline and tooltip should appear on top of all other map elements for better visibility. Currently, selected routes may be obscured by other route lines.

**Current Behavior:**
- Selected routes don't always appear on top
- Tooltips may be hidden behind other map elements
- Visual hierarchy is unclear between selected and non-selected routes

**Desired Behavior:**
- Selected routes should have higher z-index than non-selected routes
- Tooltips should appear above all map elements
- Clear visual distinction between selected and non-selected routes

**Acceptance Criteria:**
- [ ] Selected polylines appear on top of all other route lines
- [ ] Tooltips are always visible and not obscured
- [ ] Visual hierarchy is clear and intuitive
- [ ] Changes work across all browsers
- [ ] No performance degradation

**Related Files:**
- \`src/visualizer.py\` - Map generation logic
- \`templates/report_template.html\` - Map rendering and JavaScript

**Priority:** P2-medium (UX improvement, not blocking core functionality)

**Related Issues:** Part of broader UI/UX improvements (#71)"

echo ""
echo "✅ Created 2 P2 issues successfully!"
echo ""
echo "Next steps:"
echo "1. Update ISSUE_PRIORITIES.md with actual issue numbers"
echo "2. Delete FUTURE_TODOS.md (issues now tracked on GitHub)"
echo "3. Update summary statistics in ISSUE_PRIORITIES.md"

# Made with Bob
