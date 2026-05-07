# Issue #152 Architecture Simplification - Coordination Plan

**Epic:** Architecture Simplification for Raspberry Pi (v0.11.0)  
**Status:** 🚀 ACTIVE - Phase 1 Starting  
**Timeline:** 5 weeks (2026-05-07 to 2026-06-14)  
**Coordinator:** Bob (Engineering Lead)

---

## Executive Summary

Migrating from Flask/SQLAlchemy/APScheduler to "Smart Static" architecture:
- **Goal:** 80% memory reduction (250MB → 50MB)
- **Approach:** Static HTML + Minimal API + Cron jobs
- **Timeline:** 5 weeks across 4 phases
- **Quality Target:** 70% test coverage, 100% feature preservation

---

## Squad Assignments

### Foundation Squad (Phase 1 Lead)
**Focus:** Service extraction, API creation, data migration  
**Members:** Primary development team  
**Timeline:** Week 1 (5 days)

### Frontend Squad (Phase 2 Lead)
**Focus:** Template conversion, JavaScript integration  
**Members:** UI/UX team  
**Timeline:** Week 2 (5 days)

### Integration Squad (Phase 3 Lead)
**Focus:** Cron conversion, background jobs, monitoring  
**Members:** DevOps/Integration team  
**Timeline:** Week 3 (5 days)

### QA Squad (Phase 4-5 Lead)
**Focus:** Testing, documentation, beta prep  
**Members:** Quality assurance team  
**Timeline:** Weeks 4-5 (10 days)

---

## Phase 1: Foundation Migration (Week 1)

### Objectives
1. Extract service layer from Flask dependencies
2. Create minimal API (50-100 lines, 4 endpoints)
3. Convert SQLite → JSON file storage
4. Migration script with rollback capability
5. Unit tests for new architecture

### Deliverables
- ✅ `api.py` - Minimal Flask API
- ✅ `scripts/migrate_to_json.py` - Migration script
- ✅ Updated service files (framework-agnostic)
- ✅ JSON data files in `data/` directory
- ✅ Test suite for new architecture

### Success Criteria
- All services work without Flask dependencies
- API endpoints return correct JSON
- Data migration successful with no data loss
- All tests passing
- Memory usage <50MB
- API response time <100ms

### Task Breakdown

#### Task 1.1: Extract Service Layer (2 days)
**Files to modify:**
- `app/services/analysis_service.py`
- `app/services/commute_service.py`
- `app/services/planner_service.py`
- `app/services/weather_service.py`
- `app/services/trainerroad_service.py`
- `app/services/route_library_service.py`

**Actions:**
- Remove Flask imports (jsonify, request, etc.)
- Return plain Python dicts/objects instead of Flask responses
- Remove any Flask context dependencies
- Add type hints for clarity
- Unit test each service independently

#### Task 1.2: Create Minimal API (1 day)
**New file:** `api.py`

**Endpoints:**
1. `GET /api/weather` - Current weather data
2. `GET /api/recommendation` - Next commute recommendation
3. `GET /api/routes` - All routes for library
4. `GET /api/status` - System health and freshness

**Features:**
- Static file serving for HTML pages
- Basic error handling
- JSON responses only
- No sessions, CORS, rate limiting (single user)

#### Task 1.3: Convert Data Storage (2 days)
**JSON file structure:**
```
data/
├── weather.json          # Current weather snapshot
├── recommendations.json  # Commute recommendations
├── routes.json          # Route library data
├── status.json          # System health/freshness
├── favorites.json       # User favorites
└── workouts.json        # TrainerRoad workouts
```

**Actions:**
- Define JSON schemas
- Create read/write utilities
- Implement atomic writes (temp file + rename)
- Add file locking for concurrent access
- Set proper permissions (0600)

#### Task 1.4: Migration Script (included in 1.3)
**Script:** `scripts/migrate_to_json.py`

**Features:**
- Export all SQLite data to JSON
- Validate data integrity
- Rollback capability
- Progress reporting
- Dry-run mode

#### Task 1.5: Testing (1 day)
**Test coverage:**
- Unit tests for API endpoints
- Integration tests for service layer
- Performance tests (response times)
- Memory usage verification
- Data migration validation

---

