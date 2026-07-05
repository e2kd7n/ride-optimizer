# Issue Prioritization

**Last Updated:** 2026-07-05 02:46:26 UTC / 2026-07-04 21:46:26 CDT

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** v0.16.0 (deployed, milestone fully closed)
- **Next Release:** v0.17.0 (in development)
- **Future Releases:** 

---

## 🎯 v0.17.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### 🔴 P0 - CRITICAL
**No P0 issues** ✅

### 🔴 P1 - HIGH
- #361 - [Design Review] Explore: add numbered workflow steps and progressive button enablement
- #360 - [Design Review] Explore: add tile/Squadrats concept explainer and coverage legend
- #359 - [Design Review] Route Detail: replace raw JSON weather dump with formatted card
- #358 - [Design Review] Dashboard: fix mobile column stacking and widen decision panel
- #357 - [Design Review] Weather: swap 7-day forecast and same-day commute windows order
- #352 - Epic: Design Review — Information Density, Discoverability & Card Placement

### 🟡 P2 - MEDIUM
- #375 - [Design Review] Apply unit system preference to temperature slider, Reports distance label, and Explore distance slider
- #374 - [Design Review] Ship or gracefully degrade help modal tutorial assets
- #373 - [Design Review] Weather: add comfort score legend; fix hardcoded commute window time labels
- #372 - [Design Review] Routes Library: label compare checkbox; add entry-point for Saved Plans
- #370 - [Design Review] Dashboard: add affordance labels and count badges to collapse toggles
- #371 - [Design Review] Route Detail: demote Uses metric; surface performance charts above history tables
- #369 - [Design Review] Reports: hide empty secondary stats; move admin gear buttons to Settings
- #368 - [Design Review] Settings: split Connections card; nest Outdoor Prefs; move Save above About
- #367 - [Design Review] Explore: move coverage stats below map; merge controls into route generation card
- #366 - [Design Review] Reports: reorder cards — Activities before Gear; consolidate chart cards
- #365 - [Design Review] Routes Library: invert column ratio to give route list more space than map
- #363 - [Design Review] Dashboard: relocate 'How It Works' button out of above-the-fold content
- #364 - [Design Review] Routes Library: collapse advanced filters behind 'More Filters' toggle
- #362 - [Design Review] Navigation: add Reports and Explore to mobile bottom nav

### 🟢 P3 - LOW
- #376 - [Design Review] P3 polish bundle: stale versions, missing H1s, a11y minor, UX polish items

### 📋 P4 - FUTURE
**No P4 issues** ✅

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

### 🔴 P0 - CRITICAL
None

### 🔴 P1 - HIGH
None

### 🟡 P2 - MEDIUM
None

### 🟢 P3 - LOW
None

### 📋 P4 - FUTURE
None

### ⚠️ Unprioritized (No P-label)
- #345 - [FEATURE] Manage and monitor python launch.py dev server processes (no PID tracking, kill_existing_server is a no-op on Windows)

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
