# GitHub Issues Creation Guide - UI/UX Redesign

**Date:** 2026-05-08  
**Based on:** [`FINAL_IMPLEMENTATION_PLAN.md`](FINAL_IMPLEMENTATION_PLAN.md)  
**Total Issues:** 1 Epic + 18 Issues

---

## Quick Start

```bash
# Create the Epic first
gh issue create --title "Epic: UI/UX Redesign - Lightweight Web App Optimization" \
  --label "epic,design,P0-critical,enhancement" \
  --body-file docs/github-issues/epic-uiux-redesign.md

# Get the Epic number (e.g., #250)
EPIC_NUM=250

# Create Phase 1 issues (linked to Epic)
gh issue create --title "Consolidate Navigation from 4 Tabs to 2 Tabs" \
  --label "design,navigation,breaking-change,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --body "Parent Epic: #${EPIC_NUM}

Current 4-tab navigation causes 40-60% navigation errors. Consolidate to Home, Routes, Settings.

**Acceptance Criteria:**
- [ ] Navigation shows only Home, Routes, Settings
- [ ] Home includes weather, next commute, recent routes
- [ ] Routes has side-by-side comparison
- [ ] URL routing updated
- [ ] Mobile bottom navigation
- [ ] User testing shows <10% confusion

**Effort:** 3 days"

# Continue for remaining issues...
```

---

## Epic Issue Template

**File:** `docs/github-issues/epic-uiux-redesign.md`

```markdown
## Overview

Comprehensive UI/UX redesign to transform the application from a static report to an optimized web application. Consolidates navigation, optimizes viewport usage, ensures accessibility compliance, and implements error recovery—all with zero new dependencies.

## Business Value

- Reduce navigation confusion from 40-60% to <10%
- Optimize for 13" MacBook Pro at 80% browser width (1024x768)
- Achieve WCAG 2.1 AA compliance (legal requirement)
- Prevent data loss with auto-save and undo
- Improve mobile usability

## Technical Approach

- **Zero new dependencies** (native browser APIs only)
- **Bundle size:** +26KB (45KB → 71KB)
- **Vanilla JavaScript** architecture maintained
- **8-week timeline** across 3 phases

## Success Metrics

- [ ] 100% primary content visible on 1024x768 without scrolling
- [ ] Navigation confusion <10%
- [ ] 100% WCAG 2.1 AA compliance
- [ ] Bundle size <100KB
- [ ] Load time <2s on 3G
- [ ] Task completion rate ≥90%
- [ ] User satisfaction ≥4.5/5

## Timeline

- **Phase 1 (Weeks 1-3):** Navigation, viewport, accessibility
- **Phase 2 (Weeks 4-5):** Components, mobile optimization
- **Phase 3 (Weeks 6-8):** Enhancement, polish, testing

## Budget

$54,890

## Stakeholder Approvals

- ✅ Marcus Rodriguez (Product Manager)
- ✅ Sarah Chen (Principal UX Designer)
- ✅ Dr. Emily Watson (Accessibility Specialist)
- ✅ Alex Thompson (Frontend Lead)
- ✅ Jennifer Park (VP of Product)

## Related Documents

- [UI/UX Redesign Strategy](../UIUX_REDESIGN_STRATEGY.md)
- [Engineering Review](../ENGINEERING_REVIEW_UIUX_REDESIGN.md)
- [Final Implementation Plan](../FINAL_IMPLEMENTATION_PLAN.md)
```

---

## Phase 1: Critical Fixes (P0)

### Issue #1: Consolidate Navigation (4 → 2 Tabs)

```bash
gh issue create \
  --title "Consolidate Navigation from 4 Tabs to 2 Tabs" \
  --label "design,navigation,breaking-change,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-lead" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** 4-tab navigation causes 40-60% navigation errors

**Solution:** Consolidate to Home, Routes, Settings

**Acceptance Criteria:**
- [ ] Navigation shows only Home, Routes, Settings
- [ ] Home includes weather, next commute, recent routes, quick actions
- [ ] Routes has side-by-side comparison view
- [ ] All Commute functionality merged into Home
- [ ] Planner removed (show 'coming soon')
- [ ] URL routing: / → Home, /routes → Routes, /settings → Settings
- [ ] Mobile bottom navigation
- [ ] Redirects for old URLs
- [ ] User testing shows <10% confusion

**Effort:** 3 days

**Related:** #2, #3"
```

