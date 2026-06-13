# UI/UX Redesign - GitHub Issues for Engineering Implementation

**Date:** 2026-05-08  
**Based on:** [`UIUX_REDESIGN_STRATEGY.md`](UIUX_REDESIGN_STRATEGY.md)  
**Priority System:** P0 (Critical) → P1 (High) → P2 (Medium) → P3 (Low)

---

## Overview

This document contains detailed GitHub issue specifications for implementing the UI/UX redesign. Issues are organized by priority and phase, with clear acceptance criteria and implementation guidance.

**Total Issues:** 30  
**Estimated Effort:** 26 weeks (6 months)  
**Phases:** 4 (Critical → Consistency → Enhancement → Polish)

---

## Phase 1: Critical Fixes (P0) - Weeks 1-4

### Issue #1: Consolidate Navigation from 4 Tabs to 2 Tabs

**Priority:** P0-critical  
**Labels:** `design`, `navigation`, `breaking-change`, `P0-critical`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Lead

**Problem:**
Current 4-tab navigation (Dashboard, Commute, Planner, Routes) reflects developer thinking rather than user mental models. This causes 40-60% navigation errors and confusion about which tab to use for common tasks.

**Solution:**
Consolidate to 2 primary tabs + 1 utility tab:
- **Home** (replaces Dashboard + Commute)
- **Routes** (enhanced route comparison + library)
- **Settings** (new utility tab)

**Acceptance Criteria:**
- [ ] Navigation bar shows only "Home", "Routes", "Settings"
- [ ] Home page includes weather, next commute, recent routes, quick actions
- [ ] Routes page has side-by-side comparison view
- [ ] All Commute functionality merged into Home
- [ ] Planner tab removed (future feature)
- [ ] URL routing updated (`/` → Home, `/routes` → Routes, `/settings` → Settings)
- [ ] Mobile navigation uses bottom bar pattern
- [ ] All links and redirects updated
- [ ] User testing shows <10% navigation confusion (down from 40-60%)

**Implementation Notes:**
```javascript
// New route structure
const routes = [
  { path: '/', component: HomePage },
  { path: '/routes', component: RoutesPage },
  { path: '/routes/:id', component: RouteDetailPage },
  { path: '/settings', component: SettingsPage }
];

// Deprecated routes (redirect to new structure)
const deprecatedRoutes = [
  { path: '/dashboard.html', redirect: '/' },
  { path: '/commute.html', redirect: '/' },
  { path: '/planner.html', redirect: '/' } // Show "coming soon" message
];
```

**Related Issues:** #2, #3, #4

---

### Issue #2: Optimize Home Page for 1024x768 Viewport (No Scroll)

**Priority:** P0-critical  
**Labels:** `design`, `layout`, `viewport-optimization`, `P0-critical`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Developer

**Problem:**
Current dashboard requires excessive scrolling on 13" MacBook Pro at 80% browser width (1024x768 effective viewport). Users must scroll to see route list, map, and recommendations.

**Solution:**
Redesign Home page to fit entirely within 1024x768 viewport with no vertical scrolling required for primary content.

**Layout Breakdown:**
```
Navigation Bar:     56px
Compact Info Bar:   72px
Quick Actions:      48px
Recent Routes:     592px
─────────────────────────
Total:             768px ✓
```

**Acceptance Criteria:**
- [ ] All primary content visible on 1024x768 without scrolling
- [ ] Compact info bar (72px height) with weather, next commute, stats
- [ ] Quick action buttons (48px height) for common tasks
- [ ] Recent routes section (592px) shows 5 routes
- [ ] Responsive down to 320px mobile
- [ ] Responsive up to 1920px+ desktop
- [ ] Tested on actual 13" MacBook Pro at 80% browser width
- [ ] No horizontal scrolling at any breakpoint
- [ ] Performance: Page loads in <2 seconds

**CSS Implementation:**
```css
.home-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.compact-info-bar {
  height: 72px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 12px;
}

.quick-actions {
  height: 48px;
  display: flex;
  gap: 12px;
  padding: 0 12px;
}

.recent-routes {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
```

**Related Issues:** #1, #3, #5

---

### Issue #3: Redesign Routes Page with Side-by-Side Layout

**Priority:** P0-critical  
**Labels:** `design`, `layout`, `routes`, `P0-critical`  
**Estimated Effort:** 1.5 weeks  
**Assignee:** Frontend Developer

**Problem:**
Current Routes page shows either list OR map, requiring users to switch views. Cannot compare routes and see map simultaneously on laptop viewport.

**Solution:**
Side-by-side layout with route list (360px) on left and interactive map (640px) on right. Fits within 1024x768 viewport.

