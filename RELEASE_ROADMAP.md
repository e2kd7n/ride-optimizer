# Release Roadmap

**Created:** 2026-05-06 16:23 CDT
**Updated:** 2026-05-14 (Release-Aware Priority System)
**Based on:** Architecture Simplification (Issue #152)

> **⚠️ IMPORTANT:** This file now inherits release numbers from GitHub milestones.
> The "Next Release" and "Future Releases" are automatically determined from open GitHub milestones.
> To update: Create/modify GitHub milestones, then run `./scripts/update-issue-priorities.sh`

---

## 🎯 Current Status

**Current Release:** v0.11.0 (deployed)
**Next Release:** v0.12.0 (in development)
**Future Releases:** v0.13.0, v0.14.0
**Target:** Single-user Raspberry Pi deployment

**Source of Truth:** GitHub Milestones (automatically detected)

---

## 📅 Release History

### v0.5.0 - Original Prototype
**Status:** Original
**Architecture:** CLI + Static HTML
**Notes:** Simple, lightweight, worked well

### v0.6.0 - v0.10.0 - Flask Experiment
**Status:** Released (formerly v2.1.0-v2.5.0)
**Architecture:** Flask + SQLAlchemy + APScheduler + Docker

**Releases:**
- v0.6.0 (formerly v2.1.0) - Code quality & design system
- v0.7.0 (formerly v2.2.0) - Test infrastructure
- v0.8.0 (formerly v2.3.0) - Segment-based route naming
- v0.9.0 (formerly v2.4.0) - Long rides feature & polish
- v0.10.0 (formerly v2.5.0) - Current release

**Key Features:**
- Strava integration for activity fetching
- Route analysis and grouping
- Weather integration
- Long ride recommendations
- Web dashboard (prototype)

**Known Issues:**
- Over-engineered for single-user deployment
- High memory usage (250-300MB)
- Complex dependency stack (27 packages)
- Unnecessary multi-user infrastructure

---

## 📅 Planned Releases

> **Note:** Release planning is now managed via GitHub milestones. Issues are assigned to milestones and prioritized within each release.

### v0.12.0 - Next Release (In Development)
**Status:** Active Development
**GitHub Milestone:** [v0.12.0](https://github.com/user/repo/milestone/X)
**Focus:** Backend infrastructure and code quality improvements

**Key Issues:**
- 2 P1-high issues (API endpoints)
- 15 P2-medium issues (architecture, testing, code quality)

### v0.13.0 - Future Release
**Status:** Planning
**GitHub Milestone:** [v0.13.0](https://github.com/user/repo/milestone/Y)
**Focus:** UI/UX improvements and user experience

**Key Issues:**
- 9 P1-high issues (error handling, FTUE, mobile navigation)
- Multiple P2-medium issues (design, weather features)

### v0.14.0 - Future Release
**Status:** Planning
**GitHub Milestone:** [v0.14.0](https://github.com/user/repo/milestone/Z)
**Focus:** Testing, performance, and production readiness

**Key Issues:**
- 13 P1-high issues (test coverage, performance, API features)
- Multiple P2-medium issues (testing infrastructure)

### v0.11.0 - Architecture Simplification (COMPLETED)
**Status:** Deployed
**Focus:** Return to simplified architecture like v0.5.0
**Architecture:** Static HTML + Minimal API + JSON files + Cron

**Goals:**
1. **Reduce Resource Usage**
   - Memory: 250MB → 50MB (80% reduction)
   - Dependencies: 27 → 12 packages (55% reduction)
   - Startup time: 5-8s → <1s

2. **Simplify Architecture**
   - Remove: Flask, SQLAlchemy, APScheduler, Docker
   - Add: Static HTML generation, minimal API endpoints
   - Keep: All existing features (100% preservation)

3. **Optimize for Single User**
   - Remove multi-user infrastructure
   - Remove unnecessary abstractions
   - Focus on pragmatic, minimal solutions

**Critical Missing Feature:**
- **#235 - Restore Interactive Maps** (EPIC, 28 days)
  - Web app has NO maps despite 1316 lines of Folium code
  - Restores all interactive map functionality from v0.5.0 CLI
  - Includes route comparison, weather overlays, heatmaps, filtering
  - See [INTERACTIVE_MAPS_RESTORATION_EPIC.md](plans/v0.11.0/INTERACTIVE_MAPS_RESTORATION_EPIC.md)

**Migration Phases:**
- **Phase 1 (Week 1):** Foundation - Data layer & static generation
- **Phase 2 (Week 2):** Frontend - Convert templates to static HTML
- **Phase 3 (Week 3):** Integration - API endpoints & cron jobs
- **Phase 4 (Week 4):** QA - Testing & validation
- **Phase 5 (Week 5):** Beta - User testing & release prep

**Related Issues:**
- #152 - Architecture Simplification (Epic)
- #153 - Phase 1: Foundation Migration
- #155 - Phase 2: Frontend Conversion
- #156 - Phase 3: Integration Work
- #157 - Phases 4-5: QA & Beta Prep

---

### v0.12.0 - v0.99.0 - Future Development
**Status:** Headroom for future releases
**Purpose:** Incremental improvements, bug fixes, new features

Plenty of version numbers available for development before declaring production-ready.

---

### v1.0.0 - Production Ready (Future)
**Status:** Reserved for true production readiness
**Requirements:**
- Architecture proven stable on Raspberry Pi
- Used successfully in daily production for 3+ months
- All core features complete and tested
- Documentation comprehensive
- No major known issues
- Confident in long-term API stability

**Not Ready Yet Because:**
- Still refining architecture (v0.11.0)
- Not yet battle-tested in daily use
- API and features may still change
- Being honest about maturity level

---

## 🎯 Feature Preservation Matrix

All existing features will be preserved in v1.0.0:

| Feature | v0.10.0 | v1.0.0 | Implementation |
|---------|--------|--------|----------------|
| Strava Integration | ✅ | ✅ | Keep existing |
| Route Analysis | ✅ | ✅ | Keep existing |
| Weather Integration | ✅ | ✅ | Keep existing |
| Long Ride Planner | ✅ | ✅ | Keep existing |
| Dashboard | ✅ | ✅ | Static HTML |
| Commute View | ✅ | ✅ | Static HTML |
| Route Library | ✅ | ✅ | Static HTML |
| Background Jobs | ✅ | ✅ | Cron jobs |
| Data Caching | ✅ | ✅ | JSON files |

**Removed Features:**
- Multi-user support (unnecessary)
- Complex ORM (SQLAlchemy → JSON)
- Job scheduler (APScheduler → cron)
- Docker containerization (direct Python)
- Beta testing infrastructure (Issue #146 - closed as bloat)

---

## 📊 Resource Impact

### Memory Usage
- **v0.10.0:** 250-300MB (Flask + SQLAlchemy + APScheduler)
- **v1.0.0:** 50MB (Static files + minimal API)
- **Reduction:** 80%

### Dependencies
- **v0.10.0:** 27 packages (Flask, SQLAlchemy, APScheduler, etc.)
- **v1.0.0:** 12 packages (core libraries only)
- **Reduction:** 55%

### Startup Time
- **v0.10.0:** 5-8 seconds (Flask app initialization)
- **v1.0.0:** <1 second (static files served immediately)
- **Improvement:** 8x faster

---

## 🚀 Post-v1.0.0 Considerations

After v1.0.0 is stable, consider these enhancements **only if needed**:

### Low Priority (Evaluate After 3+ Months)
- **Alternative Geocoding:** Photon API vs Nominatim (if performance issues)
- **Additional Platforms:** Garmin, Wahoo (if Strava insufficient)
- **Mobile App:** Native app (if web interface insufficient)

### Not Planned (Bloat for Single User)
- ~~Social features~~ (unnecessary for personal tool)
- ~~Beta testing infrastructure~~ (you are the tester)
- ~~Multi-user support~~ (single-user deployment)
- ~~Admin dashboards~~ (you are the admin)
- ~~Feedback forms~~ (you provide your own feedback)

---

## 🔗 Related Documents

- **Architecture Simplification:** [ARCHITECTURE_SIMPLIFICATION_PROPOSAL.md](ARCHITECTURE_SIMPLIFICATION_PROPOSAL.md)
- **Implementation Summary:** [ARCHITECTURE_SIMPLIFICATION_SUMMARY.md](ARCHITECTURE_SIMPLIFICATION_SUMMARY.md)
- **Version Rebaseline:** [VERSION_REBASELINE_PLAN.md](VERSION_REBASELINE_PLAN.md)
- **Squad Organization:** [SQUAD_ORGANIZATION.md](SQUAD_ORGANIZATION.md)
- **Issue Priorities:** [ISSUE_PRIORITIES.md](ISSUE_PRIORITIES.md)

---

## 📝 Version History

- **v0.10.0** (2026-03-30): Last pre-production release with complex architecture (formerly v2.5.0)
- **v0.9.0** (2026-03-30): Long rides feature & polish (formerly v2.4.0)
- **v0.8.0** (2026-03-30): Segment-based route naming (formerly v2.3.0)
- **v0.7.0** (2026-03-30): Test infrastructure (formerly v2.2.0)
- **v0.6.0** (2026-03-26): Code quality & design system (formerly v2.1.0)
- **v1.0.0** (Target: 2026-06): First production-ready release with simplified architecture

---

*Last updated: 2026-05-07 (Version Rebaseline)*  
*See [VERSION_REBASELINE_PLAN.md](VERSION_REBASELINE_PLAN.md) for details on version scheme changes*