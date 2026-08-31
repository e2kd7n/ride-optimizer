# Weekly Maintenance Tasks

## Purpose
This document defines recurring maintenance tasks to keep project documentation synchronized with the codebase.

## Parallel Task Execution

**For Long-Running Tasks:** Some maintenance tasks (like issue management, comprehensive audits, or bulk updates) can take significant time. To avoid blocking other work:

### Run in Separate Terminals
```bash
# Terminal 1: Issue management (can take 10-30 minutes)
./scripts/update-issue-priorities.sh

# Terminal 2: Continue with other maintenance tasks
# Documentation updates, code reviews, etc.
```

### Background Task Pattern
```bash
# Start long-running task in background
./scripts/update-issue-priorities.sh > logs/issue-update.log 2>&1 &

# Note the process ID
echo $! > /tmp/maintenance-task.pid

# Continue with other work
# Check progress: tail -f logs/issue-update.log
# Check if complete: ps -p $(cat /tmp/maintenance-task.pid)
```

### Tasks That Benefit from Parallel Execution
- **Issue Management** (10-30 min): `./scripts/update-issue-priorities.sh`
- **GitHub Label Sync** (5-10 min): `./scripts/sync-github-labels.sh`
- **Test Suite** (5-15 min): `./scripts/run-tests.sh all`
- **Dependency Updates** (5-10 min): `pip list --outdated`
- **Security Scans** (2-5 min): `safety check`

### Quick Tasks (Run Inline)
- Version reference updates (1-2 min)
- Documentation edits (2-5 min)
- Git operations (1-2 min)
- File renames (1-2 min)

---

## Weekly Tasks (Every 7 Days)

### 1. Documentation Sync Review
**Frequency:** Weekly (every Monday or first work day of week)
**Estimated Time:** 30-45 minutes (excluding parallel tasks)

#### Tasks:
1. **Review Project Plan (PLAN.md)**
   - Compare planned features vs implemented features
   - Update status of completed items
   - Add new features that were implemented
   - Remove or archive obsolete items
   - Update timeline estimates

2. **Review Technical Specifications (TECHNICAL_SPEC.md)**
   - Verify module descriptions match current implementation
   - Update API signatures if changed
   - Document new modules or classes added
   - Update data flow diagrams if architecture changed
   - Verify dependencies list is current

3. **Review Implementation Guide (IMPLEMENTATION_GUIDE.md)**
   - Update setup instructions if changed
   - Verify all code examples still work
   - Add new configuration options
   - Update troubleshooting section

4. **Review Workflow Documentation (WORKFLOW.md)**
   - Ensure workflow matches current practices
   - Update any changed processes
   - Add new workflows if introduced

5. **Review Time Tracking (TIME_TRACKING.md)**
   - Update time spent on tasks completed this week
   - Analyze actual vs estimated time
   - Document lessons learned
   - Update future estimates based on actual data
   - Calculate velocity and productivity metrics