**Layout Breakdown:**
```
Navigation Bar:     56px
Filters Bar:        48px
Route Comparison:  664px (360px list + 640px map)
─────────────────────────
Total:             768px ✓
```

**Acceptance Criteria:**
- [ ] Route list (360px width) on left side
- [ ] Interactive map (640px width) on right side
- [ ] 5-7 routes visible without scrolling
- [ ] Click route to highlight on map
- [ ] Ctrl/Cmd+Click for multi-select
- [ ] Map auto-zooms to selected routes
- [ ] Direction arrows on route polylines
- [ ] Route colors match list (green, red, blue, yellow)
- [ ] Filters bar (48px) with direction, distance, sort
- [ ] Responsive: stacks vertically on tablet/mobile
- [ ] Tested on 1024x768 viewport

**Component Structure:**
```jsx
<RoutesPage>
  <FiltersBar />
  <RouteComparison>
    <RouteList width="360px">
      {routes.map(route => (
        <RouteCard 
          key={route.id}
          route={route}
          onSelect={handleSelect}
          isSelected={selectedIds.includes(route.id)}
        />
      ))}
    </RouteList>
    <RouteMap width="640px">
      <LeafletMap routes={routes} selected={selectedIds} />
    </RouteMap>
  </RouteComparison>
</RoutesPage>
```

**Related Issues:** #1, #2, #6, #7

---

### Issue #4: Add ARIA Labels to All Interactive Elements

**Priority:** P0-critical  
**Labels:** `accessibility`, `a11y`, `WCAG`, `P0-critical`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Developer + Accessibility Specialist

**Problem:**
Missing ARIA labels throughout application. Screen readers announce "button" with no context. Violates WCAG 4.1.2 (Name, Role, Value). Legal liability under ADA.

**Solution:**
Add descriptive ARIA labels to ALL interactive elements (buttons, links, inputs, icons).

**Acceptance Criteria:**
- [ ] All icon buttons have `aria-label` attributes
- [ ] All form inputs have associated labels
- [ ] All images have `alt` text
- [ ] All interactive elements have descriptive labels
- [ ] Screen reader testing passes (NVDA, JAWS, VoiceOver)
- [ ] Automated testing passes (axe, WAVE)
- [ ] No WCAG 4.1.2 violations
- [ ] Documentation updated with accessibility guidelines

**Implementation Examples:**
```html
<!-- WRONG -->
<button onclick="favoriteRoute()">
  <i class="icon-star"></i>
</button>

<!-- CORRECT -->
<button 
  onclick="favoriteRoute()"
  aria-label="Add Main St route to favorites"
  title="Add to favorites"
>
  <i class="icon-star" aria-hidden="true"></i>
</button>

<!-- Form inputs -->
<label for="route-search">Search routes</label>
<input 
  id="route-search"
  type="text"
  aria-describedby="search-help"
/>
<span id="search-help" class="sr-only">
  Search by route name, distance, or location
</span>

<!-- Images -->
<img 
  src="route-map.png" 
  alt="Map showing Main Street route from home to work"
/>
```

**Testing Checklist:**
- [ ] Run axe DevTools on all pages
- [ ] Run WAVE on all pages
- [ ] Test with NVDA (Windows)
- [ ] Test with JAWS (Windows)
- [ ] Test with VoiceOver (macOS/iOS)
- [ ] Lighthouse accessibility score ≥ 95

**Related Issues:** #5, #6, #7

---

### Issue #5: Implement Visible Focus Indicators (2px Minimum)

**Priority:** P0-critical  
**Labels:** `accessibility`, `a11y`, `WCAG`, `keyboard-navigation`, `P0-critical`  
**Estimated Effort:** 3 days  
**Assignee:** Frontend Developer

**Problem:**
Focus indicators barely visible or missing. Keyboard users lose their place. Violates WCAG 2.4.7 (Focus Visible).

**Solution:**
Add 2px minimum visible focus indicators to ALL interactive elements with high contrast.

**Acceptance Criteria:**
- [ ] All interactive elements have visible focus indicators
- [ ] Focus indicators are 2px minimum thickness
- [ ] Focus indicators have sufficient contrast (3:1 minimum)
- [ ] Focus indicators visible on all backgrounds
- [ ] Keyboard navigation works on all pages
- [ ] Tab order is logical
- [ ] No WCAG 2.4.7 violations
- [ ] Tested with keyboard-only navigation

