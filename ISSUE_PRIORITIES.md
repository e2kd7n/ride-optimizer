# Issue Prioritization

**Last Updated:** 2026-09-20 00:03:37 UTC / 2026-09-20 00:03:37 GMT

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** v0.19.0 (deployed, milestone fully closed)
- **Next Release:** v0.18.0 (in development)
- **Future Releases:** 

---

## 🎯 v0.18.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### 🔴 P0 - CRITICAL
**No P0 issues** ✅

### 🔴 P1 - HIGH
**No P1 issues** ✅

### 🟡 P2 - MEDIUM
**No P2 issues** ✅

### 🟢 P3 - LOW
- #514 - Offload background analysis batch jobs to Pi Zero W cluster (ClusterHAT)

### 📋 P4 - FUTURE
**No P4 issues** ✅

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

### 🔴 P0 - CRITICAL
- #571 - Nightly cron wipes the tile index after every activity sync — the actual root cause of cold rebuilds, not the #555 cache sweep
- #570 - Explore tab: fix route-generation failures and multi-minute stalls on real rides
- #563 - Explore: client stacks 3x45s timeouts on coverage requests — a slow backend can hang silently for ~2 minutes
- #558 - Explore: single global lock across all zoom levels serializes coverage requests behind cold-start rebuilds

### 🔴 P1 - HIGH
- #598 - Single 4-thread gunicorn worker can starve the whole app for minutes when an external API (Overpass) is slow
- #597 - pi-auto-update.sh pulls the image but never syncs the host checkout, so bind-mounted config.yaml drifts silently
- #595 - Non-corridor coverage fetch sends unclamped map viewport as bbox, can exceed backend's 0.5° limit
- #584 - computeCorridorBoxes' own padding can push a segment past the backend's bbox limit, causing an unretried 400
- #583 - CoverageTracker._activities_cache never refreshes on its own — blocks #571's soft-invalidate fix from being safe
- #576 - POST /api/exploration/invalidate has no rate limit and reproduces the full cold-rebuild incident on demand via Clear Cache
- #573 - ExplorationService.initialize() never runs in production — persisted route cache never loads despite being written on every route
- #572 - get_exploration_service() is not thread-safe — concurrent requests can construct duplicate CoverageTrackers
- #567 - Explore: silent water/roadless-exclusion failure can suggest un-rideable (open-water) tiles
- #565 - Explore: generate-then-plot flow requires too many manual taps for a mid-ride rider
- #564 - Explore: coverage load failures show no toast or retry affordance
- #560 - Explore: cold-start tile index rebuild runs synchronously on the first request after every restart

### 🟡 P2 - MEDIUM
- #600 - Explore tile rendering waits on the roadless/water-polygon fetch for no reason
- #580 - Explore rate limits don't match real call volume — legitimate use self-inflicts 429s that get silently swallowed
- #579 - Coverage tile-grid responses and rendering ship/draw far more data than used — payload bloat and 65k-rectangle map freeze
- #578 - compute_route's first ORS attempt ignores the remaining wall-clock budget — can still approach gunicorn's 60s timeout
- #577 - ExplorationService._route_cache is mutated from multiple threads with no lock — same crash class as #559
- #574 - get_roadless_tiles is an unbounded O(tiles x polygon points) pure-Python sweep with no bbox prefilter (perf, not the 2026-09-11 cause)
- #566 - Explore: loading/slow-hint copy is static, doesn't reflect elapsed time or actual failure cause
- #562 - Overpass water-polygon fetch has no retry/backoff or negative-cache, ties up a thread for up to 30s per failure

### 🟢 P3 - LOW
- #601 - CI build workflow doesn't trigger on templates/** changes
- #594 - Epic: RideWithGPS integration — import routes and suggest Explore tile-coverage optimizations
- #593 - RideWithGPS: publish an optimized route back as a new route
- #592 - RideWithGPS: Explore tab visualization of suggested vs. original route
- #591 - RideWithGPS: algorithm to suggest a tile-coverage-optimizing modification to an existing route
- #590 - RideWithGPS: import existing routes into the app's route model
- #589 - RideWithGPS: connect an account (auth + service scaffolding)
- #588 - Settings analysis 'Done' summary drops long_rides_count from the same result object it reads counts from
- #586 - Commute-window weather card averages away the hourly breakdown it already fetched
- #585 - Explore route detail: "N new tiles" doesn't distinguish squadrats from squadratinhos
- #582 - Config keys referenced in code but missing from config.yaml, plus stale docstrings/comments in the coverage/exploration subsystem
- #581 - Dead road-coverage feature (~200 lines): osmnx/shapely not installed, no frontend caller
- #569 - Explore route/tile color palette drifts from the documented Fair Weather brand palette
- #568 - Explore: no offline/last-known-good cached fallback when a load fails

### 📋 P4 - FUTURE
None

### ⚠️ Unprioritized (No P-label)
- #526 - Add HTTPS/TLS to Pi deployment (required for geolocation and other secure-context APIs)

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
