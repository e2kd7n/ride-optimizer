# Version Rebaseline Plan

**Created:** 2026-05-07  
**Purpose:** Align all documentation with actual GitHub release versions and establish v1.0.0 as first production release

---

## 🎯 Problem Statement

Documentation references outdated version scheme (v0.9.x, v3.0.0) that doesn't match actual GitHub releases (v2.1.0-v2.5.0). This creates confusion and makes the project appear disorganized.

**Found:** 84 version references across 30+ files that need updating

---

## 📊 Current State vs Target State

### Current State
- **GitHub Releases:** v2.1.0, v2.2.0, v2.3.0, v2.4.0, v2.5.0 (latest)
- **Documentation:** References v0.9.0, v0.9.1, v0.9.2, v0.9.3, v3.0.0
- **Confusion:** Docs don't match reality

### Target State (Option B - Approved)
- **Current Release:** v2.5.0 (last pre-production)
- **Next Major Release:** v1.0.0 (first production-ready with simplified architecture)
- **Rationale:** v1.0.0 signals "production ready" better than v2.6.0

---

## 🗺️ Version Mapping

| Old Reference | New Reference | Status | Notes |
|---------------|---------------|--------|-------|
| v0.9.0 | v2.5.0 | Current | Last pre-production release |
| v0.9.1 | ~~Deprecated~~ | Skip | Merged into v1.0.0 scope |
| v0.9.2 | ~~Deprecated~~ | Skip | Merged into v1.0.0 scope |
| v0.9.3 | ~~Deprecated~~ | Skip | Merged into v1.0.0 scope |
| v3.0.0 | v1.0.0 | Target | First production release with simplified architecture |