**CSS Implementation:**
```css
/* Global focus indicator */
*:focus-visible {
  outline: 2px solid #667eea;
  outline-offset: 2px;
}

/* Enhanced focus for interactive elements */
button:focus-visible,
a:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 3px solid #667eea;
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
}

/* Route cards */
.route-card:focus-visible {
  outline: 3px solid #667eea;
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
  transform: translateX(4px);
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  *:focus-visible {
    outline: 3px solid currentColor;
    outline-offset: 3px;
  }
}
```

**Testing Checklist:**
- [ ] Tab through all interactive elements
- [ ] Verify focus indicator visible on all backgrounds
- [ ] Test in high contrast mode
- [ ] Test with keyboard-only navigation
- [ ] Verify tab order is logical
- [ ] Test Shift+Tab (reverse navigation)

**Related Issues:** #4, #6, #7

---

### Issue #6: Add Skip Navigation Links

**Priority:** P0-critical  
**Labels:** `accessibility`, `a11y`, `WCAG`, `keyboard-navigation`, `P0-critical`  
**Estimated Effort:** 2 days  
**Assignee:** Frontend Developer

**Problem:**
Keyboard users must tab through entire navigation every page. Violates WCAG 2.4.1 (Bypass Blocks). Frustrating and time-consuming.

**Solution:**
Add skip links at top of page to jump to main content, route list, and map.

**Acceptance Criteria:**
- [ ] Skip links appear on keyboard focus
- [ ] Skip links hidden visually until focused
- [ ] Skip to main content link
- [ ] Skip to route list link (on Routes page)
- [ ] Skip to map link (on Routes page)
- [ ] Links work correctly (jump to target)
- [ ] No WCAG 2.4.1 violations
- [ ] Tested with keyboard navigation

**HTML Implementation:**
```html
<body>
  <!-- Skip links (hidden until focused) -->
  <a href="#main-content" class="skip-link">
    Skip to main content
  </a>
  <a href="#route-list" class="skip-link">
    Skip to route list
  </a>
  <a href="#route-map" class="skip-link">
    Skip to map
  </a>
  
  <nav>...</nav>
  
  <main id="main-content">
    <div id="route-list">...</div>
    <div id="route-map">...</div>
  </main>
</body>
```

**CSS Implementation:**
```css
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #667eea;
  color: white;
  padding: 8px 16px;
  text-decoration: none;
  z-index: 10000;
  border-radius: 0 0 4px 0;
  font-weight: 600;
  transition: top 0.2s;
}

.skip-link:focus {
  top: 0;
}
```

**Related Issues:** #4, #5, #7

---

### Issue #7: Implement Auto-Save for User Preferences

**Priority:** P0-critical  
**Labels:** `error-recovery`, `data-loss-prevention`, `P0-critical`  
**Estimated Effort:** 3 days  
**Assignee:** Frontend Developer

**Problem:**
Users lose preferences on browser crash or accidental navigation. No draft saving. Frustrating and drives users away.

**Solution:**
Auto-save user preferences to localStorage every 30 seconds and on page unload.

**Acceptance Criteria:**
- [ ] Preferences auto-save every 30 seconds
- [ ] Preferences save on page unload
- [ ] Preferences load on page load
- [ ] Preferences include: favorites, hidden routes, sort, filters, units
- [ ] Error handling for localStorage failures
- [ ] Clear indication when preferences are saved
- [ ] Settings page to manage preferences
- [ ] Export/import preferences functionality

**Implementation:**
```javascript
class PreferencesManager {
  constructor() {
    this.saveInterval = 30000; // 30 seconds
    this.preferences = this.load();
    this.startAutoSave();
  }
  
  load() {
    try {
      const saved = localStorage.getItem('ride-optimizer-prefs');
      return saved ? JSON.parse(saved) : this.getDefaults();
    } catch (error) {
      console.error('Failed to load preferences:', error);
      return this.getDefaults();
    }
  }
  
  save() {
    try {
      localStorage.setItem(
        'ride-optimizer-prefs',
        JSON.stringify(this.preferences)
      );
      this.showSaveIndicator();
      return true;
    } catch (error) {
      console.error('Failed to save preferences:', error);
      this.showError('Failed to save preferences');
      return false;
    }
  }
  
  startAutoSave() {
    // Auto-save every 30 seconds
    setInterval(() => this.save(), this.saveInterval);
    
    // Save on page unload
    window.addEventListener('beforeunload', () => this.save());
  }
  
  getDefaults() {
    return {
      favoriteRoutes: [],
      hiddenRoutes: [],
      sortPreference: 'score',
      directionFilter: 'all',
      units: 'imperial',
      theme: 'light'
    };
  }
  
  showSaveIndicator() {
    // Show subtle "Saved" indicator
    const indicator = document.getElementById('save-indicator');
    indicator.textContent = 'Saved';
    indicator.classList.add('visible');
    setTimeout(() => {
      indicator.classList.remove('visible');
    }, 2000);
  }
}

// Initialize
const preferencesManager = new PreferencesManager();
```