### Issue #2: Optimize Home Page (No Scroll on 1024x768)

```bash
gh issue create \
  --title "Optimize Home Page for 1024x768 Viewport (No Scroll)" \
  --label "design,layout,viewport-optimization,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Current dashboard requires scrolling on target viewport

**Solution:** Redesign to fit within 768px height

**Layout:**
- Navigation: 56px
- Compact info bar: 72px
- Quick actions: 48px
- Recent routes: 592px
- **Total: 768px ✓**

**Acceptance Criteria:**
- [ ] All primary content visible on 1024x768 without scrolling
- [ ] Compact info bar with weather, next commute, stats
- [ ] Quick action buttons (48px height)
- [ ] Recent routes shows 5 routes
- [ ] Responsive 320px → 1920px+
- [ ] No horizontal scroll
- [ ] Load time <2s
- [ ] Lighthouse score ≥90

**Effort:** 2 days

**Related:** #1, #3"
```

### Issue #3: Redesign Routes Page (Side-by-Side)

```bash
gh issue create \
  --title "Redesign Routes Page with Side-by-Side Layout" \
  --label "design,layout,routes,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Cannot compare routes and see map simultaneously

**Solution:** Side-by-side layout (360px list + 640px map)

**Layout:**
- Navigation: 56px
- Filters: 48px
- Comparison: 664px (360px + 640px)
- **Total: 768px ✓**

**Acceptance Criteria:**
- [ ] Route list (360px) on left
- [ ] Interactive map (640px) on right
- [ ] 5-7 routes visible without scrolling
- [ ] Click to highlight on map
- [ ] Ctrl/Cmd+Click for multi-select
- [ ] Map auto-zooms to selected routes
- [ ] Direction arrows on polylines
- [ ] Filters bar (direction, distance, sort)
- [ ] Responsive: stacks on mobile
- [ ] 60fps map interactions

**Effort:** 3 days

**Related:** #1, #2, #10"
```

### Issue #4: Add ARIA Labels to All Interactive Elements

```bash
gh issue create \
  --title "Add ARIA Labels to All Interactive Elements" \
  --label "accessibility,a11y,WCAG,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev,accessibility-specialist" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Missing ARIA labels violate WCAG 4.1.2. Legal liability.

**Solution:** Add descriptive ARIA labels to ALL interactive elements

**Acceptance Criteria:**
- [ ] All icon buttons have aria-label
- [ ] All form inputs have labels
- [ ] All images have alt text
- [ ] All interactive elements have descriptive labels
- [ ] Dynamic content has ARIA live regions
- [ ] Screen reader testing passes (NVDA, JAWS, VoiceOver)
- [ ] Automated testing passes (axe, WAVE)
- [ ] No WCAG 4.1.2 violations
- [ ] Documentation updated

**Effort:** 3 days

**Related:** #5, #6"
```

### Issue #5: Implement Visible Focus Indicators (2px Min)

```bash
gh issue create \
  --title "Implement Visible Focus Indicators (2px Minimum)" \
  --label "accessibility,a11y,WCAG,keyboard-navigation,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Focus indicators barely visible. Violates WCAG 2.4.7.

**Solution:** 2px minimum visible focus indicators with high contrast

**Acceptance Criteria:**
- [ ] All interactive elements have visible focus
- [ ] Focus indicators 2px minimum thickness
- [ ] Sufficient contrast (3:1 minimum)
- [ ] Visible on all backgrounds
- [ ] Keyboard navigation works on all pages
- [ ] Tab order is logical
- [ ] No WCAG 2.4.7 violations
- [ ] Tested keyboard-only navigation

**Effort:** 2 days

**Related:** #4, #6"
```

### Issue #6: Add Skip Navigation Links

