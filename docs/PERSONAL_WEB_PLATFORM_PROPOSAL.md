# Personal Web Platform Proposal: Ride Optimizer

**Date:** 2026-05-06
**Updated:** 2026-05-07 (Architecture Simplification & Version Rebaseline)
**Current Version:** v0.10.0 (formerly v2.5.0)
**Next Version:** v0.11.0 (Architecture Simplification)
**Future Version:** v1.0.0 (Production-Ready, when stable)
**Project:** Strava Commute Analyzer → Personal Ride Optimizer
**Deployment:** Raspberry Pi (Single-User, Home Network)

> **Note:** This proposal has been updated to reflect architecture simplification (Issue #152). Version 0.11.0 will use a lightweight "Smart Static" architecture optimized for single-user Raspberry Pi deployment, replacing the Flask-based approach from v0.6.0-v0.10.0. All releases use 0.x.x versioning until production-ready. See [`VERSIONING_PLAN.md`](VERSIONING_PLAN.md), [`VERSION_REBASELINE_PLAN.md`](../VERSION_REBASELINE_PLAN.md), and [`ARCHITECTURE_SIMPLIFICATION_PROPOSAL.md`](../ARCHITECTURE_SIMPLIFICATION_PROPOSAL.md) for details.

---

## Executive Summary

Ride Optimizer should evolve from a strong CLI analysis tool into a **personal cycling decision platform**: a browser-based system that helps one rider make better daily commute and ride-planning decisions from any device on the home network.

The goal is not merely to "put the CLI behind Flask." The goal is to create a system that is:

- **Useful every day** for commute decisions
- **Compelling on weekends** for long ride planning
- **Trustworthy** because recommendations are fresh, explainable, and resilient
- **Maintainable** as a solo project running on a Raspberry Pi
- **Ambitious enough** to feel like a real product rather than a thin wrapper around existing reports

### Product Thesis

The platform should answer three high-value questions quickly:

1. **What is the best commute route in the next 24 hours?**
2. **What ride should I do today given weather, timing, distance, surface preferences, and workout intent?**
3. **How should today's commute adapt if a scheduled TrainerRoad workout requires extra ride time or distance?**

> **Implementation note:** The engineering team’s consolidated recommendation is documented in [`consolidated_implementation_plan.md`](docs/reviews/personal-web-platform/consolidated_implementation_plan.md). Where this proposal leaves room for interpretation, the consolidated plan defines the recommended delivery boundaries and sequencing.

### Vision

"Optimize your cycling experience with intelligent commute recommendations and personalized ride planning, accessible from any device at home."

### Why This Product Direction Makes Sense

The current project already has strong foundations:

- Route grouping and similarity logic
- Weather-aware analysis
- Historical ride data
- Interactive visual output
- Raspberry Pi deployment experience
- A modular Python codebase with clear business-logic boundaries

That makes a single-user web platform a realistic next step. The best version of v1 keeps the scope ambitious, but structures it around reusable services, hybrid persistence, and features a cyclist would actually return to.

---

## Product Principles

The revised web platform should follow these principles from day one:

1. **Single-user first**  
   Optimize for one rider, one household, one trusted deployment environment.

2. **Reuse the existing analysis core**  
   Existing modules remain the source of truth for route analysis, weather scoring, and historical ride intelligence.

3. **Extract shared services before overbuilding the web layer**  
   The web app, scheduler, and any future CLI workflows should reuse the same orchestration and service interfaces.

4. **Hybrid persistence over unnecessary rewrites**  
   Use SQLite where it improves UX and operational clarity. Keep existing file caches where they remain efficient and stable.

5. **Explain recommendations, don’t just rank them**  
   A cyclist should be able to see _why_ a route is recommended: wind, duration, confidence, elevation, surface, and historical fit.

6. **Optimize for phone-in-hand usage**  
   The app should work well when checked in the kitchen before work or from a phone while deciding on a weekend ride.

7. **Fail gracefully when external data is stale**  
   If Strava sync or weather refresh fails, the platform should remain usable with clear timestamps and degraded-mode behavior.

8. **Ship practical cycling value before novelty**  
   The product should first become indispensable for real ride decisions, then expand into richer planning features.

---

## Core Product Vision

### Primary Use Cases

#### 1. Daily Commute Intelligence
**Show the best commute to or from work in the next 24 hours.**

The platform should combine:
- Weather and wind impact
- Historical route performance
- Time-of-day patterns
- Recent data freshness
- Confidence based on past route usage
- Optional workout-aware commute extension when a scheduled TrainerRoad session should be accommodated outdoors

#### 2. Long Ride Planning
**Recommend strong ride options for today or a future start time.**

The planner should support:
- Origin and start time
- Distance and/or duration targets
- Surface preferences
- Elevation or climbing bias
- Ride intent presets
- Weather-aware route suitability
- Workout-aware constraints derived from imported TrainerRoad calendar events

#### 3. Historical Ride Reuse
**Help revisit proven rides with better context.**

The platform should make it easy to:
- Browse route families
- Reopen a favorite past ride
- Compare similar rides
- Ask for the best “ride like this again” option under current conditions

### Core Value Propositions

#### 1. Optimal Commute Intelligence
- Real-time weather and wind-aware route recommendations
- Historical commute performance
- Alternative route comparison
- Automated overnight refresh for morning usage
- Clear rationale and confidence score
- Workout-aware commute extensions driven by TrainerRoad calendar data when enabled

#### 2. Personal Long Ride Planning
- Form-based ride planning from laptop or phone
- Route suggestions based on your own history
- Variants of known routes and exploratory suggestions near known ride patterns
- Road surface and climbing preference filters
- Weather suitability and risk flags
- Ability to repeat or adapt successful past rides
- Workout-aware commute extensions driven by TrainerRoad calendar data when a scheduled workout needs more ride time than a normal commute provides

> **Scope clarification:** Per the consolidated review in [`consolidated_implementation_plan.md`](docs/reviews/personal-web-platform/consolidated_implementation_plan.md), v1 should distinguish between proven historical rides, known-route variants, and exploratory suggestions. True novel route generation is not a guaranteed core v1 capability.

#### 3. Trustworthy Personal Platform
- Single-user, privacy-first architecture
- No external sharing or social complexity
- Local-network-first deployment
- Clear system status and freshness indicators
- Low-ops design suitable for a Raspberry Pi

---

## Version 1.0 Scope

Version 1.0 should be ambitious, but internally structured so implementation risk stays manageable.

### v1 Core User Experience

These capabilities define the main product promise and should be treated as primary v1 deliverables:

1. **Web Dashboard**
   - Current best commute recommendation
   - Workout fit summary when TrainerRoad data is available
   - Best departure window guidance when relevant
   - Last successful analysis timestamp
   - Last Strava sync timestamp
   - Next scheduled analysis time
   - Shortcuts to key flows

2. **Commute Recommendations**
   - Morning and evening commute views
   - Recommended route with explanation
   - Alternative routes
   - Weather and wind impact
   - Historical duration and distance context
   - Recommendation confidence indicator
   - Optional workout accommodation guidance when a TrainerRoad workout is scheduled

3. **Long Ride Planner**
   - Planning form with start point, time, distance, duration, and surface controls
   - Ride intent presets
   - Weather-aware results
   - Ranked route suggestions with rationale
   - Link back to similar historical rides
   - Optional TrainerRoad workout import to set minimum duration or distance targets

4. **Route Library**
   - Browse all route groups and notable rides
   - Filter by route type, distance, date range, and surface
   - View route details, history, and map

5. **Settings and Preferences**
   - Home/work confirmation or override
   - Units
   - Commute time windows
   - Long ride thresholds
   - Planner preference defaults

6. **Manual and Scheduled Analysis**
   - Run analysis on demand
   - Daily scheduled refresh
   - Job history and result status
   - Partial rerun capability for failed stages where practical

7. **Mobile-Friendly Experience**
   - Responsive layout
   - Phone-usable primary actions
   - Map and recommendation views designed for small screens

### v1 Extended Features

These are still appropriate for v1 if time allows and implementation remains stable:

- **GPX export** for route details or selected recommendations
- **Saved ride plans** for future reference
- **Departure window suggestions** when weather changes materially over the next few hours
- **Weather risk flags** such as gusts, precipitation timing, heat, or cold warnings
- **Repeat a past ride** workflow to adapt a known ride to today’s conditions
- **Route confidence score** based on history depth, weather certainty, and similarity quality
- **TrainerRoad ICS integration** to import scheduled workouts and convert them into route-length or ride-time constraints
- **Workout-aware commute route extension** so the recommended commute can be long enough to complete the prescribed session outdoors

> **Sequencing note:** The consolidated plan in [`consolidated_implementation_plan.md`](docs/reviews/personal-web-platform/consolidated_implementation_plan.md) recommends including TrainerRoad support in v1, but sequencing it after the base commute and recommendation flows are stable.

### Explicitly Not in v1

These are valuable, but should not distort v1 architecture or delivery:

- Multi-user support
- Public/community route sharing
- Subscription or monetization systems
- Native mobile apps
- Fully offline-capable PWA
- ML-based predictive training recommendations
- Broad remote-access productization

---

## Key User Flows

### 1. Dashboard Flow

The dashboard should function as a decision hub rather than a generic homepage.

**Quick Stats**
- Last analysis timestamp
- Last successful Strava sync
- Current best commute route
- Next scheduled refresh
- Weather freshness
- Outstanding warning or stale-data badge if present

**Action Cards**
- "View Today’s Commute Recommendation"
- "Plan a Ride"
- "Browse Route Library"
- "Repeat a Past Ride"
- "Run Analysis Now"

### 2. Commute Recommendation Flow

**Daily Automated Analysis**
- Fetch latest Strava activities
- Refresh route grouping inputs
- Update weather forecast
- Generate next-24-hour commute recommendations
- Apply workout-aware commute logic when a TrainerRoad calendar event is present
- Store recommendation snapshot and job result

**Commute View**
- **Morning Commute**
  - recommended route
  - recommendation rationale
  - confidence score
  - weather conditions and wind impact
  - estimated time and distance
  - alternatives
  - workout accommodation summary if applicable
- **Evening Commute**
  - same structure as morning
  - updated conditions where needed

**Interactive Details**
- Route map
- Elevation profile
- Historical performance
- Notes on tradeoffs:
  - faster
  - less windy
  - more consistent
  - lower stress
  - better in rain
  - long enough to complete today’s scheduled workout outdoors

### 3. Long Ride Planner Flow

**Planning Inputs**
- Origin point:
  - Home
  - Work
  - Custom location
- Start date and time
- Target distance
- Target duration
- Surface preference:
  - road
  - gravel
  - mixed
- Climbing preference:
  - flatter
  - balanced
  - hillier
- Ride intent preset:
  - fastest
  - lowest stress
  - endurance
  - gravel bias
  - hill session

**Planner Output**
- Top route recommendations ranked by fit
- Distance and estimated duration
- Elevation gain
- Surface breakdown
- Weather forecast
- Weather risk flags
- Similar past rides
- Workout fit summary if a TrainerRoad session was imported
- Confidence and explanation:
  - why this route scored well
  - what tradeoffs exist
  - whether a different departure time might be better
  - whether the route is long enough to satisfy the planned workout

### 4. Repeat a Past Ride Flow

This is a high-value cyclist feature that keeps the platform feeling personal.

**User Flow**
1. Choose a historical ride or route group
2. Select “Ride like this again”
3. Adjust start time, distance tolerance, and intent
4. View best current match based on:
   - weather
   - expected duration
   - surface compatibility
   - current recommendation score

### 5. Route Library Flow

**Browse and Filter**
- Commute routes
- Long ride route groups
- Notable individual rides
- Loop vs point-to-point
- Distance range
- Date range
- Surface type
- Ride intent match where available

**Route Details**
- Interactive map
- Historical use count
- Average time and distance
- Elevation profile
- Weather history summary
- Similar rides
- Optional GPX export
- "Ride like this again" action

---

## Cyclist-Centric Features Worth Including

These features add meaningful value without turning the project into a social platform.

### TrainerRoad Workout-Aware Commute Planning
The platform should optionally read a TrainerRoad ICS calendar feed and use upcoming workouts as route-planning inputs.

This enables commute recommendations that answer a more specific question:
- "Which commute route lets me complete today's prescribed workout outdoors?"

Useful behaviors include:
- import the next relevant TrainerRoad workout from an ICS feed
- infer minimum ride time and/or distance targets from the scheduled workout
- prefer commute variants or route extensions long enough to complete the workout
- indicate when a normal commute is too short and an extended route is required
- show whether the workout fit is exact, approximate, or not realistically supported by available routes
- allow the feature to remain optional so normal commute recommendations still work without TrainerRoad data

### Ride Intent Presets
The system should support intent-based ranking, not just generic route ordering.

Examples:
- **Fastest commute**
- **Lowest-stress commute**
- **Endurance day**
- **Gravel bias**
- **Hill session**
- **Weather avoidance**

### Departure Window Suggestions
If conditions improve significantly within a practical time window, the app should say so.

Examples:
- "Leaving 45 minutes later reduces headwind by 8 mph."
- "Rain risk drops after 6:30 PM."
- "Best departure window for this route: 8:00-8:45 AM."

### Confidence and Explainability
Recommendations should include:
- history depth
- route similarity confidence
- forecast confidence or freshness
- known variability in ride duration

### Weather Risk Flags
Useful flags include:
- strong gusts
- crosswind exposure
- precipitation risk during planned ride window
- extreme heat/cold
- rapid weather change likelihood

### Surface and Climbing Fit
Long ride planning should consider:
- paved-only preference
- gravel-friendly preference
- flatter route preference
- higher climbing preference

---

## Architecture

### Technical Direction

A small integration layer should be added for optional calendar-driven workout inputs, including TrainerRoad ICS ingestion.

The architecture should favor maintainability and reuse over a hard reset.

**Backend**
- **Flask** for the web application and lightweight JSON endpoints
- **Python 3.8+** for compatibility with the current codebase
- **Shared service layer** extracted from existing CLI orchestration
- **Calendar/workout integration service** for optional TrainerRoad ICS ingestion
- **SQLite** for lightweight web app state and history

**Frontend**
- **Bootstrap 5** for responsive UI
- **Vanilla JavaScript** for interactive controls without frontend framework overhead
- **Folium/Leaflet** for maps and route display

**Persistence**
- **SQLite** for:
  - recommendation snapshots
  - planner sessions
  - job history
  - user preferences
  - route metadata needed for web UX
  - imported workout metadata and commute workout-fit summaries
- **Existing file caches** for:
  - raw fetched activities
  - heavy cached analysis artifacts
  - weather or geocoding caches already working well

**Infrastructure**
- **Raspberry Pi 4** (2GB+ RAM recommended)
- **Podman container** as the primary deployment model
- **Systemd** for timers or host-managed scheduling where needed
- **Local network first**
- Optional future remote access via VPN/Tailscale/Tunnel approaches

### High-Level Design

```text
┌────────────────────────────────────────────────────────────┐
│                         Home Network                       │
│                                                            │
│  ┌──────────────┐        ┌──────────────────────────────┐  │
│  │ Laptop/Phone │───────▶│ Raspberry Pi                │  │
│  │ Browser      │  HTTP  │                              │  │
│  └──────────────┘        │  ┌────────────────────────┐  │  │
│                          │  │ Flask Web App          │  │  │
│                          │  └────────────┬───────────┘  │  │
│                          │               │              │  │
│                          │  ┌────────────▼───────────┐  │  │
│                          │  │ Shared Services Layer  │  │  │
│                          │  │ (web + scheduler + CLI)│  │  │
│                          │  └────────────┬───────────┘  │  │
│                          │               │              │  │
│                          │  ┌────────────▼───────────┐  │  │
│                          │  │ Existing Analysis Core │  │  │
│                          │  └───────┬────────┬───────┘  │  │
│                          │          │        │          │  │
│                          │  ┌───────▼───┐ ┌──▼────────┐ │  │
│                          │  │ SQLite    │ │ File Cache│ │  │
│                          │  └───────────┘ └────┬──────┘ │  │
│                          │                     │        │  │
│                          │             ┌───────▼──────┐ │  │
│                          │             │ Strava/Weather│─┼──┼─▶ Internet
│                          │             └──────────────┘ │  │
│                          └──────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Architectural Priorities

1. **Extract shared orchestration from the CLI path**
2. **Keep analysis algorithms largely intact**
3. **Avoid rewriting stable caches without measured benefit**
4. **Let the scheduler and web layer call the same services**
5. **Keep deployment simple enough for one person to operate**

---

## Application Structure

A practical first-pass structure could look like this:

```text
ride-optimizer/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── routes/
│   │   ├── dashboard.py         # Dashboard pages
│   │   ├── commute.py           # Commute recommendations
│   │   ├── planner.py           # Long ride planner
│   │   ├── route_library.py     # Route browsing/details
│   │   ├── settings.py          # Preferences and status
│   │   └── api.py               # Lightweight JSON endpoints
│   ├── templates/
│   ├── static/
│   └── db/
│       ├── models.py
│       └── repository.py
├── services/
│   ├── analysis_service.py      # Shared orchestration
│   ├── commute_service.py       # Commute recommendation logic
│   ├── planner_service.py       # Long ride planning logic
│   ├── route_library_service.py # Route/history retrieval
│   ├── trainerroad_service.py   # ICS import and workout parsing
│   ├── scheduler_service.py     # Scheduled job execution
│   └── status_service.py        # Health/freshness/status
├── src/                         # Existing analysis modules
├── cache/                       # Existing file caches
├── config/
│   ├── config.yaml
│   └── flask_config.py
├── migrations/
├── tests/
└── wsgi.py
```

This structure is intentionally service-oriented so [`main.py`](main.py), Flask routes, and scheduled jobs do not drift into separate logic paths.

---

## Persistence Strategy

### Why Hybrid Persistence Is the Right Fit

A full database migration would add complexity before it adds value. The current codebase already benefits from file caching, and that should be preserved where it is efficient.

### SQLite Responsibilities
SQLite should be introduced for state that benefits from structured querying and web UX:

- recommendation snapshots
- scheduled job history
- planner sessions
- imported workout metadata
- commute workout-fit summaries
- saved plans
- route metadata summaries
- user preferences
- status and error records

> **Data ownership note:** The consolidated review in [`consolidated_implementation_plan.md`](docs/reviews/personal-web-platform/consolidated_implementation_plan.md) recommends SQLite for web-facing state and summaries, while heavy fetched and derived analysis artifacts remain file-cache-backed unless a stronger reason to migrate them emerges.

### File Cache Responsibilities
Existing file caches should remain the primary storage for:

- fetched activity cache
- geocoding cache
- route similarity cache
- heavier derived artifacts that already work well as files

### Migration Principle
Only move data into SQLite when it meaningfully improves:
- UI responsiveness
- operational visibility
- reliability
- search/filtering
- saved-state behavior

---

## Privacy & Security

### Privacy-First Principles

1. **Local-first deployment**  
   The platform is designed for home-network use.

2. **Single-user by default**  
   No multi-tenant complexity, sharing model, or public discovery layer.

3. **Data control**  
   Data export and deletion should remain straightforward.

4. **Encrypted credential storage**  
   Strava tokens should remain encrypted and inaccessible to browser clients.

5. **No telemetry or data resale**  
   This is a personal platform, not an analytics business.

### Security Position for v1

For a trusted home deployment, mandatory user authentication can remain optional. However, the platform should still follow sound defaults:

- secure token handling
- CSRF protection where forms exist
- session security defaults
- firewall rules to block external exposure
- clear path to optional lightweight auth later if needed

### Future Remote Access

If remote access is desired later, preferred options are:
- VPN
- Tailscale
- Cloudflare Tunnel

Direct public exposure should not be the default path.

---

## Reliability, Resilience, and Operations

A personal platform only becomes useful if it is dependable on ordinary days and understandable on broken ones.

### Operational Requirements

The web app should visibly report:

- last successful Strava sync
- last successful weather refresh
- last successful recommendation run
- next scheduled analysis time
- stale data status
- partial failure status

### Degraded Mode Behavior

If one dependency fails:

- the system should continue serving the last known good recommendations where possible
- stale timestamps should be obvious
- the failed stage should be identifiable
- manual rerun should be available

### Maintenance Requirements

Include support for:
- log rotation
- cache cleanup
- disk-space monitoring
- SQLite backup/export
- config backup/export
- visible job history for troubleshooting

### Why This Matters

A cyclist checking the app before a ride needs to know:
- whether data is fresh
- whether the recommendation is trustworthy
- whether the platform is healthy enough to rely on right now

---

## Performance and Raspberry Pi Constraints

### Resource Management

**Memory**
- Keep the web app lightweight
- Limit worker count appropriately for single-user deployment
- Avoid unnecessary in-memory duplication of route geometry

**CPU**
- Schedule heavier analysis off-hours where practical
- Keep manual refresh available with clear progress/status
- Prefer reuse of cached artifacts over repeated full recalculation

**Storage**
- Rotate logs
- Clean old transient records
- Keep caches bounded and understandable

**Network**
- Local hosting improves latency and removes cloud infrastructure complexity

### Performance Targets

- Dashboard load: **<2 seconds**
- Primary page transitions: **<2 seconds**
- Map rendering: **<3 seconds**
- API/status endpoints: **<500ms**
- Full analysis refresh: **<5 minutes** target on Raspberry Pi
- Mobile UI remains usable under normal home Wi-Fi conditions

---

## Database Model (Initial SQLite Scope)

SQLite should start with focused tables that help the web platform without forcing all raw data into a relational model.

```sql
-- Recommendation snapshots
recommendation_snapshots (
    id,
    created_at,
    recommendation_type,
    direction,
    recommended_route_id,
    confidence_score,
    weather_summary,
    rationale_json
)

-- Planner sessions / saved plans
planner_sessions (
    id,
    created_at,
    origin_type,
    origin_payload,
    target_distance,
    target_duration,
    surface_preference,
    climbing_preference,
    ride_intent,
    result_summary_json
)

-- Job history
job_runs (
    id,
    job_type,
    started_at,
    completed_at,
    status,
    stage,
    error_message,
    summary_json
)

-- Route metadata for web browsing
route_summaries (
    id,
    route_group_id,
    route_type,
    avg_distance,
    avg_duration,
    avg_elevation_gain,
    surface_summary,
    use_count,
    last_used_at
)

-- Preferences
settings (
    key,
    value
)
```

This schema can grow later, but it is sufficient to support the first web release.

---

## API and Web Endpoints

A lightweight endpoint surface is enough for v1.

```text
GET  /                       # Dashboard
GET  /commute                # Today's commute recommendations
GET  /commute/history        # Prior recommendation snapshots
GET  /planner                # Ride planning form
POST /planner/generate       # Generate ride recommendations
POST /planner/save           # Save a planner session or plan
GET  /routes                 # Route library
GET  /routes/<id>            # Route details
POST /routes/<id>/repeat     # Ride like this again
GET  /settings               # Preferences and system status
POST /settings               # Update preferences
POST /analysis/run           # Manual analysis trigger
POST /analysis/rerun-stage   # Rerun failed stage where supported
GET  /api/status             # JSON system/freshness status
GET  /api/weather            # Current forecast summary
GET  /api/jobs               # Job history
```

The system does not need a large public API surface in v1. It needs a good internal web contract.

---

## Implementation Plan (Version 1.0.0)

> **Target Release:** v1.0.0 - Q3 2026 (8-10 weeks from approval)  
> **Current Version:** v0.5.0 (CLI-based system)  
> **See also:** [`VERSIONING_PLAN.md`](docs/VERSIONING_PLAN.md) for complete versioning strategy

### Phase 1: Shared Services and Web Foundation (2-3 weeks)

**Goals**
- Extract shared orchestration from the current CLI path
- Build the Flask application skeleton
- Establish template/layout system
- Reuse existing report logic where possible

**Key Deliverables**
- service layer for shared workflows
- Flask app factory and route modules
- basic dashboard shell
- SQLite setup and initial migrations
- initial status and recommendation snapshot storage

### Phase 2: Core Product Flows (2-3 weeks)

**Goals**
- Implement the main user-facing product loops
- Build the minimum feature set that makes the platform useful every day

**Key Deliverables**
- dashboard
- commute recommendation views
- long ride planner
- route library
- settings/preferences page
- mobile-responsive UI

### Phase 3: Automation, Reliability, and Pi Validation (1-2 weeks)

**Goals**
- Make the platform dependable for day-to-day use
- Improve visibility into freshness and failures
- Validate performance on Raspberry Pi hardware

**Key Deliverables**
- scheduled job execution
- stage-level job history and status visibility
- stale-data badges
- degraded mode behavior
- last-known-good snapshot serving
- performance tuning and Pi deployment validation

### Phase 4: Workout and Extended Decision Features (1-2 weeks)

**Goals**
- Add features that increase repeat usage and delight without destabilizing the product

**Key Deliverables**
- TrainerRoad ICS ingestion
- workout-aware commute extension
- saved plans
- repeat-a-past-ride flow
- departure window suggestions
- route confidence scores
- weather risk flags
- optional GPX export

> **Implementation note:** This sequencing reflects the team recommendation in [`consolidated_implementation_plan.md`](docs/reviews/personal-web-platform/consolidated_implementation_plan.md), which places workout-aware commute logic in v1 but after the base recommendation architecture is stable.

### Post-1.0 Roadmap

- **v1.1.0** - richer route insights, saved-plan improvements, export polish
- **v1.2.0** - PWA shell, notifications, offline-adjacent improvements
- **v1.3.0** - predictive insights and deeper planning intelligence
- **v2.0.0** - multi-user and broader deployment options if product direction changes

---

## Migration from the Current System

### What Stays the Same

- Existing route analysis algorithms
- Strava OAuth and credential model
- Route similarity logic
- Weather integration
- Core visualization capabilities
- Podman-based deployment approach
- File-based caching where already effective

### What Changes

- CLI-first interaction becomes web-first interaction
- Manual execution becomes scheduled plus on-demand
- Single generated report becomes multi-page product experience
- Orchestration becomes reusable services rather than CLI-only flow
- Persistence becomes hybrid rather than file-only

### Recommended Migration Strategy

1. Preserve the current analysis core
2. Extract shared orchestration into services
3. Build the web UI on top of those services
4. Introduce SQLite for web-facing state
5. Keep file caches where they already perform well
6. Add scheduled jobs and operational visibility
7. Expand cyclist-facing features after core reliability is proven

---

## Success Metrics

### Product Success

- The dashboard is checked regularly from laptop and phone
- Commute recommendations feel timely, explainable, and useful
- Long ride planning produces routes worth actually riding
- Route library and repeat-a-past-ride flows get recurring use
- The product feels like a cycling platform, not a report viewer

### Reliability Success

- Daily scheduled analysis completes successfully under normal conditions
- Failed refreshes are visible and recoverable
- Last-known-good recommendations remain available during partial outages
- Job history makes troubleshooting practical
- The platform runs stably on Raspberry Pi with minimal babysitting

### Performance Success

- Dashboard loads in under 2 seconds
- Core pages remain responsive on mobile
- Analysis completes in under 5 minutes on target hardware
- API/status endpoints remain lightweight
- Pi memory and temperature remain within reasonable operating bounds

### Quality Gates

- Existing tests continue to pass
- New web/service tests are added
- Critical flows are validated on Raspberry Pi
- Security-sensitive paths are reviewed
- Documentation is updated for deployment and maintenance

---

## Cost and Maintenance

### Hardware
- Raspberry Pi 4 (2GB+ RAM)
- SD card or SSD
- Power supply
- Home network connection

### Software
- Raspberry Pi OS
- Python 3.8+
- Flask
- SQLite
- Podman
- Existing Python dependencies

### Time Investment
- **Development:** 8-10 weeks part-time
- **Testing and Pi validation:** 1-2 weeks
- **Ongoing maintenance:** low, assuming automation, backups, and bounded scope

### Cost
- **Hardware:** likely already owned
- **Software:** open source
- **Cloud hosting:** none for local-only deployment
- **Operating cost:** minimal household power/network usage

---

## Comparison: Original Platform Vision vs Personal Web Platform

| Aspect | Original Proposal | Personal Web Platform |
|--------|------------------|-----------------------|
| **Users** | Multi-tenant community platform | Single-user personal platform |
| **Infrastructure** | Kubernetes on AWS/GCP | Raspberry Pi at home |
| **Database** | PostgreSQL + PostGIS | SQLite + existing caches |
| **Backend** | FastAPI + Celery | Flask + shared services |
| **Frontend** | Next.js + React | Bootstrap + Vanilla JS |
| **Primary Value** | Community route sharing | Personal decision support |
| **Authentication** | Multi-user OAuth + accounts | Strava OAuth, optional local auth later |
| **Monetization** | Subscription tiers | None |
| **Cost** | Large funded product build | Hobby-scale local deployment |
| **Timeline** | Team, multi-quarter roadmap | Solo, ambitious v1 |
| **Complexity** | High-scale product system | High-value single-user product |
| **Maintenance** | Ongoing team operations | Low-ops personal platform |

---

## Recommended Next Steps

### Immediate
1. Approve this revised product and implementation direction
2. Define the shared services boundary from the current CLI flow
3. Create Flask application skeleton
4. Add SQLite schema and migration scaffolding
5. Build dashboard and commute pages first

### Near Term
1. Implement planner and route library
2. Add scheduling and job history
3. Validate performance on Raspberry Pi
4. Add resilience and stale-data handling
5. Layer in cyclist-centric extended features

### After Launch
1. Observe actual usage patterns
2. Improve the features used most often
3. Keep maintenance burden low through automation
4. Expand only where the product proves it earns the complexity

---

## Version 1.0.0 Success Criteria

### Must-Have
- Web dashboard accessible from laptop and mobile
- Automated daily analysis
- Commute recommendations with explanation
- Long ride route planner
- Route library
- SQLite-backed web state
- Mobile-responsive design
- Raspberry Pi deployment
- Job/status visibility
- Settings/preferences support

### Strongly Desired
- Saved plans
- Repeat-a-past-ride flow
- Confidence indicators
- Weather risk flags
- Departure window suggestions
- GPX export

### Release Quality Gates
- Existing core tests passing
- New web/service tests added
- Security-sensitive flows reviewed
- Pi deployment validated
- Documentation updated
- Core user flows usable without command line access

---

**Prepared By:** Senior Development Team (Bob & Assistant)  
**Date:** 2026-05-06  
**Status:** Revised for Review and Implementation

**Related Documents:**
- [`VERSIONING_PLAN.md`](docs/VERSIONING_PLAN.md) - Version strategy and roadmap
- [`WEB_PLATFORM_PROPOSAL.md`](docs/archive/WEB_PLATFORM_PROPOSAL.md) - Original multi-user proposal (archived)
- [`TECHNICAL_SPEC.md`](docs/TECHNICAL_SPEC.md) - Current technical foundations
