# Issue Prioritization

**Last Updated:** 2026-05-14 20:39:15 UTC / 2026-05-14 15:39:15 CDT

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** v0.12.0 (deployed)
- **Next Release:** v0.13.0 (in development)
- **Future Releases:** v0.14.0

---

## 🎯 v0.13.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### 🔴 P0 - CRITICAL
**No P0 issues** ✅

### 🔴 P1 - HIGH
**No P1 issues** ✅

### 🟡 P2 - MEDIUM
- #274 - Add Last Updated Timestamps
- #272 - Add Hourly Weather Forecast
- #263 - Refine Settings Form Structure
- #227 - Improve Test Coverage for New Features
- #194 - Long Rides: Add accessibility features (WCAG 2.1 AA)
- #141 - Add repeat-a-past-ride flow and saved plan support
- #122 - [LOW PRIORITY] Grey out unselected routes on map when route is clicked
- #121 - [LOW PRIORITY] Color code route names to match map line colors
- #116 - Add visual weather icons and color coding
- #115 - Display optimal departure time suggestions
- #114 - Add transit recommendations when conditions are poor
- #113 - Show optimal route recommendations based on wind
- #112 - Add weather severity indicators (good/fair/poor/miserable icons)
- #111 - Add evening commute window (3-6 PM) weather display
- #110 - Add morning commute window (7-9 AM) weather display
- #109 - Design 7-day forecast card layout
- #108 - Integrate forecast generator into main.py workflow
- #107 - Add interactive map showing all long ride routes
- #106 - Add average speed and elevation gain metrics
- #105 - Add monthly ride statistics breakdown
- #94 - Implement Accessibility Improvements
- #93 - Implement Comprehensive Error States
- #92 - Add Loading States with Skeleton Loaders

### 🟢 P3 - LOW
- #200 - Route naming improvements (Start → Main → End format)
- #169 - Design: Verify WCAG AA contrast ratios (4.5:1)
- #145 - 🌤️ EPIC: Weather Dashboard & Forecast Integration
- #120 - [LOW PRIORITY] Debug and fix Bootstrap tab switching functionality
- #54 - Weather Dashboard Implementation (Epic)
- #48 - Implement Data Export in JSON, GPX, and CSV Formats

### 📋 P4 - FUTURE
- #68 - ✨ Visual Hierarchy & Polish
- #66 - 🎓 Feature Discovery & Onboarding
- #64 - 📊 Progressive Disclosure for Metrics
- #62 - 🎨 EPIC: Mobile-First UI/UX Redesign & Accessibility
- #47 - Add Side-by-Side Route Comparison Feature
- #39 - Evaluate Photon API as Nominatim alternative
- #38 - Add social features (compare with other commuters)
- #37 - Add real-time route suggestions
- #35 - Add integration with other fitness platforms

---

## 📅 v0.14.0 (Future Release)

### 🔴 P1 - HIGH
- #226 - Fix Planner Error Handling Test
- #224 - Fix Route Library Search API Response Format
- #208 - Create test data fixtures for integration testing
- #206 - Implement lazy service initialization to fix performance issues
- #205 - Create missing QA test harnesses for dashboard, commute, and planner
- #172 - Add Marshmallow validation schemas for planner endpoints
- #171 - Build planner frontend UI (currently placeholder only)
- #163 - Test Coverage: data_fetcher.py (49% → 80%)
- #162 - Test Coverage: long_ride_analyzer.py (13% → 50%)
- #161 - Test Coverage: route_analyzer.py (20% → 50%)

### 🟡 P2 - MEDIUM
- #209 - Implement graceful degradation for unavailable services
- #207 - Implement dependency injection pattern for better testability
- #193 - Long Rides: Implement skeleton loaders and error states
- #192 - Establish PR review requirements
- #187 - Testing: Increase Route Namer coverage 15% → 50%
- #186 - Testing: Increase Route Analyzer coverage 20% → 50%
- #185 - Testing: Increase Data Fetcher coverage 49% → 80%
- #184 - Testing: Increase Long Ride Analyzer coverage 13% → 50%
- #183 - Code Quality: Add debug logging for exception handlers
- #182 - Code Quality: Replace 4 bare except statements with specific exceptions
- #180 - Add planner-specific API client methods
- #165 - Test Coverage: route_namer.py (15% → 50%)

