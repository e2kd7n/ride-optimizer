# Issue Prioritization

**Last Updated:** 2026-11-08 19:30:48 UTC / 2026-11-08 13:30:48 CST

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** none (deployed, milestone fully closed)
- **Next Release:** 0.22.0 (in development)
- **Future Releases:** 

---

## 🎯 0.22.0 (Next Release - IN DEVELOPMENT)

**Priority within this release determines work order. Complete P0/P1 issues before moving to future releases.**

### 🔴 P0 - CRITICAL
**No P0 issues** ✅

### 🔴 P1 - HIGH
- #621 - Ride chat: PII sanitizer corrupts tool JSON (list_routes unparseable)

### 🟡 P2 - MEDIUM
- #636 - Garmin client: garth is deprecated — pin, wrap, or migrate

### 🟢 P3 - LOW
- #634 - Data Cleanup: Strava manual workflow (link-out checklist feeding the cache)
- #633 - Data Cleanup: review & approve page (new tab)
- #632 - Data Cleanup: reconcile activity cache + regroup after each cleanup batch
- #631 - Data Cleanup: resumable background runner for approved Garmin deletes/renames
- #630 - Data Cleanup: full Garmin history + recording-device names in GarminService
- #629 - Data Cleanup: duplicate/fragment/name-sync detection service
- #628 - Epic: Data Cleanup tab — find duplicate/unnamed activities across Garmin & Strava, fix them in the background
- #594 - Epic: RideWithGPS integration — import routes and suggest Explore tile-coverage optimizations
- #593 - RideWithGPS: publish an optimized route back as a new route
- #592 - RideWithGPS: Explore tab visualization of suggested vs. original route
- #591 - RideWithGPS: algorithm to suggest a tile-coverage-optimizing modification to an existing route
- #590 - RideWithGPS: import existing routes into the app's route model
- #589 - RideWithGPS: connect an account (auth + service scaffolding)

### 📋 P4 - FUTURE
- #635 - Spike: Strava web automation for delete/rename — go/no-go decision record
- #514 - Offload background analysis batch jobs to Pi Zero W cluster (ClusterHAT)

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

### 🔴 P0 - CRITICAL
None

### 🔴 P1 - HIGH
None

### 🟡 P2 - MEDIUM
- #623 - Gear cache emptied by 2026-10-01 refresh; gear shows raw IDs (Reports + chat)
- #622 - Ride chat: totals count runs/walks/swims as rides; no all-cycling filter
- #620 - Option to check for new activities nightly and pull them into the cache (all connected sources), then regroup
- #619 - "Backfill this month" fails when Strava isn't connected — should use whichever source is connected (e.g. Garmin)
- #617 - Match review: let the rider confirm uncertain route matches and teach the matcher
- #607 - Port Garmin integration from garth (unofficial SSO) to Garmin's official Personal API

### 🟢 P3 - LOW
- #625 - Ride chat: Strava activity IDs still sent to Claude via record URLs
- #624 - Fastest-speed record picks GPS glitches and non-ride activities
- #608 - Ride-data chat on the Reports tab (ephemeral Claude sessions, no history)

### 📋 P4 - FUTURE
None

### ⚠️ Unprioritized (No P-label)
- #626 - [BUG] mobile app screen changes away from explore

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