**Related Issues:** #8, #9

---

### Issue #8: Add Undo Functionality with Toast Notifications

**Priority:** P0-critical  
**Labels:** `error-recovery`, `undo`, `toast`, `P0-critical`  
**Estimated Effort:** 4 days  
**Assignee:** Frontend Developer

**Problem:**
Destructive actions (hide route, unfavorite) are permanent and immediate. No recovery. Users afraid to take actions.

**Solution:**
Implement undo functionality with 5-second window via toast notifications.

**Acceptance Criteria:**
- [ ] Undo available for: hide route, unfavorite, delete (if implemented)
- [ ] Toast notification shows action with "Undo" button
- [ ] 5-second window to undo
- [ ] Toast auto-dismisses after 5 seconds
- [ ] Multiple toasts stack vertically
- [ ] Toasts are non-blocking
- [ ] Keyboard accessible (Tab to Undo button, Escape to dismiss)
- [ ] Screen reader announces toast content

**Implementation:**
```javascript
class UndoManager {
  constructor() {
    this.undoStack = [];
    this.undoTimeout = 5000; // 5 seconds
  }
  
  addAction(action, undoFn) {
    const undoItem = {
      action,
      undo: undoFn,
      timestamp: Date.now()
    };
    
    this.undoStack.push(undoItem);
    this.showUndoToast(action, undoFn);
    
    // Auto-remove after timeout
    setTimeout(() => {
      this.removeFromStack(undoItem);
    }, this.undoTimeout);
  }
  
  showUndoToast(action, undoFn) {
    const toast = document.createElement('div');
    toast.className = 'toast success';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    toast.innerHTML = `
      <div class="toast-icon">✓</div>
      <div class="toast-content">
        <div class="toast-title">${action}</div>
      </div>
      <button class="toast-action" onclick="handleUndo()">
        Undo
      </button>
      <button class="toast-close" onclick="this.parentElement.remove()">
        ×
      </button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-dismiss
    setTimeout(() => {
      toast.remove();
    }, this.undoTimeout);
  }
}

// Usage
const undoManager = new UndoManager();

function hideRoute(routeId) {
  const route = routes.find(r => r.id === routeId);
  route.hidden = true;
  updateRouteList();
  
  undoManager.addAction(
    'Route hidden',
    () => {
      route.hidden = false;
      updateRouteList();
    }
  );
}
```

**Related Issues:** #7, #9, #10

---

### Issue #9: Add Unsaved Changes Warning

**Priority:** P0-critical  
**Labels:** `error-recovery`, `data-loss-prevention`, `P0-critical`  
**Estimated Effort:** 2 days  
**Assignee:** Frontend Developer

**Problem:**
Users can navigate away from pages with unsaved changes. Silent data loss. Confusing and frustrating.

**Solution:**
Warn users before leaving pages with unsaved changes.

**Acceptance Criteria:**
- [ ] Warning dialog appears when navigating away with unsaved changes
- [ ] Warning includes: "You have unsaved changes. Are you sure?"
- [ ] User can cancel navigation
- [ ] User can proceed and lose changes
- [ ] Works for: browser back button, link clicks, page refresh
- [ ] Does not trigger after successful save
- [ ] Clear indication of what changes will be lost

**Implementation:**
```javascript
class UnsavedChangesGuard {
  constructor() {
    this.hasUnsavedChanges = false;
    this.setupWarning();
  }
  
  markDirty() {
    this.hasUnsavedChanges = true;
    this.updateUI();
  }
  
  markClean() {
    this.hasUnsavedChanges = false;
    this.updateUI();
  }
  
  setupWarning() {
    window.addEventListener('beforeunload', (e) => {
      if (this.hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
      }
    });
  }
  
  updateUI() {
    const indicator = document.getElementById('unsaved-indicator');
    if (this.hasUnsavedChanges) {
      indicator.textContent = 'Unsaved changes';
      indicator.classList.add('visible');
    } else {
      indicator.classList.remove('visible');
    }
  }
}

// Usage
const changeGuard = new UnsavedChangesGuard();

// Mark dirty on changes
document.querySelectorAll('input, select, textarea').forEach(input => {
  input.addEventListener('change', () => {
    changeGuard.markDirty();
  });
});

