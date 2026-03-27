# GitHub Issues to Create from FUTURE_TODOS.md

Created: 2026-03-27

## Issue 1: Investigate Route Matching Algorithm for Routes 78 and 62

**Title**: Investigate why routes 78 and 62 aren't matching in route grouping

**Labels**: P2-medium, bug, route-analysis

**Description**:
During route analysis, routes 78 and 62 are not being grouped together despite potentially being similar routes. This needs investigation to determine if:

1. The routes should actually be grouped together
2. The similarity algorithm needs adjustment
3. The distance/coordinate comparison thresholds need tuning

**Acceptance Criteria**:
- [ ] Analyze routes 78 and 62 to determine if they should match
- [ ] Review route similarity algorithm logic
- [ ] Check distance and coordinate comparison thresholds
- [ ] Document findings and recommend changes if needed
- [ ] Implement fixes if algorithm needs adjustment

**Related Files**:
- `src/route_analyzer.py` - Route grouping logic
- `src/optimizer.py` - Route similarity calculations

**Priority**: P2-medium (affects route grouping accuracy but not critical)

---

## Issue 2: Improve Map Visual Hierarchy for Selected Routes

**Title**: Ensure selected polylines and tooltips appear on top of all map elements

**Labels**: P2-medium, enhancement, ui-ux, map

**Description**:
When a route is selected on the interactive map, the polyline and tooltip should appear on top of all other map elements for better visibility. Currently, selected routes may be obscured by other route lines.

**Current Behavior**:
- Selected routes don't always appear on top
- Tooltips may be hidden behind other map elements
- Visual hierarchy is unclear between selected and non-selected routes

**Desired Behavior**:
- Selected routes should have higher z-index than non-selected routes
- Tooltips should appear above all map elements
- Clear visual distinction between selected and non-selected routes

**Acceptance Criteria**:
- [ ] Selected polylines appear on top of all other route lines
- [ ] Tooltips are always visible and not obscured
- [ ] Visual hierarchy is clear and intuitive
- [ ] Changes work across all browsers
- [ ] No performance degradation

**Related Files**:
- `src/visualizer.py` - Map generation logic
- `templates/report_template.html` - Map rendering and JavaScript

**Priority**: P2-medium (UX improvement, not blocking core functionality)

**Related Issues**: Part of broader UI/UX improvements (#71)

---

## Instructions for Creating Issues

1. Create these issues on GitHub with the exact titles above
2. Apply the specified labels to each issue
3. Copy the description, acceptance criteria, and related files to each issue
4. Link Issue 2 to Issue #71 (UI/UX Improvements Epic)
5. Update ISSUE_PRIORITIES.md to reflect the new P2 issues
6. Delete FUTURE_TODOS.md after issues are created

## Summary

- **Total Issues**: 2
- **Priority**: Both P2-medium
- **Categories**: 1 bug (route matching), 1 enhancement (map UI)