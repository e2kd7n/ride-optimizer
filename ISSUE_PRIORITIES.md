# Issue Prioritization

**Last Updated:** 2026-03-26 22:31 UTC

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

**No P0 issues currently open** ✅

## 🔴 P1 - HIGH (Current Sprint)
Issues that significantly impact core functionality or user experience.

- #60 - Security: Upgrade vulnerable dependencies (requests, tornado, pygments)
- #58 - Show time-aware next commute recommendations (to work & to home)
- #56 - Implement percentile-based route similarity to reduce over-clustering
- #55 - Complete and review full analysis with Fréchet algorithm


## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.

- #59 - Security: Replace MD5 hash with SHA256 for cache keys
- #21 - Update TECHNICAL_SPEC.md with comprehensive implementation details
- #24 - [LOW PRIORITY] Grey out unselected routes on map when route is clicked

## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.

- #61 - Code Quality: Improve exception handling (remove bare except)
- #22 - [LOW PRIORITY] Debug and fix Bootstrap tab switching functionality
- #41 - Create unit tests for core modules
- #42 - Write integration tests for full workflow

## 📋 P4 - FUTURE ENHANCEMENTS
Feature requests and enhancements for future releases.

- #57 - 🎯 EPIC: Long Rides Analysis & Recommendations (consolidates #6, #7, #8, #9)
- #54 - Weather Dashboard Implementation (Epic)
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
- #33 - Add traffic pattern analysis
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

- **Total Open Issues:** 32
- **P0 (Critical):** 0
- **P1 (High):** 4
- **P2 (Medium):** 3
- **P3 (Low):** 4
- **P4 (Future):** 6
- **Unprioritized:** 15

## Recommended Next Actions

1. **🔒 Security #60** - Upgrade vulnerable dependencies (IMMEDIATE)
2. **Implement #58** - Time-aware next commute recommendations (highest user value)
3. **Implement #56** - Fix route similarity algorithm (highest impact on core functionality)
4. **🔒 Security #59** - Replace MD5 with SHA256 in cache keys
5. **Complete #55** - Validate Fréchet algorithm improvements
6. **Triage unprioritized issues** - Assign priority labels to remaining 15 issues