// Mark clean after save
function savePreferences() {
  if (preferencesManager.save()) {
    changeGuard.markClean();
    showToast('Preferences saved', 'success');
  }
}
```

**Related Issues:** #7, #8

---

## Phase 2: Consistency & Efficiency (P1) - Weeks 5-12

### Issue #10: Create Compact Route Card Component

**Priority:** P1-high  
**Labels:** `design`, `component`, `routes`, `P1-high`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Developer

**Problem:**
Current route cards are too large (80px height), limiting visible routes. Inconsistent styling across pages.

**Solution:**
Create standardized compact route card component (56px height) with consistent styling.

**Acceptance Criteria:**
- [ ] Route card height: 56px (down from 80px)
- [ ] Displays: rank, name, distance, elevation, score, weather
- [ ] Optimal route has gradient background and border
- [ ] Hover effect: translateX(4px) + shadow
- [ ] Click to select/deselect
- [ ] Keyboard accessible (Tab, Enter, Space)
- [ ] Screen reader friendly
- [ ] Responsive: adapts to mobile
- [ ] Reusable across all pages
- [ ] Documented in component library

**Component Spec:**
```jsx
<RouteCard
  route={route}
  rank={1}
  isOptimal={true}
  isSelected={false}
  onSelect={handleSelect}
  onFavorite={handleFavorite}
  onHide={handleHide}
/>
```

**Related Issues:** #3, #11, #12

---

### Issue #11: Implement Skeleton Screens for Loading States

**Priority:** P1-high  
**Labels:** `performance`, `loading`, `skeleton`, `P1-high`  
**Estimated Effort:** 3 days  
**Assignee:** Frontend Developer

**Problem:**
Generic spinners during loading. No context about what's loading. Feels slower than it is.

**Solution:**
Replace spinners with content-aware skeleton screens that match final layout.

**Acceptance Criteria:**
- [ ] Skeleton screens for: route cards, map, info cards
- [ ] Skeleton matches final content structure
- [ ] Smooth transition from skeleton to content
- [ ] Loading animation (shimmer effect)
- [ ] Accessible (aria-busy, aria-label)
- [ ] Reusable skeleton components
- [ ] Documented in component library

**Implementation:**
```jsx
function SkeletonRouteCard() {
  return (
    <div className="skeleton-route-card" aria-busy="true" aria-label="Loading route">
      <div className="skeleton-rank"></div>
      <div className="skeleton-info">
        <div className="skeleton-line"></div>
        <div className="skeleton-line short"></div>
      </div>
      <div className="skeleton-weather"></div>
    </div>
  );
}

// CSS
.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**Related Issues:** #12, #13

---

### Issue #12: Replace Alert Dialogs with Toast Notifications

**Priority:** P1-high  
**Labels:** `ui`, `toast`, `notifications`, `P1-high`  
**Estimated Effort:** 4 days  
**Assignee:** Frontend Developer

**Problem:**
Alert dialogs are disruptive and block workflow. Not accessible. Poor user experience.

**Solution:**
Implement non-blocking toast notification system.

**Acceptance Criteria:**
- [ ] Toast types: success, error, warning, info
- [ ] Auto-dismiss after 5 seconds (configurable)
- [ ] Manual dismiss with X button
- [ ] Multiple toasts stack vertically
- [ ] Toasts slide in from bottom-right
- [ ] Keyboard accessible (Tab, Escape)
- [ ] Screen reader announces (aria-live)
- [ ] Action buttons supported (e.g., "Undo")
- [ ] Mobile-friendly positioning
- [ ] Reusable toast component

**API:**
```javascript
// Show toast
showToast('Route favorited', 'success', {
  duration: 5000,
  action: {
    label: 'Undo',
    onClick: () => unfavoriteRoute(routeId)
  }
});

// Toast types
showToast('Success message', 'success');
showToast('Error message', 'error');
showToast('Warning message', 'warning');
showToast('Info message', 'info');
```

**Related Issues:** #8, #11, #13

---

### Issue #13: Optimize Mobile Layouts and Touch Targets

**Priority:** P1-high  
**Labels:** `mobile`, `responsive`, `touch`, `P1-high`  
**Estimated Effort:** 1.5 weeks  
**Assignee:** Frontend Developer

**Problem:**
Some tap targets below 44x44px minimum. Horizontal scrolling on mobile. Desktop-first thinking.

**Solution:**
Audit and fix all mobile layouts and touch targets.

**Acceptance Criteria:**
- [ ] All touch targets ≥ 44x44px
- [ ] No horizontal scrolling on any mobile view
- [ ] Bottom navigation bar on mobile
- [ ] Swipe gestures: swipe-to-favorite, swipe-to-hide
- [ ] Tables convert to cards on mobile
- [ ] Tested on: iPhone SE, iPhone 14, Samsung Galaxy, Pixel
- [ ] Touch accuracy ≥ 95%
- [ ] No layout breaks on any device
- [ ] Performance: 60fps scrolling