```bash
gh issue create \
  --title "Add Skip Navigation Links" \
  --label "accessibility,a11y,WCAG,keyboard-navigation,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Keyboard users must tab through entire navigation. Violates WCAG 2.4.1.

**Solution:** Skip links to jump to main content, route list, map

**Acceptance Criteria:**
- [ ] Skip links appear on keyboard focus
- [ ] Hidden visually until focused
- [ ] Skip to main content
- [ ] Skip to route list (Routes page)
- [ ] Skip to map (Routes page)
- [ ] Links work correctly
- [ ] No WCAG 2.4.1 violations
- [ ] Tested with keyboard navigation

**Effort:** 1 day

**Related:** #4, #5"
```

### Issue #7: Implement Debounced Auto-Save

```bash
gh issue create \
  --title "Implement Debounced Auto-Save for User Preferences" \
  --label "error-recovery,data-loss-prevention,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Users lose preferences on crash/navigation

**Solution:** Auto-save to localStorage with 500ms debouncing

**Acceptance Criteria:**
- [ ] Auto-save 500ms after last change (debounced)
- [ ] Save on page unload
- [ ] Load on page load
- [ ] Preferences: favorites, hidden routes, sort, filters, units
- [ ] Error handling for localStorage failures
- [ ] 'Saving...' indicator
- [ ] 'All changes saved' confirmation
- [ ] Settings page to manage preferences
- [ ] Export/import functionality

**Effort:** 2 days

**Related:** #8, #9"
```

### Issue #8: Add Single-Level Undo with Toast

```bash
gh issue create \
  --title "Add Single-Level Undo Functionality with Toast" \
  --label "error-recovery,undo,toast,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Destructive actions permanent. No recovery.

**Solution:** Single-level undo with 5-second toast window

**Acceptance Criteria:**
- [ ] Undo for: hide route, unfavorite
- [ ] Toast shows action with 'Undo' button
- [ ] 5-second window
- [ ] Auto-dismisses after 5s
- [ ] Only one toast at a time
- [ ] Non-blocking
- [ ] Keyboard accessible (Tab, Escape)
- [ ] Screen reader announces toast
- [ ] Clear 'Undo last action' label

**Effort:** 2 days

**Related:** #7, #9, #12"
```

### Issue #9: Add Unsaved Changes Warning

```bash
gh issue create \
  --title "Add Unsaved Changes Warning" \
  --label "error-recovery,data-loss-prevention,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Users can navigate away with unsaved changes. Silent data loss.

**Solution:** Warn before leaving with unsaved changes

**Acceptance Criteria:**
- [ ] Warning dialog on navigation with unsaved changes
- [ ] Message: 'You have unsaved changes. Are you sure?'
- [ ] User can cancel navigation
- [ ] User can proceed and lose changes
- [ ] Works for: back button, link clicks, refresh
- [ ] Does not trigger after successful save
- [ ] Clear indication of what will be lost

**Effort:** 1 day

**Related:** #7, #8"
```

---

## Phase 2: Components & Mobile (P1)

### Issue #10: Create Compact Route Card Component

```bash
gh issue create \
  --title "Create Compact Route Card Component" \
  --label "design,component,routes,P1-high" \
  --milestone "Phase 2 - Components & Mobile" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Current cards too large (80px), inconsistent styling

**Solution:** Standardized compact card (56px height)

**Acceptance Criteria:**
- [ ] Height: 56px (down from 80px)
- [ ] Displays: rank, name, distance, elevation, score, weather
- [ ] Optimal route has gradient background
- [ ] Hover: translateX(4px) + shadow
- [ ] Click to select/deselect
- [ ] Keyboard accessible
- [ ] Screen reader friendly
- [ ] Responsive mobile
- [ ] Reusable across pages
- [ ] Documented in component library

**Effort:** 2 days

**Related:** #3, #11"
```

### Issue #11: Implement Skeleton Loading States

