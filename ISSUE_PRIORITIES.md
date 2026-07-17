# Issue Prioritization

**Last Updated:** 2026-07-17 12:53:06 UTC / 2026-07-17 12:53:06 GMT

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
- #477 - route_analyzer.py::_open_geocoding_terminal is macOS-only, silently no-ops on Windows/Linux
- #459 - Lost-update races in read-modify-write JSON flows (plan storage, TrainerRoad cache)

### 🔴 P1 - HIGH
- #493 - Explore: plotted road routes can claim zero of their highlighted new tiles — never verified against the actual route
- #489 - Explore: replace implicit round-trip with explicit route shape (Loop / Out-and-back / Point-to-point)

### 🟡 P2 - MEDIUM
- #492 - Epic: Explore Route Generator — Shape/Duration/Area Targeting, Trim Coverage-Browser Scope
- #491 - Explore: let rider draw/select a target area instead of only start-point + radius
- #490 - Explore: add duration-based route target alongside distance
- #488 - Explore: fold full-map coverage browsing into route-generation feedback; drop standalone browse mode
- #487 - Explore: audit and prune optimizeFor strategy sprawl (tiles/distance/efficiency/infill/frontier)
- #481 - /api/exploration/roads: unbounded bbox can OOM the Pi via osmnx, and road_network.graphml cache ignores requested bounds (wrong results after panning)
- #451 - Exploration route generator: extend overlap penalty to tiles claimed within the in-progress tour

### 🟢 P3 - LOW
- #482 - /api/exploration/route: waypoints not validated (500s on malformed input, no count cap → ORS quota burn) and route memo cache grows unbounded
- #453 - Exploration route generator: wind-aware outbound/return orientation (headwind out, tailwind back)
- #452 - Exploration route generator: detect and label unavoidable out-and-back routes
- #430 - Coverage tracker should include Garmin activities, not just Strava

### 📋 P4 - FUTURE
**No P4 issues** ✅

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