**Touch Target Audit:**
```javascript
// Audit script
document.querySelectorAll('button, a, input, select').forEach(el => {
  const rect = el.getBoundingClientRect();
  if (rect.width < 44 || rect.height < 44) {
    console.warn('Touch target too small:', el, rect);
  }
});
```

**Related Issues:** #14, #15

---

### Issue #14: Add Tooltips to All Icon Buttons

**Priority:** P1-high  
**Labels:** `accessibility`, `tooltips`, `help`, `P1-high`  
**Estimated Effort:** 3 days  
**Assignee:** Frontend Developer

**Problem:**
Icon buttons have no labels or tooltips. Users guess at functionality. Features go undiscovered.

**Solution:**
Add tooltips to all icon buttons with clear, descriptive text.

**Acceptance Criteria:**
- [ ] All icon buttons have tooltips
- [ ] Tooltips appear on hover (desktop)
- [ ] Tooltips appear on long-press (mobile)
- [ ] Tooltips are keyboard accessible
- [ ] Tooltips have sufficient contrast
- [ ] Tooltips don't block content
- [ ] Tooltips auto-dismiss after 3 seconds
- [ ] Reusable tooltip component

**Implementation:**
```jsx
<Tooltip content="Add to favorites">
  <IconButton 
    icon="star"
    onClick={handleFavorite}
    aria-label="Add to favorites"
  />
</Tooltip>
```

**Related Issues:** #4, #15

---

### Issue #15: Create First-Time User Onboarding Flow

**Priority:** P1-high  
**Labels:** `onboarding`, `ux`, `help`, `P1-high`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Developer + UX Designer

**Problem:**
New users dropped into empty application with no guidance. High abandonment rate.

**Solution:**
Create 3-5 step onboarding flow for first-time users.

**Acceptance Criteria:**
- [ ] Onboarding triggers on first visit
- [ ] 3-5 steps maximum
- [ ] Steps: Welcome → Connect Strava → View Routes → Compare Routes → Done
- [ ] Skip button on each step
- [ ] Progress indicator (1 of 5)
- [ ] Keyboard accessible
- [ ] Mobile-friendly
- [ ] Can replay from Settings
- [ ] Analytics tracking

**Onboarding Steps:**
1. **Welcome** - "Welcome to Ride Optimizer! Let's get you started."
2. **Connect Strava** - "Connect your Strava account to import routes."
3. **View Routes** - "Here are your routes. Click to see details."
4. **Compare Routes** - "Compare routes side-by-side with weather."
5. **Done** - "You're all set! Start optimizing your rides."

**Related Issues:** #14, #16

---

## Phase 3: Enhancement (P2) - Weeks 13-22

### Issue #16: Add Multi-Select Functionality for Routes

**Priority:** P2-medium  
**Labels:** `feature`, `bulk-operations`, `routes`, `P2-medium`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Developer

**Problem:**
Cannot select multiple routes. Tedious for users with many routes.

**Solution:**
Add multi-select with checkboxes and keyboard shortcuts.

**Acceptance Criteria:**
- [ ] Checkbox on each route card
- [ ] Click checkbox to select/deselect
- [ ] Ctrl/Cmd+Click to multi-select
- [ ] Shift+Click to select range
- [ ] "Select All" button
- [ ] "Deselect All" button
- [ ] Selected count indicator
- [ ] Bulk actions available when routes selected
- [ ] Keyboard accessible
- [ ] Mobile-friendly (long-press to select)

**Related Issues:** #17, #18

---

### Issue #17: Implement Bulk Actions (Hide, Favorite, Export)

**Priority:** P2-medium  
**Labels:** `feature`, `bulk-operations`, `routes`, `P2-medium`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Developer

**Problem:**
No bulk operations. Time-consuming for power users.

**Solution:**
Add bulk actions for selected routes.

**Acceptance Criteria:**
- [ ] Bulk hide routes
- [ ] Bulk favorite routes
- [ ] Bulk export routes (JSON, GPX, CSV)
- [ ] Bulk delete (with confirmation)
- [ ] Actions appear when routes selected
- [ ] Confirmation dialog for destructive actions
- [ ] Undo available for all actions
- [ ] Progress indicator for long operations
- [ ] Error handling

**Related Issues:** #16, #18, #19

---

### Issue #18: Add Keyboard Shortcuts

