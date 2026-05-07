# Release Roadmap

**Created:** 2026-05-06 16:23 CDT  
**Updated:** 2026-05-07 (Version Rebaseline)  
**Based on:** Architecture Simplification (Issue #152)

---

## 🎯 Current Status

**Current Release:** v2.5.0 (Pre-Production)  
**Next Release:** v1.0.0 (First Production-Ready Release)  
**Target:** Single-user Raspberry Pi deployment

---

## 📅 Release Schedule

### v2.5.0 - Current Release (Pre-Production)
**Status:** Released  
**Focus:** CLI-based ride analysis with web dashboard prototype  
**Architecture:** Flask + SQLAlchemy + APScheduler + Docker

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

### v1.0.0 - First Production Release (Target: 5 weeks)
**Status:** In Planning (Issue #152)  
**Focus:** Simplified architecture optimized for Raspberry Pi  
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

## 🚫 Deprecated Releases

The following planned releases have been **deprecated** and merged into v1.0.0 scope:

### ~~v0.9.0 - Web Platform MVP~~
**Status:** Deprecated  
**Reason:** Over-engineered for single-user Pi deployment  
**Merged Into:** v1.0.0 (simplified architecture)

### ~~v0.9.1 - UX Enhancements~~
**Status:** Deprecated  
**Reason:** Unnecessary complexity for personal tool  
**Merged Into:** v1.0.0 (core features only)

### ~~v0.9.2 - Mobile Optimization~~
**Status:** Deprecated  
**Reason:** Responsive design sufficient for single user  
**Merged Into:** v1.0.0 (mobile-first CSS)

### ~~v0.9.3 - External Integrations~~
**Status:** Deprecated  
**Reason:** Strava integration sufficient for personal use  
**Merged Into:** Future consideration (post-v1.0.0)

### ~~v3.0.0 - Web Platform~~
**Status:** Deprecated (version number confusion)  
**Replaced By:** v1.0.0 (correct semantic versioning)

---

## 🎯 Feature Preservation Matrix

All existing features will be preserved in v1.0.0:

| Feature | v2.5.0 | v1.0.0 | Implementation |
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
- **v2.5.0:** 250-300MB (Flask + SQLAlchemy + APScheduler)
- **v1.0.0:** 50MB (Static files + minimal API)
- **Reduction:** 80%

### Dependencies
- **v2.5.0:** 27 packages (Flask, SQLAlchemy, APScheduler, etc.)
- **v1.0.0:** 12 packages (core libraries only)
- **Reduction:** 55%

### Startup Time
- **v2.5.0:** 5-8 seconds (Flask app initialization)
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

- **v2.5.0** (2026-03-30): Last pre-production release with complex architecture
- **v2.4.0** (2026-03-30): Long rides feature & polish
- **v2.3.0** (2026-03-30): Segment-based route naming
- **v2.2.0** (2026-03-30): Test infrastructure
- **v2.1.0** (2026-03-26): Code quality & design system
- **v1.0.0** (Target: 2026-06): First production-ready release with simplified architecture

---

*Last updated: 2026-05-07 (Version Rebaseline)*  
*See [VERSION_REBASELINE_PLAN.md](VERSION_REBASELINE_PLAN.md) for details on version scheme changes*