**Key Principle:** v1.0.0 represents the first production-ready release after architecture simplification (Issue #152)

---

## 📁 Files to Update

### Priority 1: User-Facing Documentation (5 files)

These are the most visible and important to fix first:

1. **RELEASE_ROADMAP.md** (20+ references)
   - Replace v0.9.0 → v2.5.0 (current)
   - Replace v0.9.1-v0.9.3 → "Deprecated - merged into v1.0.0"
   - Replace v3.0.0 → v1.0.0
   - Update timeline to reflect architecture simplification

2. **ISSUE_PRIORITIES.md**
   - Update Epic #144 from "v3.0.0" to "v1.0.0"
   - Update Epic #146 (closed, but document for reference)

3. **SQUAD_ORGANIZATION.md**
   - Replace v3.0.0 references with v1.0.0
   - Update timeline to reflect 5-week architecture simplification

4. **docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md**
   - Confirm v1.0.0 target is correct
   - Update timeline estimates

5. **docs/VERSIONING_PLAN.md**
   - Add section explaining v2.5.0 → v1.0.0 transition
   - Document why we're resetting to v1.0.0

### Priority 2: Internal Documentation (8 files)

These support development work:

6. **FRONTEND_CODE_REVIEW.md** - Update v3.0.0 → v1.0.0
7. **CROSS_SQUAD_COORDINATION_URGENT.md** - Update v3.0.0 MVP → v1.0.0 MVP
8. **QA_PROGRESS_REPORT.md** - Update v3.0.0 MVP → v1.0.0 MVP
9. **ISSUE_MANAGEMENT_SUMMARY.md** - Update v3.0.0 milestone → v1.0.0
10. **OUTSTANDING_ACTIONS.md** - Update v3.0.0 milestone → v1.0.0
11. **INTELLIGENT_ISSUE_MANAGEMENT_REPORT.md** - Update v3.0.0 epic → v1.0.0
12. **SQUAD_PROGRESS_MONITORING.md** - Update v3.0.0 MVP → v1.0.0 MVP
13. **app/README.md** - Update v3.0.0 references → v1.0.0

### Priority 3: Historical/Archive (Keep As-Is)

**DO NOT MODIFY** - These are historical records:

- `docs/releases/HISTORICAL_RELEASES.md` - Historical accuracy required
- `docs/releases/TIME_TRACKING.md` - Time tracking for past releases
- `docs/releases/v2.0.0/*` - Historical release notes
- `docs/archive/*` - Archived analysis and decisions
- `plans/v0.1.0/*` - Historical planning docs
- `plans/v2.2.0-v2.5.0/*` - Historical implementation plans

### Special Case: Dependency Versions

**DO NOT MODIFY** - These are library versions, not project versions:

- `stravalib>=0.10.0`
- `flask==3.0.0`
- `pandas>=1.5.0`
- `pytest-cov>=4.0.0`
- etc.

---

## 🔄 Update Strategy

### Phase 1: High-Priority Docs (Week 1)
1. Create this plan document ✅
2. Update RELEASE_ROADMAP.md
3. Update ISSUE_PRIORITIES.md
4. Update SQUAD_ORGANIZATION.md
5. Update docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md
6. Update docs/VERSIONING_PLAN.md

### Phase 2: Internal Docs (Week 1)
7. Update all 8 internal documentation files
8. Verify no broken cross-references

### Phase 3: Verification (Week 1)
9. Search for any remaining v0.9.x or v3.0.0 references
10. Verify historical docs remain unchanged
11. Update this plan with completion status

### Phase 4: GitHub Integration (Week 1)
12. Create GitHub issue for tracking
13. Update issue #152 (architecture simplification) to reference v1.0.0
14. Close this tracking issue when complete

---

## 🎯 Success Criteria

- [ ] All 13 priority files updated with correct versions
- [ ] No references to v0.9.x or v3.0.0 in active documentation
- [ ] Historical docs preserved unchanged
- [ ] GitHub issue created and tracked
- [ ] Architecture simplification (Issue #152) references v1.0.0
- [ ] All cross-references verified working

---

## 📝 Standard Replacement Patterns

Use these patterns for consistency:

### Pattern 1: Current Release
```markdown
# Before
v0.9.0 - Web Platform MVP (Current - Week 8)

# After
v2.5.0 - Current Release (Pre-Production)
**Note:** v1.0.0 will be the first production-ready release with simplified architecture
```

### Pattern 2: Deprecated Releases
```markdown
# Before
### v0.9.1 - Release +1 (Weeks 12-15)
### v0.9.2 - Release +2 (Weeks 16-21)
### v0.9.3 - Release +3 (Weeks 22-25)

# After
**Note:** Releases v0.9.1-v0.9.3 have been deprecated and merged into v1.0.0 scope as part of architecture simplification (Issue #152)
```

### Pattern 3: Next Major Release
```markdown
# Before
v3.0.0 - Web Platform MVP

# After
v1.0.0 - First Production Release
**Focus:** Simplified architecture optimized for single-user Raspberry Pi deployment
```

### Pattern 4: Epic/Milestone References
```markdown
# Before
Epic #144 - Personal Web Platform Migration (v3.0.0)

# After
Epic #144 - Personal Web Platform Migration (v1.0.0)
```

---

## 🚨 Important Notes

1. **Historical Accuracy:** Never modify historical release notes or time tracking
2. **Dependency Versions:** Never change library version requirements (e.g., `flask==3.0.0`)
3. **Cross-References:** Verify all internal links still work after updates
4. **Consistency:** Use exact patterns above for uniformity
5. **Architecture Link:** Always mention Issue #152 when explaining v1.0.0

---

## 📊 Progress Tracking

| Phase | Files | Status | Completed |
|-------|-------|--------|-----------|
| Phase 1 | 5 files | Pending | 0/5 |
| Phase 2 | 8 files | Pending | 0/8 |
| Phase 3 | Verification | Pending | 0/3 |
| Phase 4 | GitHub | Pending | 0/2 |
| **Total** | **13 files + 5 tasks** | **0%** | **0/18** |

---

## 🔗 Related Issues

- **#152** - Architecture Simplification (defines v1.0.0 scope)
- **#153** - Phase 1: Foundation Migration
- **#155** - Phase 2: Frontend Conversion
- **#156** - Phase 3: Integration Work
- **#157** - Phases 4-5: QA & Beta Prep
- **#146** - Beta Program (closed as bloat)

---

## 📅 Timeline

- **Week 1:** Complete all documentation updates
- **Week 2-6:** Execute architecture simplification (Issue #152)
- **Week 6:** Release v1.0.0 (first production-ready)

---

## ✅ Completion Checklist

- [ ] VERSION_REBASELINE_PLAN.md created
- [ ] All Priority 1 files updated (5 files)
- [ ] All Priority 2 files updated (8 files)
- [ ] Historical docs verified unchanged
- [ ] GitHub issue created for tracking
- [ ] Issue #152 updated to reference v1.0.0
- [ ] Final verification search shows no v0.9.x or v3.0.0 in active docs
- [ ] This plan marked complete and archived