# Version 0.10.0 - APScheduler + Docker (Current)

**Release Date:** March 30, 2026  
**Original Tag:** v2.5.0 (renumbered to v0.10.0)  
**Architecture:** Flask + SQLAlchemy + APScheduler + Docker

## Overview

This is the current release, featuring automated scheduling with APScheduler and Docker containerization. While functional, this architecture is considered over-engineered for single-user deployment and is planned for simplification in v0.11.0.

## Key Features

- **APScheduler** - Automated background job scheduling
- **Docker Support** - Containerized deployment
- **Weather Dashboard** - Comprehensive weather integration
- **Route Comparison** - Side-by-side route comparison
- **Template Refactoring** - Continued template improvements
- **Background Geocoding** - Improved geocoding performance

## Planning Documents

- **BACKGROUND_GEOCODING_IMPROVEMENT.md** - Geocoding optimization
- **LONG_RIDES_REDESIGN.md** - Long rides UI/UX improvements
- **README.md** - Version overview
- **ROUTE_COMPARISON_IMPLEMENTATION_PLAN.md** - Route comparison feature
- **TEMPLATE_REFACTORING_PLAN.md** - Template cleanup strategy
- **WEATHER_DASHBOARD_IMPLEMENTATION_PLAN.md** - Weather dashboard design

## Architecture Characteristics

- **Memory Usage:** 250-300MB (high for single-user)
- **Dependencies:** 27 packages
- **Startup Time:** 5-8 seconds
- **Complexity:** High (Flask + SQLAlchemy + APScheduler + Docker)

## Known Issues

This architecture is **over-engineered** for the target use case (single-user Raspberry Pi deployment). Version 0.11.0 will simplify the architecture significantly.

## Version History Note

This release was originally tagged as v2.5.0 but has been renumbered to v0.10.0 to align with semantic versioning conventions. This is part of the pre-1.0 development cycle.

---

*Part of the pre-1.0 development cycle (v0.x.x series)*  
*Current release - planned for simplification in v0.11.0*