### 🟢 P3 - LOW
- #199 - Design: Test on real iOS/Android devices
- #196 - Design: Ensure touch targets ≥44x44px with 8px spacing
- #195 - Design: Verify mobile-first responsive design (320px viewport)
- #170 - Design: Test keyboard navigation and screen reader support

### 📋 P4 - FUTURE
- #203 - Implement GDPR-compliant data deletion endpoint
- #144 - 🌐 EPIC: Personal Web Platform Migration (v3.0.0)

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

### 🔴 P0 - CRITICAL
None

### 🔴 P1 - HIGH
- #260 - Implement guided FTUE for Strava API key setup with in-app configuration
- #254 - Implement Animated GIF Tutorials for Key Features

### 🟡 P2 - MEDIUM
None

### 🟢 P3 - LOW
None

### 📋 P4 - FUTURE
None

### ⚠️ Unprioritized (No P-label)
None

---

## 📝 Workspace TODOs & Tasks
Code comments and inline tasks found in the workspace that may need attention.

Found **2** code comments requiring attention:

- `app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html

## 📖 Priority System (Release-Aware)

**Key Principle:** Priority is now WITHIN a release. A P1 issue in the next release takes precedence over a P0 issue in a future release.

### Work Order Priority

1. **Next Release P0** - Drop everything
2. **Next Release P1** - Current sprint focus
3. **Next Release P2** - Next sprint planning
4. **Next Release P3** - Backlog for this release
5. **Future Release P0** - Plan for future critical work
6. **Future Release P1+** - Long-term planning

### Priority Definitions (Within a Release)

#### 🔴 P0 - CRITICAL
- Application is down or unusable
- Data loss or corruption
- Security vulnerabilities
- Blocks release deployment
- **Action:** Drop everything and fix immediately

#### 🔴 P1 - HIGH
- Core features broken or severely degraded
- Significant user pain points
- Blocks important workflows
- Must complete before release
- **Action:** Fix in current sprint (1-2 weeks)

#### 🟡 P2 - MEDIUM
- Feature improvements
- Moderate user pain points
- Quality of life enhancements
- Should complete for release
- **Action:** Plan for next sprint (2-4 weeks)

#### 🟢 P3 - LOW
- Minor UX improvements
- Edge cases
- Nice-to-have features
- Can defer to next release if needed
- **Action:** Backlog, address when time permits

#### 📋 P4 - FUTURE
- New features for later releases
- Major enhancements
- Long-term improvements
- Explicitly deferred
- **Action:** Plan for future releases

## 🔄 How to Update Priorities

### 1. Assign to Release Milestone
```bash
gh issue edit <issue_num> --milestone "v0.13.0"
```

### 2. Set Priority Within Release
```bash
gh issue edit <issue_num> --add-label "P1-high"
```

### 3. Regenerate This File
```bash
./scripts/update-issue-priorities.sh
```

### 4. Commit and Communicate
```bash
git add ISSUE_PRIORITIES.md
git commit -m "Update issue priorities for <release>"
```

## 📝 Managing Workspace TODOs

- Review code comments regularly and convert important ones to GitHub issues
- Use `TODO:` for tasks that should become issues
- Use `FIXME:` for bugs that need attention
- Use `HACK:` for temporary solutions that need proper fixes
- Use `NOTE:` for important information or context

## 🎯 Release Planning Guidelines

- **Assign milestones early** - Every issue should have a target release
- **Prioritize within release** - Focus on P0/P1 issues for next release first
- **Defer strategically** - Move P3/P4 issues to future releases if needed
- **Review regularly** - Run this script weekly to track progress
