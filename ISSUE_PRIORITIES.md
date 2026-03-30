# Issue Prioritization

**Last Updated:** 2026-03-29 16:57 UTC

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

### Active P0 Issues

**None** ✅

## 🔴 P1 - HIGH (Current Sprint)
Issues that significantly impact core functionality or user experience.

### Active P1 Issues

- #57 - 🎯 EPIC: Long Rides Analysis & Recommendations (consolidates #6, #7, #8, #9)
  - **Phase 1: Navigation Redesign (Week 1, Days 1-2)**
    - #78 - Simplify Navigation from 4 Tabs to 2 Tabs (4h)
    - #79 - Add "How It Works" Modal (2h)
    - #80 - Integrate Weather Forecast into Commute Tab (2h)
  - **Phase 2-3: Statistics & Map (Week 1, Days 3-5 + Week 2, Days 1-2)**
    - #6 - Add top 10 longest rides table with Strava links
    - #7 - Add monthly ride statistics breakdown
    - #8 - Add average speed and elevation gain metrics
    - #9 - Add interactive map showing all long ride routes
  - **Phase 4: Backend API Layer (Week 2, Days 3-5)**
    - #81 - Create Flask API Server for Long Rides (6h)
    - #82 - Implement Recommendations API Endpoint (4h)
    - #83 - Implement Geocoding API Endpoint (2h)
    - #84 - Implement Weather API Endpoint (2h)
  - **Phase 5: Interactive Recommendations (Week 3)**
    - #85 - Create Interactive Recommendation Input Form (4h)
    - #86 - Implement Frontend API Integration (4h)
    - #87 - Create Recommendation Results Display Component (4h)
    - #88 - Integrate Map with Recommendation System (4h)
  - **Phase 6: Backend Improvements (Week 4)**
    - #89 - Add Data Persistence Layer for API (4h)
    - #90 - Implement Input Validation with Marshmallow (3h)
    - #91 - Add Rate Limiting to API Endpoints (2h)
  - **Phase 7: Frontend Polish (Week 5)**
    - #92 - Add Loading States with Skeleton Loaders (3h)
    - #93 - Implement Comprehensive Error States (3h)
    - #94 - Implement Accessibility Improvements (4h)
  - **Testing & Documentation**
    - #99 - Create Comprehensive Unit Tests for All Core Modules (8-10h) - Supersedes #41
    - #100 - Create Comprehensive Integration Tests for All Workflows (8-10h) - Supersedes #42
    - #101 - Update Documentation for Long Rides Feature (3h)
- #54 - Weather Dashboard Implementation (Epic)
- #47 - Add Side-by-Side Route Comparison Feature


## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.

- #73 - Investigate why routes 78 and 62 aren't matching in route grouping
- #74 - Ensure selected polylines and tooltips appear on top of all map elements
- #62 - 🎨 EPIC: Mobile-First UI/UX Redesign & Accessibility
  - #63 - Mobile-First Responsive Layout (in progress)
  - #64 - Progressive Disclosure for Metrics
  - #65 - Touch-Optimized Interactions (in progress)
  - #66 - Feature Discovery & Onboarding
  - #67 - Mobile Navigation Patterns
  - #68 - Visual Hierarchy & Polish

### P2 Issues from Long Rides Feature (Phase 7 - Polish)
- #95 - Optimize Mobile Map Performance (3h)
- #96 - Add Form Validation Feedback (2h)
- #97 - Optimize Chart Responsiveness (2h)
- #98 - Add Animation Performance Optimizations (2h)



## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.

- #22 - Debug and fix Bootstrap tab switching functionality

## 📋 P4 - FUTURE ENHANCEMENTS
Feature requests and enhancements for future releases.



## ⚠️ Unprioritized Issues
Issues without priority labels that need to be triaged.

- #49 - Implement Metric/Imperial Unit Toggle with Complete Consistency
- #48 - Implement Data Export in JSON, GPX, and CSV Formats
- #46 - Add PDF Export Option
- #45 - Add QR Code Generation for Mobile Transfer
- #44 - Extract HTML template to external file
- #39 - Evaluate Photon API as Nominatim alternative
- #38 - Add social features (compare with other commuters)
- #37 - Add real-time route suggestions
- #36 - Create mobile app version
- #35 - Add integration with other fitness platforms



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

