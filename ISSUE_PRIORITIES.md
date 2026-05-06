
# Issue Prioritization

**Last Updated:** 2026-05-06 19:42:26 UTC / 2026-05-06 14:42:26 CDT

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

- #76 - Background Geocoding with Progressive Report Updates

## 🔴 P1 - HIGH (Current Sprint)
Issues that significantly impact core functionality or user experience.

- #101 - Update Documentation for Long Rides Feature
- #100 - Create Comprehensive Integration Tests for All Workflows
- #99 - Create Comprehensive Unit Tests for All Core Modules
- #94 - Implement Accessibility Improvements
- #93 - Implement Comprehensive Error States
- #92 - Add Loading States with Skeleton Loaders
- #91 - Add Rate Limiting to API Endpoints
- #90 - Implement Input Validation with Marshmallow
- #89 - Add Data Persistence Layer for API
- #88 - Integrate Map with Recommendation System
- #87 - Create Recommendation Results Display Component
- #86 - Implement Frontend API Integration
- #85 - Create Interactive Recommendation Input Form
- #84 - Implement Weather API Endpoint
- #83 - Implement Geocoding API Endpoint
- #82 - Implement Recommendations API Endpoint
- #81 - Create Flask API Server for Long Rides
- #80 - Integrate Weather Forecast into Commute Tab
- #79 - Add "How It Works" Modal
- #78 - Simplify Navigation from 4 Tabs to 2 Tabs
- #54 - Weather Dashboard Implementation (Epic)
- #47 - Add Side-by-Side Route Comparison Feature

## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.

- #98 - Add Animation Performance Optimizations
- #97 - Optimize Chart Responsiveness
- #96 - Add Form Validation Feedback
- #95 - Optimize Mobile Map Performance
- #74 - Ensure selected polylines and tooltips appear on top of all map elements
- #73 - Investigate why routes 78 and 62 aren't matching in route grouping

## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.

**No P3 issues currently open** ✅

## 📋 P4 - FUTURE ENHANCEMENTS
Feature requests and enhancements for future releases.

**No P4 issues currently open** ✅

## ⚠️ Unprioritized Issues
Issues without priority labels that need to be triaged.

- #124 - Improve map polyline and tooltip z-index layering
- #123 - Investigate route matching issues for routes 78 and 62
- #122 - [LOW PRIORITY] Grey out unselected routes on map when route is clicked
- #121 - [LOW PRIORITY] Color code route names to match map line colors
- #120 - [LOW PRIORITY] Debug and fix Bootstrap tab switching functionality
- #119 - Update TECHNICAL_SPEC.md with comprehensive implementation details
- #118 - Re-enable geocoding after rate limit expires
- #117 - Fix map zoom to show start and finish when route is selected
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
- #102 - Refactor report template to extract JavaScript into separate files
- #69 - 🗺️ Map Direction Indicators
- #68 - ✨ Visual Hierarchy & Polish
- #67 - 📱 Mobile Navigation Patterns
- #66 - 🎓 Feature Discovery & Onboarding
- #65 - 👆 Touch-Optimized Interactions
- #64 - 📊 Progressive Disclosure for Metrics
- #63 - 📱 Mobile-First Responsive Layout
- #62 - 🎨 EPIC: Mobile-First UI/UX Redesign & Accessibility
- #49 - Implement Metric/Imperial Unit Toggle with Complete Consistency
- #48 - Implement Data Export in JSON, GPX, and CSV Formats
- #46 - Add PDF Export Option
- #45 - Add QR Code Generation for Mobile Transfer
- #44 - Extract HTML Template to External File
- #39 - Evaluate Photon API as Nominatim alternative
- #38 - Add social features (compare with other commuters)
- #37 - Add real-time route suggestions
- #36 - Create mobile app version
- #35 - Add integration with other fitness platforms

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