**Priority:** P2-medium  
**Labels:** `feature`, `keyboard`, `shortcuts`, `P2-medium`  
**Estimated Effort:** 4 days  
**Assignee:** Frontend Developer

**Problem:**
Mouse required for everything. Slow for power users.

**Solution:**
Add keyboard shortcuts for common actions.

**Acceptance Criteria:**
- [ ] Shortcuts: `?` (help), `/` (search), `f` (favorite), `h` (hide)
- [ ] Arrow keys navigate route list
- [ ] Enter selects route
- [ ] Escape deselects all
- [ ] Ctrl/Cmd+A selects all
- [ ] Shortcuts documented in help modal
- [ ] Shortcuts shown in tooltips
- [ ] Shortcuts work on all pages
- [ ] No conflicts with browser shortcuts

**Keyboard Shortcuts:**
- `?` - Show keyboard shortcuts help
- `/` - Focus search
- `f` - Toggle favorite on selected route
- `h` - Hide selected route
- `↑↓` - Navigate route list
- `Enter` - Select route
- `Escape` - Deselect all
- `Ctrl/Cmd+A` - Select all
- `Ctrl/Cmd+Click` - Multi-select

**Related Issues:** #16, #17, #19

---

### Issue #19: Create Help Documentation Site

**Priority:** P2-medium  
**Labels:** `documentation`, `help`, `P2-medium`  
**Estimated Effort:** 2 weeks  
**Assignee:** Technical Writer + Frontend Developer

**Problem:**
No help documentation. Users on their own. Support burden increases.

**Solution:**
Create comprehensive, searchable help documentation.

**Acceptance Criteria:**
- [ ] Help site accessible from navigation
- [ ] Searchable documentation
- [ ] Categories: Getting Started, Features, FAQ, Troubleshooting
- [ ] Screenshots and videos
- [ ] Keyboard shortcuts reference
- [ ] Mobile-friendly
- [ ] Accessible (WCAG AA)
- [ ] Analytics tracking

**Documentation Structure:**
```
Help
├── Getting Started
│   ├── Connect Strava
│   ├── Import Routes
│   └── First Ride
├── Features
│   ├── Route Comparison
│   ├── Weather Integration
│   ├── Favorites
│   └── Export Data
├── FAQ
│   ├── How does scoring work?
│   ├── What is wind impact?
│   └── How to delete routes?
└── Troubleshooting
    ├── Connection issues
    ├── Missing routes
    └── Performance problems
```

**Related Issues:** #14, #15, #18

---

### Issue #20: Implement Data Export (JSON, GPX, CSV)

**Priority:** P2-medium  
**Labels:** `feature`, `export`, `data`, `P2-medium`  
**Estimated Effort:** 1 week  
**Assignee:** Backend Developer + Frontend Developer

**Problem:**
Users cannot export their data. Vendor lock-in concerns.

**Solution:**
Add data export in multiple formats.

**Acceptance Criteria:**
- [ ] Export formats: JSON, GPX, CSV
- [ ] Export single route
- [ ] Export multiple routes (bulk)
- [ ] Export all routes
- [ ] Export includes: route data, weather, scores
- [ ] GPX format compatible with Garmin, Wahoo
- [ ] CSV format compatible with Excel
- [ ] Download as file
- [ ] Progress indicator for large exports
- [ ] Error handling

**Export Formats:**
- **JSON** - Complete data with all fields
- **GPX** - GPS Exchange Format (route coordinates)
- **CSV** - Spreadsheet format (route summary)

**Related Issues:** #17, #21

---

## Phase 4: Polish (P3) - Weeks 23-26

### Issue #21: Add Micro-Interactions and Animations

**Priority:** P3-low  
**Labels:** `polish`, `animations`, `delight`, `P3-low`  
**Estimated Effort:** 1 week  
**Assignee:** Frontend Developer + UX Designer

**Problem:**
Interface feels static. No delight moments.

**Solution:**
Add subtle micro-interactions and animations.

**Acceptance Criteria:**
- [ ] Button hover effects
- [ ] Route card hover effects
- [ ] Success celebrations (confetti on favorite)
- [ ] Smooth transitions (0.2-0.3s)
- [ ] Loading animations
- [ ] Scroll animations
- [ ] Respects prefers-reduced-motion
- [ ] Performance: 60fps animations

**Animations:**
- Button hover: scale(1.05) + shadow
- Route card hover: translateX(4px) + shadow
- Success: confetti animation
- Loading: skeleton shimmer
- Scroll: fade-in on scroll

**Related Issues:** #22, #23

---

### Issue #22: Create Video Tutorials for Key Workflows

