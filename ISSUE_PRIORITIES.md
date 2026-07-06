# Issue Prioritization

**Last Updated:** 2026-07-06 03:56:53 UTC / 2026-07-05 22:56:53 CDT

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** none (deployed, milestone fully closed)
- **Next Release:** v0.17.0 (in development)
- **Future Releases:** 

---

## 🎯 v0.17.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### 🔴 P0 - CRITICAL
**No P0 issues** ✅

### 🔴 P1 - HIGH
**No P1 issues** ✅

### 🟡 P2 - MEDIUM
- #444 - Wire static/js/mobile.js into all 7 pages (bottom nav keyboard/swipe/touch support)
- #428 - Phase 4i: Extract strava_bp Blueprint (/api/strava/*, /api/setup/*)
- #427 - Phase 4h: Extract integrations_bp Blueprint (/api/intervals/*, /api/ors/*, /api/garmin/*, /api/trainerroad/*)
- #426 - Phase 4g: Extract data_bp Blueprint (/api/analyze/*, /api/fetch/*, /api/cache-info, /api/activities)
- #425 - Phase 4f: Extract commute_bp Blueprint (/api/commute, /api/recommendation, /api/workout-options)
- #424 - Phase 4e: Extract core_bp Blueprint (/api/status, /api/settings/*, /api/plans/*, /api/user/*)
- #423 - Phase 4d: Extract planner_bp Blueprint (/api/planner/*, /api/exploration/*, /api/geocode)
- #422 - Phase 4c: Extract weather_bp Blueprint (/api/weather/*)
- #421 - Phase 4b: Extract routes_bp Blueprint (/api/routes/*)
- #420 - Phase 4a: Extract stats_bp Blueprint (/api/stats/*)
- #418 - Phase 5: Thin launch.py — wire create_app(), reduce to ~120 lines
- #416 - Phase 3: Parallel service initialisation via ServiceContainer
- #415 - Phase 2: Extract infrastructure — credentials, env helpers, process management
- #413 - Epic: launch.py Blueprint Refactor — Split 3,404-line monolith into 9 focused Blueprints
- #402 - Explore: support round-trip vs. point-to-point route type with configurable endpoint

### 🟢 P3 - LOW
- #443 - PR #431: bottom-nav-more drawer markup duplicated across 7 pages
- #430 - Coverage tracker should include Garmin activities, not just Strava
- #419 - Phase 6: Cleanup — remove dead code, update AGENTS.md architecture section

### 📋 P4 - FUTURE
**No P4 issues** ✅

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

**All issues are assigned to releases** ✅

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
# macOS / Linux / WSL — output written directly to ISSUE_PRIORITIES.md
./scripts/update-issue-priorities.sh

# Windows (PowerShell) — same command, no redirect needed
wsl bash ./scripts/update-issue-priorities.sh
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