## Phase 2: Frontend Conversion (Week 2)

### Objectives
1. Convert Jinja2 templates to static HTML
2. Add JavaScript for API calls
3. Implement client-side filtering/sorting
4. Verify responsive design
5. Test all interactive features

### Deliverables
- Static HTML files in `static/` directory
- JavaScript modules for API interaction
- All features verified working
- Responsive design intact

---

## Phase 3: Integration Work (Week 3)

### Objectives
1. Convert APScheduler jobs to cron scripts
2. Test background automation
3. Setup monitoring and logging
4. Integration testing
5. Performance verification on Pi

### Deliverables
- Cron scripts in `scripts/cron/`
- Crontab configuration
- Monitoring in place
- Integration tests passing

---

## Phase 4-5: QA & Beta Prep (Weeks 4-5)

### Objectives
1. Comprehensive testing (70% coverage)
2. Update all documentation
3. Beta infrastructure setup
4. Final verification
5. Launch preparation

### Deliverables
- All tests passing (70% coverage)
- Complete documentation
- Beta infrastructure ready
- Performance verified on Pi

---

## Parallel Work Strategy

### Week 1 (Phase 1)
- **Foundation Squad:** Full focus on migration
- **Frontend Squad:** Plan template conversion, review current templates
- **Integration Squad:** Plan cron conversion, review APScheduler jobs
- **QA Squad:** Plan test strategy, prepare test infrastructure

### Week 2 (Phase 2)
- **Foundation Squad:** Support frontend, bug fixes
- **Frontend Squad:** Full focus on conversion
- **Integration Squad:** Continue planning, start cron scripts
- **QA Squad:** Begin API testing

### Week 3 (Phase 3)
- **Foundation Squad:** Support integration
- **Frontend Squad:** Support integration, polish UI
- **Integration Squad:** Full focus on cron + monitoring
- **QA Squad:** Integration testing

### Weeks 4-5 (Phase 4-5)
- **All Squads:** Testing, documentation, beta prep

---

## Risk Management

### Risk 1: Service Extraction Complexity
**Likelihood:** MEDIUM  
**Impact:** MEDIUM  
**Mitigation:** Services already well-structured, incremental extraction

### Risk 2: Data Migration Issues
**Likelihood:** LOW  
**Impact:** HIGH  
**Mitigation:** Thorough testing, rollback capability, backup strategy

### Risk 3: Timeline Slippage
**Likelihood:** LOW  
**Impact:** MEDIUM  
**Mitigation:** Conservative estimates, parallel work, daily standups

### Risk 4: Feature Loss During Conversion
**Likelihood:** LOW  
**Impact:** HIGH  
**Mitigation:** Feature preservation matrix, comprehensive testing

---

## Communication Plan

### Daily Standups (15 min)
- What did you complete yesterday?
- What are you working on today?
- Any blockers?

### Weekly Reviews (30 min)
- Phase completion review
- Next phase kickoff
- Risk assessment
- Timeline adjustment if needed

### Ad-hoc Coordination
- Slack/Discord for quick questions
- Pair programming for complex tasks
- Code reviews for all changes

---

## Success Metrics

### Technical Metrics
- ✅ Memory usage <50MB (vs 250MB)
- ✅ 70% test coverage (vs 27% current)
- ✅ API response time <100ms
- ✅ 100% feature preservation
- ✅ Zero data loss during migration

### Quality Metrics
- ✅ Zero P0 bugs
- ✅ <3 P1 bugs
- ✅ Complete documentation
- ✅ Excellent Pi performance

### Timeline Metrics
- ✅ Phase 1 complete by Week 1 end
- ✅ Phase 2 complete by Week 2 end
- ✅ Phase 3 complete by Week 3 end
- ✅ Beta ready by Week 5 end

---

## Next Steps

1. **Immediate:** Begin Phase 1, Task 1.1 (Service extraction)
2. **Today:** Create feature branch `feature/smart-static-migration`
3. **This Week:** Complete Phase 1 deliverables
4. **Next Week:** Transition to Phase 2

---

**Last Updated:** 2026-05-07 03:04 UTC  
**Coordinator:** Bob (Engineering Lead)  
**Status:** 🚀 ACTIVE - Phase 1 Starting