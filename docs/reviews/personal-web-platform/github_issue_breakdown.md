# GitHub Issue Breakdown for the Personal Web Platform

**Source proposal:** [`docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md`](docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md)  
**Consolidated review:** [`docs/reviews/personal-web-platform/consolidated_implementation_plan.md`](docs/reviews/personal-web-platform/consolidated_implementation_plan.md)  
**Status:** Draft breakdown for issue creation and subagent execution  
**Date:** 2026-05-06

---

## Purpose

This document does two things:

1. Re-slot currently open GitHub issues against the approved personal web platform direction.
2. Define the missing implementation issues needed so multiple engineers or subagents can begin work in parallel.

The approved product direction is no longer “improve the HTML report UI a bit more.” It is now a **single-user, local-first cycling decision platform** with:
- a recommendation-first dashboard
- commute recommendations
- long ride planning
- route library access
- workout-aware commute support
- Raspberry Pi-friendly operations and reliability

That means some open issues still matter, but many are tied to the older report-centric prototype and should be treated as **legacy reference work** rather than next-release implementation drivers.

---

## Re-Slotting Existing Open Issues

## Keep as Legacy / Prototype Reference

These issues represent real bugs or UI improvements, but they belong to the current or historical report-based prototype rather than the approved next-release platform architecture.

