# Test Coverage Roadmap to 70%

## Current Status
- **Current Coverage**: 47.3% (3,202/6,765 lines)
- **Target Coverage**: 70% (4,736 lines)
- **Gap**: 1,534 lines needed

## Recently Completed (Squad 2)
- ✅ `weather_service.py`: 16% → 99% (+83%)
- ✅ `trainerroad_service.py`: 18% → 76% (+58%)
- ✅ `next_commute_recommender.py`: 36% → 95% (+59%)

## Prioritized Modules for 70% Target

### Phase 1: Core Business Logic (Target: +10% coverage)
**Priority**: P1-high  
**Estimated Impact**: 674 lines → +10% coverage  
**Timeline**: 2-3 weeks

1. **route_analyzer.py** (763 lines, 20% → 50%)
   - Impact: +230 lines (+3.4%)
   - Complexity: High
   - Business Value: Critical

2. **long_ride_analyzer.py** (409 lines, 13% → 50%)
   - Impact: +151 lines (+2.2%)
   - Complexity: High
   - Business Value: High

3. **data_fetcher.py** (271 lines, 49% → 80%)
   - Impact: +84 lines (+1.2%)
   - Complexity: Medium
   - Business Value: Critical

4. **report_generator.py** (233 lines, 47% → 80%)
   - Impact: +77 lines (+1.1%)
   - Complexity: Medium
   - Business Value: Medium

5. **route_namer.py** (377 lines, 15% → 50%)
   - Impact: +132 lines (+2.0%)
   - Complexity: Medium
   - Business Value: Medium

### Phase 2: Security & Infrastructure (Target: +5% coverage)
**Priority**: P1-high  
**Estimated Impact**: 284 lines → +4.2% coverage  
**Timeline**: 1-2 weeks

6. **auth_secure.py** (280 lines, 0% → 50%)
   - Impact: +140 lines (+2.1%)
   - Complexity: High
   - Business Value: Critical (Security)

7. **scheduler/jobs.py** (132 lines, 14% → 70%)
   - Impact: +74 lines (+1.1%)
   - Complexity: Medium
   - Business Value: High

8. **models/workouts.py** (140 lines, 20% → 70%)
   - Impact: +70 lines (+1.0%)
   - Complexity: Low
   - Business Value: Medium

### Phase 3: Supporting Modules (Target: +8% coverage)
**Priority**: P2-medium  
**Estimated Impact**: 576 lines → +8.5% coverage  
**Timeline**: 2-3 weeks

9. **visualizer.py** (218 lines, 0% → 60%)
   - Impact: +131 lines (+1.9%)
   - Complexity: Medium
   - Business Value: Low

10. **traffic_analyzer.py** (162 lines, 0% → 60%)
    - Impact: +97 lines (+1.4%)
    - Complexity: Medium
    - Business Value: Low

11. **carbon_calculator.py** (147 lines, 0% → 60%)
    - Impact: +88 lines (+1.3%)
    - Complexity: Low
    - Business Value: Low

12. **secure_cache.py** (107 lines, 0% → 70%)
    - Impact: +75 lines (+1.1%)
    - Complexity: Medium
    - Business Value: High (Security)

13. **scheduler/health.py** (135 lines, 27% → 70%)
    - Impact: +58 lines (+0.9%)
    - Complexity: Low
    - Business Value: Medium

14. **routes/settings.py** (107 lines, 32% → 70%)
    - Impact: +41 lines (+0.6%)
    - Complexity: Low
    - Business Value: Medium

15. **api/long_rides_api.py** (96 lines, 0% → 70%)
    - Impact: +67 lines (+1.0%)
    - Complexity: Medium
    - Business Value: Medium

## Execution Strategy

### Squad Organization
- **Squad 2A**: Focus on Phase 1 (Core Business Logic)
- **Squad 2B**: Focus on Phase 2 (Security & Infrastructure)
- **Squad 2C**: Focus on Phase 3 (Supporting Modules)

### Testing Approach
1. **Read existing tests** for patterns and conventions
2. **Analyze module** to understand functionality
3. **Identify critical paths** and edge cases
4. **Write unit tests** for individual functions
5. **Write integration tests** for module interactions
6. **Verify coverage** after each module
7. **Ensure all tests pass** before moving to next module

### Success Criteria
- Overall coverage ≥ 70%
- All new tests pass
- No existing tests broken
- Tests follow established patterns
- Comprehensive edge case coverage

## GitHub Issues

See individual issues for detailed implementation plans:
- Issue #XXX: Test Coverage - route_analyzer.py
- Issue #XXX: Test Coverage - long_ride_analyzer.py
- Issue #XXX: Test Coverage - data_fetcher.py
- Issue #XXX: Test Coverage - report_generator.py
- Issue #XXX: Test Coverage - route_namer.py
- Issue #XXX: Test Coverage - auth_secure.py
- Issue #XXX: Test Coverage - scheduler/jobs.py
- Issue #XXX: Test Coverage - models/workouts.py

## Progress Tracking

| Phase | Modules | Target Coverage | Status |
|-------|---------|----------------|--------|
| Completed | 3 modules | 42% → 47% | ✅ Done |
| Phase 1 | 5 modules | 47% → 57% | 📋 Planned |
| Phase 2 | 3 modules | 57% → 61% | 📋 Planned |
| Phase 3 | 7 modules | 61% → 70% | 📋 Planned |

## Notes
- Phases can be executed in parallel by different squad members
- Phase 1 is highest priority due to business criticality
- Security modules (auth_secure.py, secure_cache.py) should be prioritized within their phases
- Each module should have its own PR for easier review