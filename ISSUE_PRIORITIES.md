# Issue Prioritization

**Last Updated:** 2026-06-21

This file reflects the current state of GitHub issues organized by release milestone and priority within each release.

**Priority is now WITHIN a release** - P0/P1 issues in the current release take precedence over all issues in future releases.

## 📍 Release Context

- **Current Release:** v0.14.0 (21 open issues, 44 closed — P2 complete, P3/P4 remain)
- **Next Release:** v0.15.0
- **Future Releases:** v0.16.0

---

## 🎯 v0.14.0 (Current Release)

**All P2 issues complete.** Remaining issues are P3 (nice-to-have) and P4 (deferred).

### 🟡 P2 - MEDIUM ✅ COMPLETE
- ~~#298~~ - ✅ Bumped GitHub Actions to Node.js 24 (v5/v4/v6/v7)
- ~~#272~~ - ✅ Added hourly weather forecast endpoint + dashboard UI
- ~~#94~~ - ✅ Accessibility audit, ARIA fixes, 75 new tests
- ~~#209~~ - ✅ Graceful degradation — individual service init, 503 guards on all endpoints
- ~~#108~~ - ✅ Closed (targets deprecated main.py CLI)
- #207 - Deferred to v0.15.0 (DI refactor)
- #136 - Deferred to v0.15.0 (settings persistence)

### 🟢 P3 - LOW
- #261 - Senior Engineer Code Review Request
- #200 - Route naming improvements (Start → Main → End format)
- #199 - Design: Test on real iOS/Android devices
- #195 - Design: Verify mobile-first responsive design (320px viewport)
- #177 - UI/UX: Add clickable 'Uses' column with modal
- #170 - Design: Test keyboard navigation and screen reader support
- #145 - 🌤️ EPIC: Weather Dashboard & Forecast Integration
- #120 - [LOW PRIORITY] Debug and fix Bootstrap tab switching functionality

### 📋 P4 - FUTURE
- #203 - Implement GDPR-compliant data deletion endpoint
- #79 - Add "How It Works" Modal
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

## 📅 v0.15.0 (Next Release)

### 🔴 P1 - HIGH
- #260 - Implement guided FTUE for Strava API key setup with in-app configuration
- #254 - Implement Animated GIF Tutorials for Key Features
- #172 - Add Marshmallow validation schemas for planner endpoints

### 🟡 P2 - MEDIUM
- #330 - Complete ntfy.sh push notification integration
- #322 - Unify route comparison pipelines between commute and long ride analyzers
- #307 - perf: reduce startup cost and per-request overhead on Pi
- #194 - Long Rides: Add accessibility features (WCAG 2.1 AA)
- #193 - Long Rides: Implement skeleton loaders and error states
- #180 - Add planner-specific API client methods
- #141 - Add repeat-a-past-ride flow and saved plan support
- #106 - Add average speed and elevation gain metrics

### 🟢 P3 - LOW
- #321 - feat: Garmin Connect integration — graceful FTUE for connecting and harvesting

---

## 📅 v0.16.0 (Future Release)

### 🟡 P2 - MEDIUM
- #275 - Major refactor: Centralize configuration and extract monolithic services
- #284 - Long Rides: build new v0.15.0 implementation plan
- #282 - 🚴 Epic: Long Rides feature re-planning and implementation

---

## ⚠️ Issues Without Release Assignment

These issues need to be assigned to a release milestone and prioritized.

**All issues are assigned to releases** ✅

---

## 📝 Workspace TODOs & Tasks
Code comments and inline tasks found in the workspace that may need attention.

Found **1** code comment requiring attention:

- `app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)

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
