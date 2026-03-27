# Issue Prioritization

**Last Updated:** 2026-03-27 01:16 UTC

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

### Active P0 Issues

**None** - All critical issues resolved! ✅

### Recently Resolved P0 Issues

- **✅ Test Suite Failures (16/43 tests failing)** - RESOLVED 2026-03-27
  - All 43 tests now passing (100% pass rate)
  - Fixed type mismatches, mock configurations, and edge cases
  - Test suite ready for CI/CD integration

## 🔴 P1 - HIGH (Current Sprint)
Issues that significantly impact core functionality or user experience.

- **EPIC: Segment-Based Route Naming** - Show connection streets + main route (see ROUTE_NAMING_EPIC.md)
  - Sub-issue 1: Increase route sampling density
  - Sub-issue 2: Implement route segment identification
  - Sub-issue 3: Implement segment-based name generation
  - Sub-issue 4: Update route analysis integration
  - Sub-issue 5: Add configuration options
  - Sub-issue 6: Clear cache and validate with real data
- #58 - Show time-aware next commute recommendations (to work & to home)

## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.

- #21 - Update TECHNICAL_SPEC.md with comprehensive implementation details



## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.

- #41 - Create unit tests for core modules (in progress - tests created, need more coverage)
- #42 - Write integration tests for full workflow (in progress - tests created, need more coverage)
- #61 - Code Quality: Improve exception handling (remove bare except)
- #22 - Debug and fix Bootstrap tab switching functionality

## 📋 P4 - FUTURE ENHANCEMENTS
Feature requests and enhancements for future releases.

- #62 - 🎨 EPIC: Mobile-First UI/UX Redesign & Accessibility
  - #63 - Mobile-First Responsive Layout (in progress)
  - #64 - Progressive Disclosure for Metrics
  - #65 - Touch-Optimized Interactions (in progress)
  - #66 - Feature Discovery & Onboarding
  - #67 - Mobile Navigation Patterns
  - #68 - Visual Hierarchy & Polish
  - #69 - Map Direction Indicators
- #57 - 🎯 EPIC: Long Rides Analysis & Recommendations (consolidates #6, #7, #8, #9)
  - #6 - Add top 10 longest rides table with Strava links
  - #7 - Add monthly ride statistics breakdown
  - #8 - Add average speed and elevation gain metrics
  - #9 - Add interactive map showing all long ride routes
- #54 - Weather Dashboard Implementation (Epic)
- #33 - Add traffic pattern analysis

## ⚠️ Unprioritized Issues
Issues without priority labels that need to be triaged.

- #49 - Implement Metric/Imperial Unit Toggle with Complete Consistency
- #48 - Implement Data Export in JSON, GPX, and CSV Formats
- #47 - Add Side-by-Side Route Comparison Feature
- #46 - Add PDF Export Option
- #45 - Add QR Code Generation for Mobile Transfer
- #44 - Extract HTML template to external file
- #39 - Evaluate Photon API as Nominatim alternative
- #38 - Add social features (compare with other commuters)
- #37 - Add real-time route suggestions
- #36 - Create mobile app version
- #35 - Add integration with other fitness platforms
- #34 - Add carbon footprint calculations
- #25 - Implement automatic token refresh for expired Strava tokens


## Priority Guidelines

### P0 - CRITICAL
- Application is down or unusable
- Data loss or corruption
- Security vulnerabilities
- **Action:** Drop everything and fix immediately

### P1 - HIGH
- Core features broken or severely degraded
- Significant user pain points
- Blocks important workflows
- **Action:** Fix in current sprint (1-2 weeks)

### P2 - MEDIUM
- Feature improvements
- Moderate user pain points
- Quality of life enhancements
- **Action:** Plan for next sprint (2-4 weeks)

### P3 - LOW
- Minor UX improvements
- Edge cases
- Nice-to-have features
- **Action:** Backlog, address when time permits

### P4 - FUTURE
- New features
- Major enhancements
- Long-term improvements
- **Action:** Plan for future releases

## How to Update Priorities

1. Use GitHub labels to set priority (P0-critical, P1-high, P2-medium, P3-low, P4-future)
2. Update this file manually or via script
3. Commit changes with descriptive message
4. Communicate priority changes to team

## Summary Statistics

- **Total Open Issues:** 29
- **P0 (Critical):** 1 ⚠️ (Test suite failures)
- **P1 (High):** 6 (includes 1 epic with 6 sub-issues)
- **P2 (Medium):** 5 (includes 2 epics with 12 sub-issues)
- **P3 (Low):** 4
- **P4 (Future):** 6
- **Unprioritized:** 15

## Completed Issues (v2.2.0 - 2026-03-27)

### v2.1.0 Completed (2026-03-26)
1. **✅ #55** - Closed as superseded by #56 (Fréchet algorithm already working)
2. **✅ #53** - Code Cleanup and Performance Optimization
3. **✅ #52** - Remove Test Routes from Production Code
4. **✅ #51** - Significantly Improve Route Naming Mechanism
5. **✅ #50** - Show Optimal Route Map Preview at Top of Page
6. **✅ #43** - Add caching for Fréchet distance calculations

### v2.2.0 In Progress (2026-03-27)
1. **✅ Test Infrastructure** - Created pytest configuration, test runner, and documentation
2. **✅ Cache Separation Implementation** - Separated test and production cache files
   - Added `use_test_cache` parameter to StravaDataFetcher
   - Created `data/cache/activities_test.json` for test data
   - Protected production cache (`data/cache/activities.json`) from test overwrites
   - Created `tests/setup_test_data.py` for synthetic test data generation
   - Documented in `tests/TEST_DATA_README.md` and `CACHE_SEPARATION_IMPLEMENTATION.md`
   - Prevents data loss incidents (recovered from March 26 incident where 2,408 activities were overwritten)
3. **✅ Test Suite Remediation** - Fixed all 16 failing tests (100% pass rate achieved)
   - Fixed Activity dataclass 'commute' parameter issues (6 tests)
   - Fixed datetime vs string type mismatches (3 tests)
   - Fixed tuple vs Location object mismatches (5 tests)
   - Fixed mock configuration issues (2 tests)
   - Fixed edge case handling and assertions (2 tests)
   - Implemented all fixes from TEST_REMEDIATION_PLAN.md (Phases 1-3)
   - Test suite now fully operational: **43/43 tests passing** ✅
4. **🔄 #41** - Unit tests for core modules (in progress - 4 test files created, need more coverage)
5. **🔄 #42** - Integration tests for full workflow (in progress - end-to-end tests created)
6. **🔄 #63** - Mobile-first responsive layout (in progress - part of #62 epic)
7. **🔄 #65** - Touch-optimized interactions (in progress - part of #62 epic)

## Recommended Next Actions

1. **🏷️ Route Naming Epic** - Implement segment-based route naming with connection streets (P1-high)
2. **#58** - Time-aware next commute recommendations (P1-high)
3. **#21** - Update TECHNICAL_SPEC.md with comprehensive implementation details (P2-medium)
4. **CI/CD Integration** - Set up GitHub Actions with the now-working test suite
5. **Increase test coverage** - Expand #41 and #42 to cover more modules
6. **Triage unprioritized issues** - Assign priority labels to remaining 15 issues
7. **Prepare v2.2.0 release** - All P1/P2 issues resolved, ready for release