# Issue Prioritization

**Last Updated:** 2026-05-07 12:50:32 UTC / 2026-05-07 07:50:32 CDT

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

- #157 - Phases 4-5: QA Testing & Beta Preparation
- #156 - Phase 3: Integration Work - Convert APScheduler to Cron + Testing
- #155 - Phase 2: Frontend Conversion - Templates to Static HTML + JavaScript
- #153 - Phase 1: Foundation Migration - Extract Services & Create Minimal API
- #152 - Architecture Simplification: Migrate to Smart Static for Pi Optimization
- #76 - Background Geocoding with Progressive Report Updates

## 🔴 P1 - HIGH (Current Sprint)
Issues that significantly impact core functionality or user experience.

- #144 - 🌐 EPIC: Personal Web Platform Migration (v1.0.0)
- #119 - Update TECHNICAL_SPEC.md with comprehensive implementation details
- #118 - Re-enable geocoding after rate limit expires
- #117 - Fix map zoom to show start and finish when route is selected
- #102 - Refactor report template to extract JavaScript into separate files
- #101 - Update Documentation for Long Rides Feature
- #91 - Add Rate Limiting to API Endpoints
- #90 - Implement Input Validation with Marshmallow
- #89 - Add Data Persistence Layer for API
- #84 - Implement Weather API Endpoint
- #83 - Implement Geocoding API Endpoint
- #82 - Implement Recommendations API Endpoint
- #81 - Create Flask API Server for Long Rides
- #80 - Integrate Weather Forecast into Commute Tab
- #79 - Add "How It Works" Modal
- #54 - Weather Dashboard Implementation (Epic)
- #47 - Add Side-by-Side Route Comparison Feature

## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.

- #160 - Fix authentication mocking in API integration tests
- #158 - 📋 Version Rebaseline Complete - Documentation Record
- #141 - Add repeat-a-past-ride flow and saved plan support
- #136 - Implement settings and preferences page for home/work locations, units, time windows, and planner defaults
- #128 - Fix "Unnamed Activity" display in Route Comparison uses modal
- #127 - Reduce excessive whitespace between report sections
- #122 - [LOW PRIORITY] Grey out unselected routes on map when route is clicked
- #121 - [LOW PRIORITY] Color code route names to match map line colors
- #116 - Add visual weather icons and color coding
- #115 - Display optimal departure time suggestions
- #114 - Add transit recommendations when conditions are poor
- #113 - Show optimal route recommendations based on wind
- #112 - Add weather severity indicators (good/fair/poor/miserable icons)
- #111 - Add evening commute window (3-6 PM) weather display
- #110 - Add morning commute window (7-9 AM) weather display
- #109 - Design 7-day forecast card layout
- #108 - Integrate forecast generator into main.py workflow
- #107 - Add interactive map showing all long ride routes
- #106 - Add average speed and elevation gain metrics
- #105 - Add monthly ride statistics breakdown
- #94 - Implement Accessibility Improvements
- #93 - Implement Comprehensive Error States
- #92 - Add Loading States with Skeleton Loaders
- #74 - Ensure selected polylines and tooltips appear on top of all map elements
- #73 - Investigate why routes 78 and 62 aren't matching in route grouping

## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.

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

**No unprioritized issues** ✅

## 📝 Workspace TODOs & Tasks
Code comments and inline tasks found in the workspace that may need attention.

**No TODO/FIXME comments found in code** ✅

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