6. **Code-to-Doc Verification**
   - Read through main modules (src/*.py)
   - Check if any new features need documentation
   - Verify docstrings match documentation
   - Update examples if API changed

#### Checklist:
- [ ] Read PLAN.md and compare with current codebase
- [ ] Read TECHNICAL_SPEC.md and verify accuracy
- [ ] Review TIME_TRACKING.md and update time entries
- [ ] Analyze time tracking data for insights
- [ ] Check all module imports and dependencies
- [ ] Verify configuration examples in docs
- [ ] Test code examples in documentation
- [ ] Update version numbers if applicable
- [ ] Commit documentation updates with clear message

#### Git Commit Template:
```bash
git commit -m "docs: Weekly sync - Update project documentation

- Updated PLAN.md with current implementation status
- Synced TECHNICAL_SPEC.md with codebase changes
- Verified all code examples and configurations
- [Add specific changes made]

Weekly maintenance: [Date]"
```

## Monthly Tasks (Every 30 Days)

### 1. Comprehensive Documentation Audit
- Review all markdown files for accuracy
- Check for broken links
- Update screenshots if UI changed
- Review and update README.md
- Update requirements.txt if dependencies changed

### 2. Code Quality Review
- Run linting tools
- Check for deprecated dependencies
- Review error handling patterns
- Update type hints if needed

## Automation

`scripts/weekly-maintenance.sh` (backups, git/branch/worktree hygiene, issue-priority
regeneration via `scripts/update-issue-priorities.sh`, ntfy summary) automates most of the
weekly checklist above. It's runnable two ways:

**Interactively**, on a dev machine with an existing `gh auth login` session:
```bash
./scripts/weekly-maintenance.sh
```
This never auto-commits — `ISSUE_PRIORITIES.md` and this file's "Last Sync Date" section are
regenerated locally, left for you to review and commit by hand.

**Unattended, via cron on pi4** — `cron/crontab.template` installs it Sundays at 5 AM, run as
host bash directly (not `podman exec`, unlike the app's own cron jobs: it needs `git`/`gh`/`jq`
against the host checkout itself, not the containerized app's bind-mounted `data/`/`config/`).
The cron entry sets `AUTO_COMMIT_MAINTENANCE=true`, which is the only thing that makes this path
auto-commit and push `ISSUE_PRIORITIES.md` and this file — off by default so the same script
never surprises an interactive run.

Requirements for the unattended path:
- `GH_TOKEN` set in the Pi's `.env` (see `.env.example`) — cron has no `gh auth login` session,
  so every `gh` call (branch/PR evaluation, worktree pruning, issue-priority regen, the backup
  push to `github.com/e2kd7n/backups`) needs this to authenticate non-interactively.
- The GHCR image must include `cron/send_maintenance_summary.py` (moved there from `scripts/`
  since only `cron/` is `COPY`'d into the image — the ntfy summary step runs via
  `podman exec ride-optimizer python cron/send_maintenance_summary.py`, the same pattern as
  `daily_analysis.py` etc., because it needs the app's Python deps that bare host Python lacks).
- `git push` must already work unattended from the Pi's checkout (existing credential
  helper/SSH key) for both the main repo and the `backups` push.

Logs: `logs/cron_weekly_maintenance.log` (cron wrapper output) and a fresh
`logs/maintenance-<timestamp>.log` per run. `--auto-close` is deliberately never passed to
`update-issue-priorities.sh` here — regex-based issue closing has produced false positives
before, so "appears resolved" issues are only ever flagged for human review, never closed
automatically.

## Last Sync Date

**Last Documentation Sync:** 2026-07-20 11:52 UTC
**Next Scheduled Sync:** 2026-07-27
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: 1029)
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
**Next Scheduled Sync:** 2026-07-24
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: 402)
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
**Next Scheduled Sync:** 2026-07-22
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: 60694)
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
**Next Scheduled Sync:** 2026-07-11
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: 43426)
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
**Next Scheduled Sync:** 2026-06-29
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: 1395)
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
**Next Scheduled Sync:** 2026-06-08
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: 69523)
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
**Next Scheduled Sync:** 2026-05-25
**Performed By:** Automated Weekly Maintenance Script

**Changes in This Sync:**
- Backups created: ISSUE_PRIORITIES.md, docs/, plans/
- Issue priorities update running in background (PID: 82599)
- Git status verified
- Repository statistics updated
- **Time Invested:** ~5 minutes (automated)

**Previous Sync (2026-05-10 02:58 UTC):**
**Next Scheduled Sync:** 2026-05-17
**Performed By:** Bob (AI Assistant)

**Changes in This Sync:**
- **Version Rebaseline Complete:** Renamed all v2.x.0 release directories to v0.x.0 format
- Updated 6 directories: v2.0.0→v0.5.0, v2.1.0→v0.6.0, v2.2.0→v0.7.0, v2.3.0→v0.8.0, v2.4.0→v0.9.0, v2.5.0→v0.10.0
- Renamed 3 files with version numbers in filenames
- Updated 15+ markdown files with version references (HISTORICAL_RELEASES.md, README.md, TIME_TRACKING.md, etc.)
- Verified 0 old version references remaining (v2.x.0 or v1.0.0)
- All releases documentation now aligned with 0.x.x versioning scheme per VERSIONING_PLAN.md
- **Time Invested:** ~15 minutes (directory renames, bulk sed replacements, verification)

**Previous Sync (2026-05-07 23:39 UTC):**
- Updated ISSUE_PRIORITIES.md (50+ commits since last sync on 2026-03-30)
- Reviewed project architecture changes (Web Platform Migration Epic #144)
- Verified major features completed: Interactive Maps (#236), P0 issue resolution (#212-#216)
- Noted extensive QA testing and bug fixes (multiple QA sessions documented)
- Identified documentation gap: TECHNICAL_SPEC.md and IMPLEMENTATION_GUIDE.md need updates for web platform architecture
- Current status: 0 P0 issues, 31 P1 issues, 28 P2 issues, 23 P3 issues, 11 P4 issues
- Major architectural changes: Flask deprecation, static frontend with API backend, new app/ structure
- Recommended action: Create GitHub issue for comprehensive documentation update to reflect web platform

**Previous Sync (2026-03-30 03:40 UTC):**
- Updated ISSUE_PRIORITIES.md with v0.9.0 completion and design audit results
- Updated TIME_TRACKING.md with v0.9.0 detailed tracking (2.5 hours invested)
- Reviewed TECHNICAL_SPEC.md for accuracy (no changes needed)
- Created DESIGN_PRINCIPLES_ISSUE_AUDIT.md (comprehensive 43-issue review)
- Completed v0.9.0 Long Rides feature with bug fixes and polish
- Fixed 'uses' field display, template errors, and pagination issues
- Added sortable headers and 'uses' column to Long Rides table
- Implemented hardware-aware parallelism for route matching
- Reviewed and updated 13 GitHub issues with design requirements
- Closed 1 duplicate issue (#22)
- Updated 2 epics (#54, #57) to enforce design principles
- Consolidated v0.10.0/v0.11.0/v0.12.0 plans into unified roadmap

## Notes

- This is a living document - update the process as needed
- If major changes occur mid-week, don't wait for weekly sync
- Keep commits focused on documentation only
- Use consistent commit message format for tracking

---

*Created: 2026-03-13*