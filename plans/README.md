# Planning Documents - Organized by Release

This directory contains all planning documents organized by the release version where the work was completed or planned.

---

## Version Numbering

**Important:** This project uses semantic versioning with 0.x.x for all pre-production releases. Version 1.0.0 is reserved for the first truly production-ready release.

**Version Mapping:**
- Original tags v2.1.0-v2.5.0 have been renumbered to v0.6.0-v0.10.0
- See [VERSIONING_PLAN.md](../docs/VERSIONING_PLAN.md) for complete details

---

## Directory Structure

```
plans/
├── v0.1.0/          # Initial Release (March 11-12, 2026)
├── v0.5.0/          # Original CLI Prototype (March 12-13, 2026) [formerly v1.0.0]
├── v0.6.0/          # Flask + SQLAlchemy + Design (March 26, 2026) [formerly v2.1.0]
├── v0.7.0/          # Test Infrastructure (March 26, 2026) [formerly v2.2.0]
├── v0.8.0/          # Route Naming (March 26, 2026) [formerly v2.3.0]
├── v0.9.0/          # Long Rides (March 30, 2026) [formerly v2.4.0]
├── v0.10.0/         # APScheduler + Docker (March 30, 2026) [formerly v2.5.0] - CURRENT
├── v0.11.0/         # Architecture Simplification (Planned - June 2026)
└── README.md        # This file
```

---

## Release v0.1.0 - Initial Release

**Date:** March 11-12, 2026  
**Tag:** v0.1.0  
**Commit:** d0b1ecd

### Planning Documents
- **PLAN.md** - Original project plan and feature roadmap
- **WORKFLOW.md** - Development workflow and processes

### Key Features
- Strava OAuth integration
- Route analysis and similarity matching
- Weather integration with wind impact
- Interactive HTML reports
- Geocoding support

---

## Release v0.5.0 - Original CLI Prototype

**Date:** March 12-13, 2026  
**Original Tag:** v1.0.0 (renumbered to v0.5.0)  
**Commit:** 7731a69

### Planning Documents
- **LONG_RIDE_RECOMMENDATIONS.md** - Long rides feature specification
- **ROUTE_SIMILARITY_OUTLIER_TOLERANCE.md** - Route matching algorithm details
- **ROUTE_MATCHING_EXPLANATION.md** - Fréchet distance implementation
- **README.md** - Version overview

### Key Features
- Long rides recommendation system with wind-optimized scoring
- Fréchet distance for route matching
- Comprehensive security enhancements
- Interactive UI features

---

## Release v0.6.0 - Flask + SQLAlchemy + Design System

**Date:** March 26, 2026  
**Original Tag:** v2.1.0 (renumbered to v0.6.0)  
**Commit:** 34033a4

### Planning Documents
- **DESIGN_PRINCIPLES.md** - Comprehensive design system (10 core principles)
- **P1_ISSUES_IMPLEMENTATION_PLAN.md** - P1 issues implementation details
- **UIUX_IMPROVEMENTS_EPIC.md** - Mobile-first UI/UX redesign specifications
- **GITHUB_ISSUE_UIUX_P1.md** - GitHub issue for UI/UX improvements
- **SPACING_REDUCTION_PLAN.md** - UI spacing optimization
- **UIUX_IMPROVEMENTS_FINDINGS.md** - UI/UX analysis findings
- **UIUX_P1_IMPROVEMENTS.md** - Priority 1 UI/UX improvements
- **README.md** - Version overview

