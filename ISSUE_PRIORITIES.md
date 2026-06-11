# Issue Prioritization

**Last Updated:** 2026-06-11 20:19:09 UTC / 2026-06-11 15:19:09 CDT

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## ≡ƒôì Release Context

- **Current Release:** v0.14.0 (deployed)
- **Next Release:** v0.14.0 (in development)
- **Future Releases:** v0.15.0

---

## ≡ƒÄ» v0.14.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### ≡ƒö┤ P0 - CRITICAL
**No P0 issues** Γ£à

### ≡ƒö┤ P1 - HIGH
- #208 - Create test data fixtures for integration testing
- #163 - Test Coverage: data_fetcher.py (49% ΓåÆ 80%)
- #162 - Test Coverage: long_ride_analyzer.py (13% ΓåÆ 50%)
- #161 - Test Coverage: route_analyzer.py (20% ΓåÆ 50%)
- #118 - Re-enable geocoding after rate limit expires
- #114 - Add transit recommendations when conditions are poor
- #89 - Add Data Persistence Layer for API

### ≡ƒƒí P2 - MEDIUM
- #300 - Test coverage gaps: wire up broken test files and fix pre-existing mock failures
- #272 - Add Hourly Weather Forecast
- #264 - Dashboard and Route Library UX Review
- #227 - Improve Test Coverage for New Features
- #209 - Implement graceful degradation for unavailable services
- #207 - Implement dependency injection pattern for better testability
- #192 - Establish PR review requirements
- #187 - Testing: Increase Route Namer coverage 15% ΓåÆ 50%
- #186 - Testing: Increase Route Analyzer coverage 20% ΓåÆ 50%
- #185 - Testing: Increase Data Fetcher coverage 49% ΓåÆ 80%
- #184 - Testing: Increase Long Ride Analyzer coverage 13% ΓåÆ 50%
- #183 - Code Quality: Add debug logging for exception handlers
- #182 - Code Quality: Replace 4 bare except statements with specific exceptions
- #165 - Test Coverage: route_namer.py (15% ΓåÆ 50%)
- #136 - Implement settings and preferences page for home/work locations, units, time windows, and planner defaults
- #108 - Integrate forecast generator into main.py workflow
- #105 - Add monthly ride statistics breakdown
- #94 - Implement Accessibility Improvements

### ≡ƒƒó P3 - LOW
- #200 - Route naming improvements (Start ΓåÆ Main ΓåÆ End format)
- #199 - Design: Test on real iOS/Android devices
- #196 - Design: Ensure touch targets ΓëÑ44x44px with 8px spacing
- #195 - Design: Verify mobile-first responsive design (320px viewport)
- #177 - UI/UX: Add clickable 'Uses' column with modal
- #170 - Design: Test keyboard navigation and screen reader support
- #145 - ≡ƒîñ∩╕Å EPIC: Weather Dashboard & Forecast Integration
- #120 - [LOW PRIORITY] Debug and fix Bootstrap tab switching functionality
- #54 - Weather Dashboard Implementation (Epic)

### ≡ƒôï P4 - FUTURE
- #203 - Implement GDPR-compliant data deletion endpoint
- #79 - Add "How It Works" Modal
- #68 - Γ£¿ Visual Hierarchy & Polish
- #66 - ≡ƒÄô Feature Discovery & Onboarding
- #64 - ≡ƒôè Progressive Disclosure for Metrics
- #62 - ≡ƒÄ¿ EPIC: Mobile-First UI/UX Redesign & Accessibility
- #47 - Add Side-by-Side Route Comparison Feature
- #39 - Evaluate Photon API as Nominatim alternative
- #38 - Add social features (compare with other commuters)
- #37 - Add real-time route suggestions
- #35 - Add integration with other fitness platforms

---

## ≡ƒôà v0.15.0 (Future Release)

### ≡ƒö┤ P1 - HIGH
- #172 - Add Marshmallow validation schemas for planner endpoints

### ≡ƒƒí P2 - MEDIUM
- #193 - Long Rides: Implement skeleton loaders and error states
- #180 - Add planner-specific API client methods
- #141 - Add repeat-a-past-ride flow and saved plan support
- #107 - Add interactive map showing all long ride routes
- #106 - Add average speed and elevation gain metrics

---

## ΓÜá∩╕Å Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

### ≡ƒö┤ P0 - CRITICAL
None

### ≡ƒö┤ P1 - HIGH
- #305 - bug: analysis results silently lost on restart ΓÇö _save_to_cache() never called
- #260 - Implement guided FTUE for Strava API key setup with in-app configuration
- #254 - Implement Animated GIF Tutorials for Key Features

### ≡ƒƒí P2 - MEDIUM
- #307 - perf: reduce startup cost and per-request overhead on Pi
- #306 - chore: dead code cleanup ΓÇö unused modules, methods, and imports
- #194 - Long Rides: Add accessibility features (WCAG 2.1 AA)

### ≡ƒƒó P3 - LOW
None

### ≡ƒôï P4 - FUTURE
None

### ΓÜá∩╕Å Unprioritized (No P-label)
- #304 - UX: usability findings from senior designer review (PR #303 + recent commits)

---

## ≡ƒô¥ Workspace TODOs & Tasks
Code comments and inline tasks found in the workspace that may need attention.

Found **4** code comments requiring attention:

- `.claude/worktrees/pedantic-spence-1b1a3d/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/pedantic-spence-1b1a3d/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html

## ≡ƒôû Priority System (Release-Aware)

**Key Principle:** Priority is now WITHIN a release. A P1 issue in the next release takes precedence over a P0 issue in a future release.

### Work Order Priority

1. **Next Release P0** - Drop everything
2. **Next Release P1** - Current sprint focus
3. **Next Release P2** - Next sprint planning
4. **Next Release P3** - Backlog for this release
5. **Future Release P0** - Plan for future critical work
6. **Future Release P1+** - Long-term planning

### Priority Definitions (Within a Release)

#### ≡ƒö┤ P0 - CRITICAL
- Application is down or unusable
- Data loss or corruption
- Security vulnerabilities
- Blocks release deployment
- **Action:** Drop everything and fix immediately

#### ≡ƒö┤ P1 - HIGH
- Core features broken or severely degraded
- Significant user pain points
- Blocks important workflows
- Must complete before release
- **Action:** Fix in current sprint (1-2 weeks)

#### ≡ƒƒí P2 - MEDIUM
- Feature improvements
- Moderate user pain points
- Quality of life enhancements
- Should complete for release
- **Action:** Plan for next sprint (2-4 weeks)

#### ≡ƒƒó P3 - LOW
- Minor UX improvements
- Edge cases
- Nice-to-have features
- Can defer to next release if needed
- **Action:** Backlog, address when time permits

#### ≡ƒôï P4 - FUTURE
- New features for later releases
- Major enhancements
- Long-term improvements
- Explicitly deferred
- **Action:** Plan for future releases

## ≡ƒöä How to Update Priorities

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

## ≡ƒô¥ Managing Workspace TODOs

- Review code comments regularly and convert important ones to GitHub issues
- Use `TODO:` for tasks that should become issues
- Use `FIXME:` for bugs that need attention
- Use `HACK:` for temporary solutions that need proper fixes
- Use `NOTE:` for important information or context

## ≡ƒÄ» Release Planning Guidelines

- **Assign milestones early** - Every issue should have a target release
- **Prioritize within release** - Focus on P0/P1 issues for next release first
- **Defer strategically** - Move P3/P4 issues to future releases if needed
- **Review regularly** - Run this script weekly to track progress