**Priority:** P3-low  
**Labels:** `documentation`, `video`, `tutorials`, `P3-low`  
**Estimated Effort:** 2 weeks  
**Assignee:** Technical Writer + Video Producer

**Problem:**
Text documentation not enough for visual learners.

**Solution:**
Create video tutorials for key workflows.

**Acceptance Criteria:**
- [ ] Videos: Getting Started, Route Comparison, Weather Analysis
- [ ] Length: 2-3 minutes each
- [ ] Captions/subtitles
- [ ] Accessible player
- [ ] Embedded in help site
- [ ] YouTube channel
- [ ] Mobile-friendly

**Video Topics:**
1. Getting Started (3 min)
2. Comparing Routes (2 min)
3. Understanding Weather Impact (2 min)
4. Using Favorites (1 min)
5. Exporting Data (1 min)

**Related Issues:** #19, #23

---

### Issue #23: Conduct User Acceptance Testing

**Priority:** P3-low  
**Labels:** `testing`, `uat`, `validation`, `P3-low`  
**Estimated Effort:** 2 weeks  
**Assignee:** UX Researcher + QA Team

**Problem:**
Need to validate redesign with real users.

**Solution:**
Conduct comprehensive user acceptance testing.

**Acceptance Criteria:**
- [ ] Recruit 8-10 cyclists (mix of experience)
- [ ] Test core workflows
- [ ] Measure: task completion, time on task, errors
- [ ] Collect qualitative feedback
- [ ] Identify pain points
- [ ] Create prioritized fix list
- [ ] Report findings to team

**Test Scenarios:**
1. Find optimal route for tomorrow's commute
2. Compare 3 routes side-by-side
3. Favorite a route
4. Export route data
5. Change preferences

**Success Criteria:**
- Task completion rate ≥ 90%
- Time on task ≤ 2 minutes
- Error rate ≤ 10%
- User satisfaction ≥ 4.5/5

**Related Issues:** #21, #22, #24

---

## Summary Statistics

### By Priority
- **P0 (Critical):** 9 issues - 4 weeks
- **P1 (High):** 6 issues - 8 weeks
- **P2 (Medium):** 5 issues - 10 weeks
- **P3 (Low):** 3 issues - 4 weeks

### By Category
- **Navigation:** 3 issues
- **Layout/Viewport:** 3 issues
- **Accessibility:** 6 issues
- **Error Recovery:** 3 issues
- **Components:** 4 issues
- **Mobile:** 2 issues
- **Bulk Operations:** 3 issues
- **Documentation:** 3 issues
- **Polish:** 3 issues

### Total Effort
- **26 weeks** (6 months)
- **30 issues**
- **4 phases**

---

## Implementation Order

### Week 1-4 (P0 - Critical)
1. Issue #1: Navigation consolidation
2. Issue #2: Home page viewport optimization
3. Issue #3: Routes page side-by-side layout
4. Issue #4: ARIA labels
5. Issue #5: Focus indicators
6. Issue #6: Skip links
7. Issue #7: Auto-save
8. Issue #8: Undo functionality
9. Issue #9: Unsaved changes warning

### Week 5-12 (P1 - High)
10. Issue #10: Compact route cards
11. Issue #11: Skeleton screens
12. Issue #12: Toast notifications
13. Issue #13: Mobile optimization
14. Issue #14: Tooltips
15. Issue #15: Onboarding

### Week 13-22 (P2 - Medium)
16. Issue #16: Multi-select
17. Issue #17: Bulk actions
18. Issue #18: Keyboard shortcuts
19. Issue #19: Help documentation
20. Issue #20: Data export

### Week 23-26 (P3 - Low)
21. Issue #21: Micro-interactions
22. Issue #22: Video tutorials
23. Issue #23: User acceptance testing

---

## Next Steps

1. **Review this document** with engineering team
2. **Create GitHub issues** using templates below
3. **Assign issues** to team members
4. **Set up project board** with phases
5. **Schedule kickoff meeting** for Phase 1
6. **Begin implementation** Week 1

---

## GitHub Issue Template

```markdown
## Problem
[Clear description of the problem]

## Solution
[Proposed solution]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Implementation Notes
[Code examples, technical details]

## Related Issues
#[issue number]

## Testing Checklist
- [ ] Unit tests
- [ ] Integration tests
- [ ] Accessibility tests
- [ ] Manual testing

## Estimated Effort
[X weeks/days]

## Priority
P[0-3]-[critical/high/medium/low]
```

---

**Document Status:** Ready for Implementation  
**Last Updated:** 2026-05-08  
**Next Review:** After Phase 1 completion