- [#78](https://github.com/e2kd7n/ride-optimizer/issues/78) Simplify Navigation from 4 Tabs to 2 Tabs  
  **Disposition:** legacy reference  
  **Reason:** tied to the current tabbed report UI, which is being replaced by dedicated web routes and a recommendation-first dashboard.

- [#79](https://github.com/e2kd7n/ride-optimizer/issues/79) Add "How It Works" Modal  
  **Disposition:** legacy reference  
  **Reason:** the need for onboarding remains valid, but modal-based help inside the report UI should not drive the new implementation. Replace with web-platform onboarding/help content later.

- [#80](https://github.com/e2kd7n/ride-optimizer/issues/80) Integrate Weather Forecast into Commute Tab  
  **Disposition:** legacy reference  
  **Reason:** the product need is valid, but “commute tab” is old UI vocabulary. Weather belongs in the dashboard and commute recommendation views for the new platform.

- [#127](https://github.com/e2kd7n/ride-optimizer/issues/127) Reduce excessive whitespace between report sections  
  **Disposition:** legacy reference  
  **Reason:** useful only if continuing to polish the report prototype in parallel; not a driver for the new platform.

- [#128](https://github.com/e2kd7n/ride-optimizer/issues/128) Fix "Unnamed Activity" display in Route Comparison uses modal  
  **Disposition:** legacy reference  
  **Reason:** valid bug in the current report modal, but coupled to legacy report internals rather than the upcoming route library and ride history web views.

## Rescope into the New Platform Release

These issues point at needed work, but the issue framing is too tied to the prior “long rides Flask API plus frontend” transition plan. They should be retained conceptually and rewritten or superseded with new platform-scoped issues.

- [#81](https://github.com/e2kd7n/ride-optimizer/issues/81) Create Flask API Server for Long Rides  
  **Disposition:** rescope  
  **New framing:** create the Flask application shell and route structure for the personal web platform, not a long-rides-only API server.

- [#82](https://github.com/e2kd7n/ride-optimizer/issues/82) Implement Recommendations API Endpoint  
  **Disposition:** rescope  
  **New framing:** internal recommendation snapshot and JSON endpoints backing dashboard and commute flows.

- [#83](https://github.com/e2kd7n/ride-optimizer/issues/83) Implement Geocoding API Endpoint  
  **Disposition:** rescope  
  **New framing:** settings/preferences geocoding workflow and background geocoding job integration for the web platform.

- [#84](https://github.com/e2kd7n/ride-optimizer/issues/84) Implement Weather API Endpoint  
  **Disposition:** rescope  
  **New framing:** weather service integration and snapshot/API exposure for dashboard, commute, and planner decisions.

- [#100](https://github.com/e2kd7n/ride-optimizer/issues/100) Create Comprehensive Integration Tests for All Workflows  
  **Disposition:** rescope  
  **New framing:** integration coverage for core platform workflows, especially dashboard freshness, commute recommendations, planner flows, route library access, and degraded mode behavior.

## Carry Forward as Background Context Only

These items in [`ISSUE_PRIORITIES.md`](ISSUE_PRIORITIES.md) and [`docs/FUTURE_TODOS.md`](docs/FUTURE_TODOS.md) remain useful as future references but are not immediate release anchors for the new platform:
- map polish issues
- report-template UI cleanup
- mobile-report refinements
- legacy workflow enhancements
- route grouping bug investigations that do not block the platform foundation

Some of these will later map into route library UX improvements or route-quality work, but they should not shape the initial issue tree.

---

## Recommended Squad / Subagent Structure

To allow parallel implementation, work should be split into five lanes.

### Squad A: Platform Foundation
Owns app skeleton, service boundaries, shared infrastructure, and schema setup.

### Squad B: Commute and Dashboard
Owns the recommendation-first dashboard, commute flows, and decision presentation.

### Squad C: Planner and Route Library
Owns long ride planning, route browsing, repeat-a-past-ride flows, and route detail views.

### Squad D: Reliability and Operations
Owns scheduler, job state, freshness, degraded mode, persistence boundaries, and Pi readiness.

### Squad E: Integrations and QA
Owns TrainerRoad integration, onboarding/explainability support, automated tests, and end-to-end quality checks.

---

## Missing GitHub Issues to Create

The following issues should be created to match the approved architecture and to let subagents begin implementation in parallel.

---

## Issue 1: Create Flask App Shell and Route Blueprint Structure

**Suggested title:** Create Flask app factory, route blueprints, and web-platform skeleton

**Suggested squad:** Squad A  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
The approved platform needs a real web application skeleton with clear route ownership. Existing issue [#81](https://github.com/e2kd7n/ride-optimizer/issues/81) is too narrow and too long-rides-specific.

### Scope
- Create Flask app factory structure
- Add route blueprints for dashboard, commute, planner, route library, settings, and lightweight internal API
- Add base template/layout shell
- Add configuration wiring suitable for local Pi deployment
- Preserve a clean boundary between web routes and service-layer logic

### Expected file/module targets
- `app/__init__.py`
- `app/routes/dashboard.py`
- `app/routes/commute.py`
- `app/routes/planner.py`
- `app/routes/route_library.py`
- `app/routes/settings.py`
- `app/routes/api.py`
- `templates/base.html`

### Acceptance criteria
- Flask app starts through an app factory
- Each major product area has its own route module
- A base layout renders successfully
- Route handlers call services or placeholders, not legacy CLI orchestration directly
- Project structure supports further parallel work without route collisions

### Dependencies
None. This is one of the first issues that should begin immediately.

---

## Issue 2: Extract Shared Analysis and Recommendation Service Layer

**Suggested title:** Extract shared service layer for analysis, recommendations, planner logic, and route-library access

**Suggested squad:** Squad A  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
The consolidated review explicitly says the platform should not be built by wiring Flask routes directly into the legacy CLI path. This is the key maintainability issue.

### Scope
- Define service modules for shared business logic
- Move reusable orchestration and data preparation out of route handlers
- Separate web-facing inputs/outputs from underlying analysis internals
- Establish stable interfaces for dashboard, commute, planner, and route-library consumers

### Expected file/module targets
- `services/analysis_service.py`
- `services/commute_service.py`
- `services/planner_service.py`
- `services/route_library_service.py`
- shared DTO or serializer helpers as needed

### Acceptance criteria
- Web handlers consume service-layer methods
- Service interfaces are documented and stable enough for parallel squads
- Existing analysis logic can be invoked without duplicating CLI-specific flow
- Clear ownership exists for recommendation generation, planner ranking, and route retrieval

### Dependencies
Can begin in parallel with Issue 1, but should align closely with the app skeleton.

---

## Issue 3: Implement SQLite Schema and Persistence Boundaries for Web State

**Suggested title:** Add SQLite-backed persistence for snapshots, preferences, route summaries, and job state

**Suggested squad:** Squad A with Squad D support  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
The approved architecture uses hybrid persistence. SQLite needs to become the home for structured state without trying to absorb all heavy artifacts.

### Scope
- Define initial schema for recommendation snapshots, preferences, route summaries, planner sessions, saved plans, job history, workout metadata, and status/error records
- Add migration/bootstrap approach
- Document authoritative ownership between SQLite and file caches
- Store enough structured state to support web rendering without re-running all analysis on every page load

### Acceptance criteria
- Schema exists for core web-platform entities
- App can initialize or migrate local database safely
- Data ownership between SQLite and file caches is explicit
- Snapshot reads support dashboard and commute views
- Job and error state can be recorded for later reliability work

### Dependencies
Should start early; unlocks dashboard, settings, and reliability work.

---

## Issue 4: Build Recommendation-First Dashboard

**Suggested title:** Build recommendation-first dashboard with freshness, status, and workout-fit summary

**Suggested squad:** Squad B  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
The dashboard is the top-level product surface. The consolidated review explicitly recommends a recommendation-first dashboard.

### Scope
- Build dashboard page and template
- Surface best current commute recommendation
- Surface workout-fit summary when available
- Show freshness and last successful analysis metadata
- Provide shortcuts to commute, planner, route library, and refresh actions

### Acceptance criteria
- Dashboard answers “what should I ride today?” at a glance
- Recommendation card is primary content
- Freshness and health are visible but secondary
- Missing TrainerRoad data does not break dashboard rendering
- Dashboard works on mobile-sized screens

### Dependencies
Needs app shell and initial snapshot/service work.

---

## Issue 5: Implement Commute Recommendation Views and Explanation Model

**Suggested title:** Implement commute recommendation views with alternatives, weather impact, and confidence framing

**Suggested squad:** Squad B  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
Commute recommendations are a core daily-use flow and the clearest bridge from current functionality to the new product.

### Scope
- Build morning and evening commute pages
- Show primary recommendation and alternatives
- Include weather and wind explanation
- Show duration and distance context from historical rides
- Add confidence or trust framing
- Prepare structure for workout-aware route extension

### Acceptance criteria
- Morning and evening commute flows render from structured data
- Primary recommendation is clear and visually distinct
- At least one alternative route can be shown when available
- Explanation model is understandable and concise
- Route taxonomy avoids overstating “new route” capability

### Dependencies
Depends on service interfaces and structured snapshot data.

---

## Issue 6: Build Long Ride Planner Flow

**Suggested title:** Build long ride planner with ride-intent presets and ranked route suggestions

**Suggested squad:** Squad C  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
The planner is a core product pillar in the approved proposal and should not be left as a later add-on.

### Scope
- Build planner input form
- Support distance, duration, surface, and ride intent controls
- Return ranked route suggestions with rationale
- Link suggestions back to similar historical rides
- Use weather context when available

### Acceptance criteria
- Planner accepts and validates core inputs
- Results show ranked route suggestions with meaningful rationale
- Historical ride references appear where relevant
- Planner does not require TrainerRoad data to function
- UI works on mobile and desktop

### Dependencies
Needs app shell, service layer, and route summary persistence.

---

## Issue 7: Build Route Library and Route Detail Experience

**Suggested title:** Build route library browsing, filtering, and route detail pages

**Suggested squad:** Squad C  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
The approved route library replaces many legacy report interactions and is where route history should live in the new platform.

### Scope
- Build route library index
- Filter by route type, distance, date range, and surface
- Build route detail page with map, usage history, and ride metadata
- Present route taxonomy clearly: historical, variant, exploratory where applicable

### Acceptance criteria
- User can browse and filter route library content
- Route detail pages provide clear historical context
- Route taxonomy is visible and not misleading
- Legacy report-only modal interactions are not required to access route history
- Route views degrade gracefully if some metadata is stale

### Dependencies
Needs route summaries and route-library service access.

---

## Issue 8: Build Settings and Preferences Workflow

**Suggested title:** Implement settings and preferences page for home/work locations, units, time windows, and planner defaults

**Suggested squad:** Squad A or Squad B  
**Suggested priority:** P2  
**Suggested release:** v1.0.0

### Why this issue exists
The proposal treats settings as a first-class product area, and this work is needed before the platform feels complete for daily personal use.

### Scope
- Build settings page
- Support home/work confirmation or override
- Support units and commute time windows
- Support long ride thresholds and planner defaults
- Persist settings in SQLite
- Integrate geocoding where needed for address/location changes

### Acceptance criteria
- Settings can be saved and reloaded
- Preferences affect downstream views or are clearly wired for use
- Geocoding failures are surfaced gracefully
- User can operate the product without editing config files directly

### Dependencies
Needs persistence layer and geocoding integration support.

---

## Issue 9: Implement Job Scheduler, Freshness, and Degraded Mode

**Suggested title:** Add scheduled jobs, stage-level status visibility, freshness windows, and last-known-good fallback behavior

**Suggested squad:** Squad D  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
Reliability is a product requirement, not an afterthought. This is especially important on Raspberry Pi.

### Scope
- Add scheduled refresh execution
- Record stage-level job history and outcome
- Expose freshness windows and stale-data indicators
- Support last-known-good snapshot serving
- Define degraded mode behavior when weather, geocoding, or TrainerRoad data is unavailable
- Bound logs/cache growth

### Acceptance criteria
- Scheduled runs update state automatically
- UI can show freshness and failure status
- Failed upstream integrations do not make the product unusable
- Last-known-good data remains available where appropriate
- Operational behavior is documented and testable

### Dependencies
Needs persistence layer and service orchestration hooks.

---

## Issue 10: Add Weather Snapshot Integration for Dashboard, Commute, and Planner

**Suggested title:** Integrate weather snapshots into dashboard, commute recommendations, and planner ranking

**Suggested squad:** Squad B with Squad D support  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
Existing weather work is currently framed as endpoint or commute-tab work. The new product needs weather to be embedded into decision views.

### Scope
- Normalize weather data into reusable snapshot/state model
- Feed weather context into dashboard recommendation summaries
- Feed weather and wind reasoning into commute views
- Feed weather-aware ranking into planner results
- Surface stale or missing weather clearly

### Acceptance criteria
- Weather context influences all appropriate recommendation surfaces
- Missing weather data yields degraded but functional views
- Weather explanation is understandable to an everyday rider
- Snapshot timestamps are visible where useful

### Dependencies
Needs service layer, persistence support, and job freshness behavior.

---

## Issue 11: Add TrainerRoad ICS Ingestion and Workout Normalization

**Suggested title:** Implement optional TrainerRoad ICS ingestion and normalize workouts into planning constraints

**Suggested squad:** Squad E  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
TrainerRoad integration is a key differentiator for this project and was explicitly approved for v1, but it must remain optional and non-blocking.

### Scope
- Ingest TrainerRoad ICS feed
- Parse scheduled workouts and relevant timing/length metadata
- Normalize workouts into internal planning constraints rather than passing calendar semantics around the system
- Store workout metadata and freshness in SQLite
- Handle stale, missing, or invalid feed data safely

### Acceptance criteria
- TrainerRoad feed can be configured and ingested successfully
- Imported workouts are available as normalized planning constraints
- Failed ingestion does not break normal commute or planner functionality
- Workout freshness and status are visible for debugging and UX messaging

### Dependencies
Needs persistence layer and reliability/status hooks.

---

## Issue 12: Implement Workout-Aware Commute Extension

**Suggested title:** Implement workout-aware commute recommendations that can extend route length to satisfy prescribed sessions

**Suggested squad:** Squad E with Squad B support  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
This is one of the most distinctive approved features and directly addresses the user’s cycling workflow.

### Scope
- Use normalized workout constraints from TrainerRoad ingestion
- Adjust commute recommendations when a scheduled workout should be completed outdoors
- Support longer route recommendations or route extensions where practical
- Explain workout fit and tradeoffs in the UI
- Respect user preference on whether indoor fallback is acceptable

### Acceptance criteria
- Commute views can reflect workout-aware logic when workout data is available
- Base commute recommendations still work when workout data is unavailable
- Recommendation explanation clearly distinguishes normal commute vs workout-extended commute
- Output is honest when no suitable outdoor match exists

### Dependencies
Depends on TrainerRoad ingestion, commute recommendation flow, and settings/preferences support.

---

## Issue 13: Build Repeat-a-Past-Ride and Saved Plan Flows

**Suggested title:** Add repeat-a-past-ride flow and saved plan support

**Suggested squad:** Squad C  
**Suggested priority:** P2  
**Suggested release:** v1.0.0

### Why this issue exists
The approved proposal treats these as high-value repeat-use features that increase stickiness without needing a heavier platform.

### Scope
- Let user start from a known historical ride
- Adapt recommendation to current conditions where possible
- Save selected plans or route choices
- Retrieve saved plans later from the web UI

### Acceptance criteria
- User can start planning from a historical ride
- Saved plans persist in SQLite
- Plan retrieval is straightforward from planner or route-library views
- Feature works without overcomplicating the core v1 UI

### Dependencies
Needs planner, route library, and persistence support.

---

## Issue 14: Add Mobile-First Layout and Shared UI Shell

**Suggested title:** Implement responsive layout, shared navigation shell, and small-screen-friendly decision views

**Suggested squad:** Squad B  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
The product is likely to be used on a phone before a ride or before leaving work. Mobile usability is core, not polish.

### Scope
- Build shared responsive layout shell
- Define primary navigation for dashboard, commute, planner, route library, and settings
- Make recommendation cards, forms, and route summaries usable on small screens
- Replace legacy tab-centric navigation patterns

### Acceptance criteria
- Primary workflows are comfortably usable on phone-sized screens
- Navigation is simple and route-based rather than tab-heavy
- Dashboard and commute surfaces remain readable without desktop-only assumptions
- No dependency on legacy report tab interactions

### Dependencies
Can start early with app shell, but should coordinate with page owners.

---

## Issue 15: Add Integration Test Coverage for Core Platform Workflows

**Suggested title:** Create integration test suite for dashboard, commute, planner, route library, TrainerRoad fallback, and degraded-mode workflows

**Suggested squad:** Squad E  
**Suggested priority:** P1  
**Suggested release:** v1.0.0

### Why this issue exists
Existing issue [#100](https://github.com/e2kd7n/ride-optimizer/issues/100) is valid in spirit, but needs to be retargeted to the approved web platform.

### Scope
- Add integration tests for dashboard rendering from snapshots
- Add tests for commute recommendation workflows
- Add tests for planner submission and results rendering
- Add tests for route library access
- Add tests for missing weather, stale data, and TrainerRoad failure cases
- Add tests for last-known-good fallback behavior where feasible

### Acceptance criteria
- Core workflows are covered by automated integration tests
- Reliability edge cases are covered, not just happy paths
- Tests run locally and fit the project’s lightweight stack
- Test data supports predictable CI execution

### Dependencies
Should begin after enough foundational routes and services exist, but test scaffolding can start early.

---

## Initial Parallel Execution Order

### Start Immediately
- Issue 1: Flask app shell and route blueprints
- Issue 2: shared service layer extraction
- Issue 3: SQLite schema and persistence boundaries
- Issue 14: mobile-first shared UI shell

### Start As Soon As Foundations Exist
- Issue 4: recommendation-first dashboard
- Issue 5: commute recommendation views
- Issue 6: long ride planner
- Issue 7: route library and route detail pages
- Issue 9: scheduler, freshness, and degraded mode
- Issue 10: weather snapshot integration

### Start After Core Flows Are Stable Enough
- Issue 8: settings and preferences
- Issue 11: TrainerRoad ingestion
- Issue 12: workout-aware commute extension
- Issue 13: repeat-a-past-ride and saved plans
- Issue 15: integration test suite

---

## Recommended Labeling Strategy

For the new issue set, add labels like:
- `web-platform`
- `v1.0.0`
- `backend`
- `frontend`
- `architecture`
- `reliability`
- `integration`
- `trainerroad`
- `mobile`
- `testing`
- squad labels such as `squad-platform`, `squad-commute`, `squad-planner`, `squad-ops`, `squad-qa`

For legacy report issues, add labels like:
- `legacy-prototype`
- `report-ui`
- `reference-only`

This preserves historical context without letting old issues distort the current release plan.

---

## Practical Notes for the Owner

- Keep the legacy issues open only if you still expect some maintenance on the report prototype.
- If not, mark them with a `legacy-prototype` label and optionally close them as superseded by the web-platform effort.
- Do not let the new platform backlog inherit old UI vocabulary like “tabs,” “uses modal,” or “report section spacing.”
- The most important early architectural constraint is still the same one identified by the engineering review: **do not let Flask routes become thin wrappers around `main.py`-style orchestration**.
- If using subagents, assign them by service/page boundary rather than by tiny UI tasks. That will reduce merge conflicts and produce cleaner ownership.