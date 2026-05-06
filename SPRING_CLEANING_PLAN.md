# Spring Cleaning Plan - May 2026

**Date:** 2026-05-06  
**Purpose:** Organize repository according to documentation reorganization principles and remove obsolete files

---

## 📋 Cleanup Actions

### 1. Files to Delete
- [x] `=0.7.1` - Pip output file (accidental commit)
- [x] `.DS_Store` - macOS system file (already in .gitignore)

### 2. Files to Move to `docs/archive/`
- [x] `WEB_PLATFORM_PROPOSAL.md` - Future proposal, not current implementation
- [x] `DOCUMENTATION_REORGANIZATION.md` - Completed reorganization summary (historical record)

### 3. Files to Move to `docs/releases/maintenance/`
- [x] `WEEKLY_MAINTENANCE.md` - Consolidate with existing maintenance docs

### 4. Scripts to Archive (Obsolete/One-Time Use)
Move to `archive/debug_scripts/`:
- [x] `scripts/create_issues.sh` - One-time issue creation
- [x] `scripts/create_p2_issues.sh` - One-time issue creation
- [x] `scripts/create_uiux_epic_issues_temp.sh` - Temporary script
- [x] `scripts/create_v2.5.0_issue_updates.sh` - One-time update
- [x] `scripts/cleanup-issue-titles.sh` - One-time cleanup
- [x] `scripts/close-duplicate-issues.sh` - One-time cleanup
- [x] `scripts/rewrite_git_history.sh` - Dangerous, should be archived

### 5. .gitignore Updates
Already properly configured:
- `.DS_Store` ✓
- `.mailmap` ✓
- `bob_skills.md` ✓
- `rewrite_git_history.sh` ✓

---

## 🎯 Benefits

### Improved Organization
- Root directory cleaner with only active project files
- Historical/completed docs properly archived
- One-time scripts separated from active utilities

### Better Maintainability
- Clear distinction between active and archived content
- Easier to find current documentation
- Reduced clutter in root directory

### Consistency
- Follows documentation reorganization principles
- Matches mealplanner project structure
- Clear archival policy

---

## 📁 Final Root Directory Structure

After cleanup, root should contain only:
```
.clineignore
.coverage
.dockerignore
.env.example
.gitignore
bob_skills.md (gitignored)
coverage.json
docker-compose.yml
Dockerfile
ISSUE_PRIORITIES.md
ISSUES_TRACKING.md
LICENSE
main.py
pyrightconfig.json
pytest.ini
README.md
requirements.txt
ride-optimizer.code-workspace
archive/
cache/
config/
data/
docs/
htmlcov/
logs/
plans/
scripts/
src/
templates/
tests/
venv/
```

---

## 🔄 Execution Steps

1. Delete accidental/system files
2. Move documentation to appropriate locations
3. Archive obsolete scripts
4. Update any broken references
5. Commit with clear message
6. Verify all links still work

---

## 📝 Additional Recommendations

### Future Maintenance
1. **Weekly:** Run `scripts/update-issue-priorities.sh` to keep issues current
2. **Monthly:** Review `docs/releases/maintenance/MAINTENANCE_CHECKLIST.md`
3. **Quarterly:** Audit scripts/ directory for obsolete files
4. **Before releases:** Update version-specific docs in `docs/releases/vX.Y.Z/`

### Script Organization
Consider creating subdirectories in `scripts/`:
- `scripts/maintenance/` - Weekly/monthly maintenance scripts
- `scripts/testing/` - Test scripts
- `scripts/debug/` - Active debugging utilities
- `scripts/github/` - GitHub issue management

### Documentation Standards
- Keep root-level docs to minimum (README, LICENSE, ISSUES_TRACKING, ISSUE_PRIORITIES)
- All other docs go in `docs/` with appropriate subdirectory
- Archive completed/superseded docs to `docs/archive/`
- Version-specific docs go in `docs/releases/vX.Y.Z/`

---

**Status:** ✅ Completed  
**Executed By:** Bob (AI Assistant)  
**Date:** 2026-05-06