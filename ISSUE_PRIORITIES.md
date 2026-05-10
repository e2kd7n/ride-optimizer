# Issue Prioritization

**Last Updated:** 2026-05-10 03:41:00 UTC / 2026-05-09 22:41:00 CDT

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

- #267 - Route Cards Non-Interactive, Missing Detail View API
- #266 - Mobile Bottom Navigation Non-Functional

## 🔴 P1 - HIGH (Current Sprint)
Issues that significantly impact core functionality or user experience.

- #271 - Add Performance Metrics and Historical Data
- #270 - Implement Route Comparison Feature
- #269 - Improve Mobile Filter UX with Quick Presets
- #268 - Add Difficulty Ratings to All Routes
- #265 - 🎯 EPIC: UAT Findings - Critical Navigation & Interaction Fixes + UX Enhancements
- #264 - Dashboard and Route Library UX Review
- #262 - Remove Legacy CLI Application Remnants
- #260 - Implement guided FTUE for Strava API key setup with in-app configuration
- #256 - UI/UX Refinements: Design Critique Follow-up
- #255 - Add Comprehensive E2E Testing for UI/UX Features
- #254 - Implement Animated GIF Tutorials for Key Features
- #226 - Fix Planner Error Handling Test
- #224 - Fix Route Library Search API Response Format
- #223 - Fix Mobile Navigation Elements
- #222 - Complete Planner Template Content
- #221 - Add Missing Commute View Content
- #220 - Add Missing Dashboard Content
- #208 - Create test data fixtures for integration testing
- #206 - Implement lazy service initialization to fix performance issues
- #205 - Create missing QA test harnesses for dashboard, commute, and planner
- #204 - UI/UX: Update polyline colors
- #177 - UI/UX: Add clickable 'Uses' column with modal
- #176 - UI/UX: Add table sorting functionality
- #175 - UI/UX: Simplify route counter
- #174 - UI/UX: Fix route name display
- #173 - UI/UX: Fix page counter display
- #172 - Add Marshmallow validation schemas for planner endpoints
- #171 - Build planner frontend UI (currently placeholder only)
- #164 - Test Coverage: report_generator.py (47% → 80%)
- #163 - Test Coverage: data_fetcher.py (49% → 80%)

## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.

- #274 - Add Last Updated Timestamps
- #273 - Implement Route Sorting Options
- #272 - Add Hourly Weather Forecast
- #263 - Refine Settings Form Structure
- #227 - Improve Test Coverage for New Features
- #209 - Implement graceful degradation for unavailable services
- #207 - Implement dependency injection pattern for better testability
- #194 - Long Rides: Add accessibility features (WCAG 2.1 AA)
- #193 - Long Rides: Implement skeleton loaders and error states
- #192 - Establish PR review requirements
- #191 - Implement workout-aware logic if #140 is incomplete
- #190 - Implement actual TrainerRoad integration if #139 is incomplete
- #189 - Implement actual weather integration if #138 is incomplete
- #188 - Verify GitHub issues #138, #139, #140 status
- #187 - Testing: Increase Route Namer coverage 15% → 50%
- #186 - Testing: Increase Route Analyzer coverage 20% → 50%
- #185 - Testing: Increase Data Fetcher coverage 49% → 80%
- #184 - Testing: Increase Long Ride Analyzer coverage 13% → 50%
- #183 - Code Quality: Add debug logging for exception handlers
- #182 - Code Quality: Replace 4 bare except statements with specific exceptions
- #180 - Add planner-specific API client methods
- #179 - Add PII sanitization to logging
- #178 - Implement log rotation with RotatingFileHandler
- #168 - Create PRIVACY.md policy for compliance
- #165 - Test Coverage: route_namer.py (15% → 50%)
- #158 - 📋 Version Rebaseline Complete - Documentation Record
- #141 - Add repeat-a-past-ride flow and saved plan support
- #136 - Implement settings and preferences page for home/work locations, units, time windows, and planner defaults
- #128 - Fix "Unnamed Activity" display in Route Comparison uses modal
- #127 - Reduce excessive whitespace between report sections

## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.

- #202 - Setup weekly maintenance routine
- #201 - Reduce P1 issue count to <25
- #200 - Route naming improvements (Start → Main → End format)
- #199 - Design: Test on real iOS/Android devices
- #196 - Design: Ensure touch targets ≥44x44px with 8px spacing
- #195 - Design: Verify mobile-first responsive design (320px viewport)
- #170 - Design: Test keyboard navigation and screen reader support
- #169 - Design: Verify WCAG AA contrast ratios (4.5:1)
- #145 - 🌤️ EPIC: Weather Dashboard & Forecast Integration
- #120 - [LOW PRIORITY] Debug and fix Bootstrap tab switching functionality
- #54 - Weather Dashboard Implementation (Epic)
- #49 - Implement Metric/Imperial Unit Toggle with Complete Consistency
- #48 - Implement Data Export in JSON, GPX, and CSV Formats
- #46 - Add PDF Export Option
- #45 - Add QR Code Generation for Mobile Transfer
- #44 - Extract HTML Template to External File

## 📋 P4 - FUTURE ENHANCEMENTS
Feature requests and enhancements for future releases.

- #203 - Implement GDPR-compliant data deletion endpoint
- #80 - Integrate Weather Forecast into Commute Tab
- #79 - Add "How It Works" Modal
- #68 - ✨ Visual Hierarchy & Polish
- #67 - 📱 Mobile Navigation Patterns
- #66 - 🎓 Feature Discovery & Onboarding
- #65 - 👆 Touch-Optimized Interactions
- #64 - 📊 Progressive Disclosure for Metrics
- #63 - 📱 Mobile-First Responsive Layout
- #62 - 🎨 EPIC: Mobile-First UI/UX Redesign & Accessibility
- #47 - Add Side-by-Side Route Comparison Feature
- #39 - Evaluate Photon API as Nominatim alternative
- #38 - Add social features (compare with other commuters)
- #37 - Add real-time route suggestions
- #36 - Create mobile app version
- #35 - Add integration with other fitness platforms

## ⚠️ Unprioritized Issues
Issues without priority labels that need to be triaged.

- #261 - Senior Engineer Code Review Request
- #166 - Complete and review full analysis with Fréchet algorithm

## 📝 Workspace TODOs & Tasks
Code comments and inline tasks found in the workspace that may need attention.

Found **2** code comments requiring attention:

- `app/static/js/map-filters.js` - 100:                // TODO: Highlight route on map (requires map layer access)
- `static/js/dashboard.js` - 7:// NOTE: Initialization is handled by inline script in index.html

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
2. Run `./scripts/update-issue-priorities.sh` to regenerate this file
3. Commit changes with descriptive message
4. Communicate priority changes to team

## Managing Workspace TODOs

- Review code comments regularly and convert important ones to GitHub issues
- Use `TODO:` for tasks that should become issues
- Use `FIXME:` for bugs that need attention
- Use `HACK:` for temporary solutions that need proper fixes
- Use `NOTE:` for important information or context