```bash
gh issue create \
  --title "Implement Skeleton Loading States" \
  --label "performance,loading,UX,P1-high" \
  --milestone "Phase 2 - Components & Mobile" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Blank screens during loading. Feels slow.

**Solution:** Skeleton screens for all async content

**Acceptance Criteria:**
- [ ] Skeleton for route cards
- [ ] Skeleton for map
- [ ] Skeleton for weather widget
- [ ] CSS-only animations (no JS)
- [ ] Matches final content layout
- [ ] Smooth transition to real content
- [ ] Respects prefers-reduced-motion
- [ ] No layout shift (CLS = 0)
- [ ] Documented in component library

**Effort:** 2 days

**Related:** #10, #12"
```

### Issue #12: Add Toast Notification System

```bash
gh issue create \
  --title "Add Toast Notification System" \
  --label "component,notifications,UX,P1-high" \
  --milestone "Phase 2 - Components & Mobile" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** No feedback for user actions

**Solution:** Toast system for success, error, info messages

**Acceptance Criteria:**
- [ ] Toast types: success, error, info, warning
- [ ] Auto-dismiss after 5s (configurable)
- [ ] Manual dismiss with X button
- [ ] Queue multiple toasts
- [ ] Keyboard accessible (Tab, Escape)
- [ ] Screen reader announces
- [ ] Position: bottom-right (mobile: bottom-center)
- [ ] Slide-in animation
- [ ] Respects prefers-reduced-motion
- [ ] Documented in component library

**Effort:** 2 days

**Related:** #8, #11"
```

### Issue #13: Optimize Touch Targets (44px Minimum)

```bash
gh issue create \
  --title "Optimize Touch Targets (44px Minimum)" \
  --label "mobile,accessibility,touch,P1-high" \
  --milestone "Phase 2 - Components & Mobile" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Touch targets too small on mobile. Hard to tap.

**Solution:** Ensure all interactive elements ≥44x44px

**Acceptance Criteria:**
- [ ] All buttons ≥44x44px
- [ ] All links ≥44x44px
- [ ] All form controls ≥44px height
- [ ] Adequate spacing between targets (8px min)
- [ ] Tested on real mobile devices
- [ ] No accidental taps
- [ ] Passes mobile usability test
- [ ] Documented in design system

**Effort:** 2 days

**Related:** #14, #15"
```

### Issue #14: Implement Mobile Bottom Navigation

```bash
gh issue create \
  --title "Implement Mobile Bottom Navigation" \
  --label "mobile,navigation,P1-high" \
  --milestone "Phase 2 - Components & Mobile" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Top navigation hard to reach on mobile

**Solution:** Bottom navigation bar for mobile (<768px)

**Acceptance Criteria:**
- [ ] Bottom bar on mobile (<768px)
- [ ] Icons + labels for Home, Routes, Settings
- [ ] Active state clearly indicated
- [ ] Fixed position (always visible)
- [ ] Height: 56px
- [ ] Touch targets ≥44x44px
- [ ] Smooth transitions
- [ ] Tested on real devices
- [ ] Documented in component library

**Effort:** 2 days

**Related:** #1, #13, #15"
```

### Issue #15: Add Swipe Gestures for Mobile

```bash
gh issue create \
  --title "Add Swipe Gestures for Mobile Navigation" \
  --label "mobile,gestures,P1-high" \
  --milestone "Phase 2 - Components & Mobile" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Mobile navigation requires tapping

**Solution:** Swipe gestures for common actions

**Acceptance Criteria:**
- [ ] Swipe left/right to navigate tabs
- [ ] Swipe down to refresh
- [ ] Visual feedback during swipe
- [ ] Smooth animations
- [ ] Respects prefers-reduced-motion
- [ ] Does not conflict with map gestures
- [ ] Tested on iOS and Android
- [ ] Documented in user guide

**Effort:** 3 days

**Related:** #13, #14"
```

---

## Phase 3: Enhancement & Polish (P2)

### Issue #16: Add Help Modal with Keyboard Shortcuts

```bash
gh issue create \
  --title "Add Help Modal with Keyboard Shortcuts" \
  --label "help,documentation,keyboard,P2-medium" \
  --milestone "Phase 3 - Enhancement & Polish" \
  --assignee "frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Users don't know keyboard shortcuts

**Solution:** Help modal (? key) with shortcuts and tips

**Acceptance Criteria:**
- [ ] Modal opens with ? key
- [ ] Lists all keyboard shortcuts
- [ ] Organized by category
- [ ] Search functionality
- [ ] Close with Escape or X button
- [ ] Keyboard accessible
- [ ] Screen reader friendly
- [ ] Mobile responsive
- [ ] Documented shortcuts

**Effort:** 2 days

**Related:** #5, #6"
```

