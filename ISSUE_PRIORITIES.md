# Issue Prioritization

**Last Updated:** 2026-06-22 04:30:00 UTC / 2026-06-21 23:30:00 CDT

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** v0.14.0 (deployed)
- **Next Release:** v0.15.0 (in development)
- **Future Releases:** v0.16.0

---

## 🎯 v0.15.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### 🔴 P0 - CRITICAL
**No P0 issues** ✅

### 🔴 P1 - HIGH
**No P1 issues** ✅

### 🟡 P2 - MEDIUM
- ~~#307~~ - perf: reduce startup/request overhead on Pi ✅ **CLOSED** (lazy folium import, bare fetch→apiClient, degraded weather cache passthrough)
- ~~#180~~ - Add planner-specific API client methods ✅ **CLOSED** (already implemented)
- #341 - Dashboard shows commute, workout ride, and indoor options when workout is scheduled (in progress elsewhere)
- #194 - Long Rides: Add accessibility features (WCAG 2.1 AA)
- #106 - Add average speed and elevation gain metrics

### 🟢 P3 - LOW
**No P3 issues** ✅

### 📋 P4 - FUTURE
**No P4 issues** ✅

---

## 📅 v0.16.0 (Future Release)

### 🔴 P1 - HIGH
- #331 - Epic: Exploration Route Generator

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

**All issues are assigned to releases** ✅

---

## 📝 Workspace TODOs & Tasks
Code comments and inline tasks found in the workspace that may need attention.

Found **24** code comments requiring attention:

- `.claude/worktrees/agent-a039b0bc70465bc21/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a039b0bc70465bc21/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-a1cf7832d2e55e023/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a1cf7832d2e55e023/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-a260dcd623739a407/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a260dcd623739a407/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-a32b4f7cc79e6fdad/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a32b4f7cc79e6fdad/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-a580b433240d8d227/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a580b433240d8d227/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-a62dd708f4abfbafa/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a62dd708f4abfbafa/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-a7905a0b3216bd919/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a7905a0b3216bd919/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-a8407d4f64334e0cf/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-a8407d4f64334e0cf/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-aca1efd51cd5ad499/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-aca1efd51cd5ad499/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-ae19632342a95b7ee/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-ae19632342a95b7ee/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
- `.claude/worktrees/agent-ae27c24a569424fd2/app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `.claude/worktrees/agent-ae27c24a569424fd2/static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html
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