### Key Features
- Improved exception handling
- SHA256 security migration
- Design system establishment
- UI/UX redesign roadmap (Epic #62 with 7 sub-issues)

---

## Release v0.7.0 - Test Infrastructure

**Date:** March 26, 2026  
**Original Tag:** v2.2.0 (renumbered to v0.7.0)  
**Commit:** 3df3bd8

### Planning Documents
- **TEST_REMEDIATION_PLAN.md** - Test suite remediation strategy
- **CACHE_SEPARATION_IMPLEMENTATION.md** - Cache separation architecture
- **GITHUB_ISSUES_FROM_FUTURE_TODOS.md** - Issue creation from TODO list
- **JSON_SERIALIZATION_FIX.md** - JSON serialization improvements
- **PERFORMANCE_OPTIMIZATION_PLAN.md** - Performance optimization strategy
- **README.md** - Version overview

### Key Features
- All test suite failures resolved
- Cache separation implementation
- Repository renamed to ride-optimizer
- P1 features added

---

## Release v0.8.0 - Segment-Based Route Naming

**Date:** March 26, 2026  
**Original Tag:** v2.3.0 (renumbered to v0.8.0)  
**Commit:** 1fdbc5c

### Planning Documents
- **ROUTE_NAMING_EPIC.md** - Segment-based route naming specification
- **INCREMENTAL_ANALYSIS_GUIDE.md** - Incremental analysis implementation
- **README.md** - Version overview

### Key Features
- Segment-based route naming system
- Repository organization (scripts and plans folders)
- Technical documentation updates
- Issue tracking improvements

---

## Release v0.9.0 - Long Rides Enhancement

**Date:** March 30, 2026  
**Original Tag:** v2.4.0 (renumbered to v0.9.0)

### Planning Documents
- **BLOCKED_UNTIL_GEOCODING_COMPLETE.md** - Release blocker documentation
- **GITHUB_ISSUES_LONG_RIDES.md** - Long rides GitHub issues
- **IMPLEMENTATION_STATUS.md** - Implementation progress tracking
- **LONG_RIDES_IMPLEMENTATION_PLAN.md** - Detailed implementation plan
- **LONG_RIDES_PEER_REVIEW.md** - Peer review documentation
- **README.md** - Quick reference guide
- **TEMPLATE_REFACTORING_TECHNICAL_DEBT.md** - Template cleanup plan

### Key Features
- Top 10 longest rides table with Strava links
- Monthly ride statistics breakdown
- Average speed and elevation gain metrics
- Interactive map showing all long ride routes

---

## Release v0.10.0 - APScheduler + Docker (CURRENT)

**Date:** March 30, 2026  
**Original Tag:** v2.5.0 (renumbered to v0.10.0)  
**Status:** 🟢 CURRENT RELEASE

### Planning Documents
- **BACKGROUND_GEOCODING_IMPROVEMENT.md** - Geocoding optimization
- **LONG_RIDES_REDESIGN.md** - Long rides UI/UX improvements
- **README.md** - Version overview
- **ROUTE_COMPARISON_IMPLEMENTATION_PLAN.md** - Route comparison feature
- **TEMPLATE_REFACTORING_PLAN.md** - Template cleanup strategy
- **WEATHER_DASHBOARD_IMPLEMENTATION_PLAN.md** - Weather dashboard design

### Key Features
- APScheduler for automated background jobs
- Docker containerization support
- Weather dashboard implementation
- Route comparison features
- Template refactoring

### Known Issues
This architecture is over-engineered for single-user deployment (250-300MB memory, 27 dependencies). Version 0.11.0 will simplify significantly.

---

## Release v0.11.0 - Architecture Simplification (PLANNED)

**Target Date:** June 2026 (5 weeks)
**Status:** 🔵 PLANNED

### Planning Documents
- **ARCHITECTURE_SIMPLIFICATION_PROPOSAL.md** - Detailed simplification proposal
- **ARCHITECTURE_SIMPLIFICATION_SUMMARY.md** - Executive summary
- **BETA_READINESS_REVISED_ASSESSMENT.md** - Readiness assessment
- **BETA_RELEASE_READINESS_ASSESSMENT.md** - Release criteria
- **EPIC_001_GITHUB_ISSUES.md** - Epic #001 GitHub issue breakdown
- **EPIC_237_IMPLEMENTATION_PLAN.md** - Epic #237 UI/UX redesign implementation plan
- **INTERACTIVE_MAPS_RESTORATION_EPIC.md** - Interactive maps restoration plan
- **ISSUE_COORDINATION_ANALYSIS.md** - Issue overlap and coordination analysis
- **MAP_API_ENDPOINTS_IMPLEMENTATION_PLAN.md** - Map API endpoints technical plan
- **UAT_FINDINGS_IMPLEMENTATION_PLAN.md** - UAT findings implementation roadmap
- **README.md** - Version overview

### Planned Features
- Simplified architecture (Static + API)
- 80% memory reduction (250MB → 50MB)
- Faster startup (<1 second vs 5-8 seconds)
- Fewer dependencies (27 → 12)
- 100% feature preservation

---

## Document Index by Type

### Architecture & Design
- v0.6.0/DESIGN_PRINCIPLES.md - Design system
- v0.7.0/CACHE_SEPARATION_IMPLEMENTATION.md - Cache architecture
- v0.11.0/ARCHITECTURE_SIMPLIFICATION_PROPOSAL.md - Simplification plan

### Feature Specifications
- v0.5.0/LONG_RIDE_RECOMMENDATIONS.md - Long rides feature
- v0.6.0/UIUX_IMPROVEMENTS_EPIC.md - UI/UX redesign
- v0.8.0/ROUTE_NAMING_EPIC.md - Route naming system
- v0.10.0/WEATHER_DASHBOARD_IMPLEMENTATION_PLAN.md - Weather dashboard

### Implementation Plans
- v0.6.0/P1_ISSUES_IMPLEMENTATION_PLAN.md - P1 issues
- v0.7.0/TEST_REMEDIATION_PLAN.md - Test suite fixes
- v0.9.0/LONG_RIDES_IMPLEMENTATION_PLAN.md - Long rides implementation
- v0.10.0/ROUTE_COMPARISON_IMPLEMENTATION_PLAN.md - Route comparison

### Technical Documentation
- v0.5.0/ROUTE_MATCHING_EXPLANATION.md - Fréchet distance
- v0.5.0/ROUTE_SIMILARITY_OUTLIER_TOLERANCE.md - Route matching
- v0.8.0/INCREMENTAL_ANALYSIS_GUIDE.md - Incremental analysis

### Project Management
- v0.1.0/PLAN.md - Original project plan
- v0.1.0/WORKFLOW.md - Development workflow
- v0.9.0/BLOCKED_UNTIL_GEOCODING_COMPLETE.md - Release blocker documentation

---

## Usage Guidelines

### For Developers
1. **Starting New Work**: Check the latest release folder for current planning documents
2. **Creating New Plans**: Place in the appropriate release folder based on target version
3. **Referencing Old Plans**: Use the release version to find historical context

### For Documentation
1. **Release Notes**: See `docs/releases/` for comprehensive release history
2. **Time Tracking**: See `docs/releases/TIME_TRACKING.md` for development time analysis
3. **Technical Specs**: See `docs/TECHNICAL_SPEC.md` for current system architecture

---

## Release Timeline

| Version | Date | Type | Planning Docs | Key Focus |
|---------|------|------|---------------|-----------|
| v0.1.0 | Mar 11-12 | Initial | 2 docs | Foundation & Core Features |
| v0.5.0 | Mar 12-13 | Major | 4 docs | Long Rides & Security (formerly v1.0.0) |
| v0.6.0 | Mar 26 | Minor | 8 docs | Code Quality & Design (formerly v2.1.0) |
| v0.7.0 | Mar 26 | Minor | 6 docs | Testing & Architecture (formerly v2.2.0) |
| v0.8.0 | Mar 26 | Minor | 3 docs | Route Naming & Organization (formerly v2.3.0) |
| v0.9.0 | Mar 30 | Minor | 7 docs | Long Rides Enhancement (formerly v2.4.0) |
| v0.10.0 | Mar 30 | Minor | 6 docs | APScheduler + Docker (formerly v2.5.0) - CURRENT |
| v0.11.0 | Jun 2026 | Minor | 11 docs | Architecture Simplification - PLANNED |

**Total Planning Documents:** 47 documents across 8 releases

---

## Related Documentation

- **[VERSIONING_PLAN.md](../docs/VERSIONING_PLAN.md)** - Complete versioning strategy and rationale
- **[RELEASE_ROADMAP.md](../RELEASE_ROADMAP.md)** - Future release planning
- **[ISSUE_PRIORITIES.md](../ISSUE_PRIORITIES.md)** - Current issue priorities and roadmap
- **[docs/TECHNICAL_SPEC.md](../docs/TECHNICAL_SPEC.md)** - System architecture and specifications

---

*Last Updated: May 7, 2026*  
*Organization Structure: Release-based planning document archive*  
*Version Numbering: Aligned with semantic versioning (0.x.x for pre-production)*