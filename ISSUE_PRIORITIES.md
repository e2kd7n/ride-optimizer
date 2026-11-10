# Issue Prioritization

**Last Updated:** 2026-11-10 01:49:38 UTC / 2026-11-09 19:49:38 CST

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** none (deployed, milestone fully closed)
- **Next Release:** 0.22.0 (in development)
- **Future Releases:** 0.23.0

---

## 🎯 0.22.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### 🔴 P0 - CRITICAL
**No P0 issues** ✅

### 🔴 P1 - HIGH
- #636 - Garmin client: garth is deprecated — pin, wrap, or migrate
- #619 - "Backfill this month" fails when Strava isn't connected — should use whichever source is connected (e.g. Garmin)

### 🟡 P2 - MEDIUM
- #677 - CI: fix the pytest --ignore list, stale tests, and lock-file builds
- #664 - Job endpoints can stick at "running" until restart on bad input or init errors
- #663 - Stopped or failed analysis publishes partial route groups and shows "Done"
- #658 - Cold boot: cheap /healthz and background warm-up instead of blocking init
- #655 - Keep one parsed copy of activities.json and load it single-flight
- #637 - Explore: compute and display current yard(inho) and übersquadrat(inho)
- #623 - Gear cache emptied by 2026-10-01 refresh; gear shows raw IDs (Reports + chat)
- #622 - Ride chat: totals count runs/walks/swims as rides; no all-cycling filter
- #620 - Option to check for new activities nightly and pull them into the cache (all connected sources), then regroup

### 🟢 P3 - LOW
- #641 - Epic: Explore — optimize for yard(inho) and übersquadrat(inho) expansion
- #640 - Explore: show yard/übersquadrat deltas on every generated route card
- #630 - Data Cleanup: full Garmin history + recording-device names in GarminService
- #629 - Data Cleanup: duplicate/fragment/name-sync detection service
- #628 - Epic: Data Cleanup tab — find duplicate/unnamed activities across Garmin & Strava, fix them in the background

### 📋 P4 - FUTURE
**No P4 issues** ✅

---

## 📅 0.23.0 (Future Release)

### 🟡 P2 - MEDIUM
- #679 - Activity data model: mixed start_date formats and shared Garmin/Strava ID space
- #671 - api-client retries non-idempotent POSTs; one CSRF fetch per client instance
- #670 - Stale responses overwrite newer ones (Reports periods/calendar, Routes map and uses modal)
- #666 - WeatherFetcher caches: thread-unsafe mutation and non-atomic file writes
- #665 - Container refresh is unlocked and publishes half-initialised services
- #662 - Epic: Background jobs, analysis state and thread safety (2026-11 review)
- #659 - Tile index: integer keys, spatial buckets, drop unused fields, remove deleted activities
- #657 - Run the nightly analysis in its own process, not a thread in the gunicorn worker
- #656 - Store route geometry compactly in route_groups/long_rides caches
- #654 - Epic: Pi memory & compute efficiency (2026-11 review)
- #653 - Own router: decisions needed from the rider (regions, walking, turn control, ORS, devices)
- #647 - Own router M2: roadless (water) tiles from the graph instead of Overpass

### 🟢 P3 - LOW
- #681 - Commute map: stamp CSP nonces server-side instead of regex-rewriting Folium HTML
- #680 - Strava status endpoint does a network token refresh on every poll
- #678 - Remove CLI-era and dead code (main.py, optimizer, Folium visualizer, osascript geocoding)
- #676 - Epic: Dead code, CI hygiene and build reproducibility (2026-11 review)
- #675 - Frontend low-priority fixes bundle (2026-11 review)
- #674 - Explore rectangle drawing is mouse-only and freezes the map on touch
- #673 - Settings: intervals.icu and ORS disconnect buttons stack duplicate listeners
- #672 - Units ignore the metric/imperial setting on most pages
- #669 - Epic: Frontend correctness, units and mobile polish (2026-11 review)
- #668 - JSON read-modify-write gaps: corrupt-file default, settings and job history
- #667 - Chunked ORS routes get a fresh time budget per chunk
- #661 - Explore: bound client-side coverage caches and per-render cost
- #660 - Static assets: content-hash versioning and long-lived caching
- #650 - Own router M5: full local planner replaces Phase 1 + Phase 2 in covered regions
- #649 - Own router M4: cluster cover on the graph (cluster rule by construction)
- #648 - Own router M3: turn-aware A→B routing in a browser Web Worker

### 📋 P4 - FUTURE
- #652 - Own router M7: retire superseded Phase 1/2 + ORS-only paths inside covered regions
- #651 - Own router M6: route options UI — straighter↔more tiles, walking connections, busy roads

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

**All issues are assigned to releases** ✅

---

## 📝 Workspace TODOs & Tasks
Code comments and inline tasks found in the workspace that may need attention.

**No TODO/FIXME comments found in code** ✅

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
# macOS / Linux / Git Bash — output written directly to ISSUE_PRIORITIES.md
./scripts/update-issue-priorities.sh

# Windows (PowerShell) — run via Git Bash, not WSL:
# WSL's git can't resolve a worktree's .git file when it holds a Windows-style
# absolute gitdir path (as git-for-windows writes), so it fails with
# 'fatal: not a git repository'. Git Bash's git is git-for-windows and handles
# this correctly.
bash ./scripts/update-issue-priorities.sh
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