- **Total Open Issues:** 28
- **P0 (Critical):** 0 ✅
- **P1 (High):** 23 (includes 18 new Long Rides issues)
- **P2 (Medium):** 6 (includes 4 new Long Rides polish issues)
- **P3 (Low):** 1
- **P4 (Future):** 0
- **Unprioritized:** 0
- **Recently Closed:** 14 issues (see "Recently Completed" section below)

### v2.4.0 Long Rides Feature Breakdown
- **Total New Issues:** 24 (#78-#101)
- **P1-high:** 18 issues (core functionality, API, testing, docs)
- **P2-medium:** 4 issues (polish and optimization)
- **P3-low:** 2 issues (deferred to v2.5.0/v2.6.0)
- **Estimated Total Effort:** 88-98 hours (5-6 weeks at 16-18 hours/week)
  - Note: Testing effort increased from 8h to 16-20h to cover all core modules and workflows

**Note:** Completed issues are documented in release notes (RELEASE_NOTES.md) and version-specific plans (plans/v2.x.0/).

## Recommended Next Actions

Focus on P1 issues for next sprint:

1. **#99** - Create Comprehensive Unit Tests for All Core Modules (P1-high, 8-10h)
   - Covers: Long Rides API, route analyzer, data fetcher, optimizer, weather fetcher, location finder
   - Target: 80% overall code coverage
   - Supersedes #41

2. **#100** - Create Comprehensive Integration Tests for All Workflows (P1-high, 8-10h)
   - Covers: Long Rides flow, commute analysis, route matching, weather integration
   - Includes edge cases and error scenarios
   - Supersedes #42

### Additional Actions (Not Issues)
- **CI/CD Integration** - Set up GitHub Actions with expanded test suite

---

## 🎉 Recently Completed

### Completed 2026-03-29

- **#34 - Add carbon footprint calculations** (COMPLETED 2026-03-29)
  - Created comprehensive CarbonCalculator module for environmental impact analysis
  - Calculates CO2 emissions saved vs driving
  - Tracks gasoline saved and money saved on fuel
  - Calculates calories burned and health benefits
  - Provides tree equivalency and environmental impact statements
  - Supports time-based projections (daily/weekly/monthly/yearly)
  - Route-by-route carbon footprint breakdown
  - Added carbon configuration to config.yaml
  - Supports both metric and imperial units
  - Files: src/carbon_calculator.py, config/config.yaml
  - Commit: 56e83fc
  - Priority: P1-high

- **#33 - Add traffic pattern analysis** (COMPLETED 2026-03-29)
  - Created comprehensive TrafficAnalyzer module for analyzing commute patterns
  - Analyzes usage by hour of day and day of week
  - Identifies peak/off-peak times and rush hour penalties
  - Calculates optimal departure times based on historical data
  - Provides traffic scores for route comparison at specific times
  - Added traffic configuration to config.yaml
  - Supports configurable rush hour windows
  - Files: src/traffic_analyzer.py, config/config.yaml
  - Commit: 40e910f
  - Priority: P1-high

- **#77 - Add user preferences configuration for browser, units, and other toggleable settings** (COMPLETED 2026-03-29)
  - Implemented user preferences system with config file support
  - Added browser selection (Chrome, Firefox, Safari, Edge, Brave)
  - Added unit system toggle (metric/imperial)
  - Added auto-open browser preference
  - Files: src/config.py, config/config.yaml
  - Priority: P1-high

- **#70 - Implement wind-aware route selection in forecast generator** (COMPLETED 2026-03-29)
  - Enhanced forecast generator to consider wind conditions
  - Integrated wind speed and direction into route recommendations
  - Added wind favorability scoring
  - Files: src/forecast_generator.py
  - Priority: P1-high

- **#58 - Show time-aware next commute recommendations (to work & to home)** (COMPLETED 2026-03-29)
  - Implemented intelligent time-based recommendations
  - Separate "to work" and "to home" route suggestions
  - Forecast weather for specific time windows
  - Wind favorability assessment
  - See NEXT_COMMUTE_FEATURE.md for details
  - Priority: P1-high

- **#25 - Implement automatic token refresh for expired Strava tokens** (COMPLETED 2026-03-29)
  - Added automatic token refresh mechanism
  - Improved authentication flow
  - Better error handling for expired tokens
  - Files: src/auth_secure.py
  - Priority: P1-high

- **#42 - Write integration tests for full workflow** (COMPLETED 2026-03-29)
  - Created comprehensive integration test suite
  - Covers full workflow from data fetching to report generation
  - Includes edge cases and error scenarios
  - Files: tests/test_integration.py
  - Priority: P1-high
  - Note: Superseded by #100 for expanded coverage

- **#41 - Create unit tests for core modules** (COMPLETED 2026-03-29)
  - Implemented unit tests for core functionality
  - Covers route analyzer, data fetcher, and other modules
  - Improved code coverage
  - Files: tests/test_route_analyzer.py, tests/test_data_fetcher.py, tests/test_units.py
  - Priority: P1-high
  - Note: Superseded by #99 for expanded coverage

### Completed 2026-03-27

- **#72 - Test: Investigate why routes 78 and 62 aren't matching** (COMPLETED 2026-03-27)
  - Investigated route matching algorithm
  - Identified and resolved matching issues
  - Improved route grouping logic
  - Priority: P2-medium

- **#61 - Code Quality: Improve exception handling (remove bare except)** (COMPLETED 2026-03-27)
  - Removed bare except clauses
  - Added specific exception handling
  - Improved error messages and logging
  - Priority: P3-low

- **#60 - Security: Upgrade vulnerable dependencies (requests, tornado, pygments)** (COMPLETED 2026-03-27)
  - Updated vulnerable dependencies to secure versions
  - Resolved security vulnerabilities
  - Updated requirements.txt
  - Priority: P1-high, security

- **#59 - Security: Replace MD5 hash with SHA256 for cache keys** (COMPLETED 2026-03-27)
  - Migrated from MD5 to SHA256 for cache key generation
  - Improved security posture
  - Updated cache handling logic
  - Priority: P2-medium, security

- **#56 - Implement percentile-based route similarity to reduce over-clustering** (COMPLETED 2026-03-27)
  - Implemented percentile-based similarity algorithm
  - Reduced over-clustering of routes
  - Improved route grouping accuracy
  - Priority: P1-high

### UI/UX Improvements
- **#71 - UI/UX Improvements for Route Comparison Table and Map** (COMPLETED 2026-03-27)
  - All 7 improvements implemented
  - Table sorting functionality with visual indicators
  - Fixed route group name display (geographic names)
  - Updated polyline colors to semantic system (green=optimal)
  - Removed "View on Strava" button, made route name clickable
  - Made "Uses" column clickable to show matched activities modal
  - Fixed page counter display
  - Simplified route counter display
  - Files: templates/report_template.html, src/route_analyzer.py, config/config.yaml
  - Priority: P1-high

- **#69 - Map Direction Indicators** (COMPLETED 2026-03-27)
  - Implemented direction arrows on Next Commute map
  - Stacked card layout for "To Work" and "To Home" recommendations
  - Dense information display with 6 compact metrics per card
  - Interactive map with color-coded routes (green for "to work", blue for "to home")
  - Direction arrows using screen-space bearing calculation
  - Click handlers to highlight and zoom to specific routes
  - Responsive design with mobile breakpoints
  - Files: templates/report_template.html
  - Priority: P1-high

- **#75 - Add current weather conditions display to map** (COMPLETED 2026-03-27)
  - Shows real-time weather on interactive map
  - Temperature with unit conversion
  - Wind speed and direction (cardinal + degrees)
  - Precipitation amount
  - Integrates with WeatherFetcher and Open-Meteo API
  - Priority: P2-medium

- **#21 - Update TECHNICAL_SPEC.md** (COMPLETED 2026-03-27)
  - Updated 3 major sections with comprehensive implementation details
  - Route naming algorithm documentation
  - Security improvements (MD5 → SHA256)
  - Exception handling enhancements
  - Priority: P2-medium