# Issue Prioritization

**Last Updated:** 2026-03-27 00:00 UTC

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

### Active P0 Issues

- **P0-CRITICAL: Fix Test Suite Failures (16/43 tests failing)**
  - **Impact:** 37.2% test failure rate blocks CI/CD and release confidence
  - **Root Cause:** Type mismatches in test code (not implementation bugs)
  - **Estimated Fix Time:** 70 minutes
  - **Details:** See TEST_REMEDIATION_PLAN.md
  - **Categories:**
    - 6 failures: Activity dataclass 'commute' parameter
    - 3 failures: datetime vs string type mismatch
    - 5 failures: tuple vs Location object mismatch
    - 2 failures: Mock configuration issues
  - **Action Required:** Implement fixes from TEST_REMEDIATION_PLAN.md phases 1-3

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
- #21 - Update TECHNICAL_SPEC.md with comprehensive implementation details
- #24 - [LOW PRIORITY] Grey out unselected routes on map when route is clicked
- #54 - Weather Dashboard Implementation (Epic)
- #33 - Add traffic pattern analysis

## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.







## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.


- #22 - [LOW PRIORITY] Debug and fix Bootstrap tab switching functionality

## 📋 P4 - FUTURE ENHANCEMENTS
Feature requests and enhancements for future releases.

- #57 - 🎯 EPIC: Long Rides Analysis & Recommendations (consolidates #6, #7, #8, #9)
- #6 - Add top 10 longest rides table with Strava links (part of #57 epic)
- #7 - Add monthly ride statistics breakdown (part of #57 epic)
- #8 - Add average speed and elevation gain metrics (part of #57 epic)
- #9 - Add interactive map showing all long ride routes (part of #57 epic)

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
1. **✅ #61** - Code Quality: Improved exception handling (replaced 4 bare except statements with specific exception types)
2. **✅ #59** - Security: Replaced MD5 with SHA256 for cache key generation
3. **✅ #60** - Security: Upgraded vulnerable dependencies (requests 2.33.0, tornado 6.5.5)
4. **✅ #56** - Implemented percentile-based route similarity to reduce over-clustering
5. **✅ #55** - Closed as superseded by #56 (Fréchet algorithm already working)

### v2.2.0 Completed (2026-03-27)
1. **✅ #41** - Created comprehensive unit tests for core modules (626 lines, 4 test files)
2. **✅ #42** - Created integration tests for full workflow (371 lines, end-to-end testing)
3. **✅ #63** - Implemented mobile-first responsive layout (P1-high sub-issue)
   - Responsive breakpoints for mobile/tablet/desktop
   - Touch-optimized controls (44px minimum)
   - Horizontal scrollable tables with sticky columns
4. **✅ #65** - Implemented touch-optimized interactions (P1-high sub-issue)
   - Touch-friendly tooltips (tap-to-show)
   - Tap feedback animations
   - Loading indicators for async actions
5. **✅ Test Infrastructure** - Created pytest configuration, test runner, and documentation

## Recommended Next Actions

1. **🔴 P0-CRITICAL: Fix Test Suite Failures** - 16/43 tests failing (70 min fix time)
   - See TEST_REMEDIATION_PLAN.md for detailed fix instructions
   - Phase 1: Fix type issues (45 min)
   - Phase 2: Fix mock configurations (15 min)
   - Phase 3: Fix edge cases (10 min)
2. **🏷️ Route Naming Epic** - Implement segment-based route naming with connection streets
3. **Implement #58** - Time-aware next commute recommendations
4. **Update #21** - Update TECHNICAL_SPEC.md with comprehensive implementation details
5. **Implement #33** - Add traffic pattern analysis
6. **Implement #54** - Weather Dashboard Implementation (Epic)
7. **Triage unprioritized issues** - Assign priority labels to remaining 15 issues