### Issue #17: Implement Animated GIF Tutorials

```bash
gh issue create \
  --title "Implement Animated GIF Tutorials for Key Features" \
  --label "help,documentation,onboarding,P2-medium" \
  --milestone "Phase 3 - Enhancement & Polish" \
  --assignee "designer,frontend-dev" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** Users don't discover key features

**Solution:** Animated GIF tutorials for common tasks

**Acceptance Criteria:**
- [ ] GIFs for: route comparison, favorites, filters, multi-select
- [ ] Max 5MB per GIF
- [ ] Optimized for web (lossy compression)
- [ ] Lazy loaded
- [ ] Alt text for accessibility
- [ ] Play on hover (optional)
- [ ] Embedded in help modal
- [ ] Documented in user guide

**Effort:** 3 days

**Related:** #16"
```

### Issue #18: Add Comprehensive E2E Testing

```bash
gh issue create \
  --title "Add Comprehensive E2E Testing for UI/UX Features" \
  --label "testing,e2e,quality,P2-medium" \
  --milestone "Phase 3 - Enhancement & Polish" \
  --assignee "qa-engineer" \
  --body "**Parent Epic:** #${EPIC_NUM}

**Problem:** No automated testing for UI/UX features

**Solution:** Comprehensive E2E test suite

**Acceptance Criteria:**
- [ ] Tests for all 18 features
- [ ] Navigation flow tests
- [ ] Accessibility tests (axe)
- [ ] Mobile responsive tests
- [ ] Keyboard navigation tests
- [ ] Error recovery tests
- [ ] Performance tests (Lighthouse)
- [ ] Cross-browser tests (Chrome, Firefox, Safari)
- [ ] CI/CD integration
- [ ] Test coverage ≥80%

**Effort:** 5 days

**Related:** All issues"
```

---

## Automation Script

Create `scripts/create_uiux_issues.sh`:

```bash
#!/bin/bash

# Create UI/UX Redesign Issues
# Usage: ./scripts/create_uiux_issues.sh

set -e

echo "Creating UI/UX Redesign Epic and Issues..."

# Create Epic
echo "Creating Epic..."
EPIC_NUM=$(gh issue create \
  --title "Epic: UI/UX Redesign - Lightweight Web App Optimization" \
  --label "epic,design,P0-critical,enhancement" \
  --body-file docs/github-issues/epic-uiux-redesign.md \
  --json number --jq '.number')

echo "✓ Epic created: #${EPIC_NUM}"

# Phase 1: Critical Fixes (P0)
echo ""
echo "Creating Phase 1 issues..."

gh issue create --title "Consolidate Navigation from 4 Tabs to 2 Tabs" \
  --label "design,navigation,breaking-change,P0-critical" \
  --milestone "Phase 1 - Critical Fixes" \
  --body "Parent Epic: #${EPIC_NUM}

See docs/GITHUB_ISSUES_CREATION_GUIDE.md for full details."

# Continue for all 18 issues...

echo ""
echo "✓ All issues created successfully!"
echo "✓ Epic: #${EPIC_NUM}"
echo "✓ View at: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/issues/${EPIC_NUM}"
```

---

## Summary

**Total Issues:** 19 (1 Epic + 18 Issues)

**Phase 1 (P0):** 9 issues - Navigation, viewport, accessibility, error recovery  
**Phase 2 (P1):** 6 issues - Components, mobile optimization  
**Phase 3 (P2):** 3 issues - Help, tutorials, testing

**Timeline:** 8 weeks  
**Budget:** $54,890

**Next Steps:**
1. Create Epic issue first
2. Create Phase 1 issues (link to Epic)
3. Create Phase 2 issues (link to Epic)
4. Create Phase 3 issues (link to Epic)
5. Assign to team members
6. Set up project board
7. Begin implementation