# Engineer A Review: Architecture and Maintainability

**Reviewer Role:** Senior software engineer focused on architecture, maintainability, code organization, and long-term delivery risk  
**Review Target:** [`docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md`](docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md)  
**Date:** 2026-05-06

---

## Executive Summary

The proposal is strong in direction and product ambition, but it needs firmer implementation discipline to avoid creating a thin web layer on top of an increasingly tangled orchestration path. The biggest opportunity is to make the web platform the first consumer of a reusable services layer rather than the new center of gravity.

I support the proposal overall. I do **not** support implementing it as:
- Flask routes calling the existing CLI workflow directly
- multiple partially overlapping persistence mechanisms without boundaries
- feature work that outruns service extraction and operational visibility

The proposal should be implemented, but with service boundaries, responsibility boundaries, and explicit sequencing as first-class concerns.

---

## What the Proposal Gets Right

### 1. Correct Product Direction
The move from CLI reporting to a personal cycling decision platform is the right next step. The current codebase already has enough business value to justify a proper application shell.

### 2. Good Architectural Instincts
The proposal correctly identifies:
- shared services as a priority
- hybrid persistence as preferable to a full rewrite
- local-first deployment as the correct infrastructure assumption
- explainability as a product requirement rather than a nice-to-have

### 3. Realistic Hobby-Scale Delivery
The Raspberry Pi, Flask, SQLite, and Bootstrap choices are all sensible for the stated scope.

---

## Primary Concerns

### 1. Scope Is Ambitious in the Right Way, but the Architecture Must Lead
The proposal is trying to do several meaningful things in v1:
- commute intelligence
- long ride planning
- route library
- TrainerRoad-aware workout accommodation
- job orchestration
- mobile-friendly web UX

That is acceptable only if the service layer is treated as a blocking dependency, not a cleanup task to do later.

**Recommendation:** no feature implementation should bypass the shared services layer.

### 2. Persistence Boundaries Need Sharper Language
The proposal says hybrid persistence, which I support, but it still leaves too much room for accidental duplication between SQLite and file caches.

Current wording should become stricter:
- SQLite is for web-facing state and historical snapshots
- file caches are for fetched and compute-heavy analysis artifacts
- the same concept should not be authoritative in both places unless one is explicitly a derived cache

### 3. The Proposal Contains Editorial Duplications That Signal Scope Drift
There are repeated bullets and duplicated responsibilities in the current proposal, especially around:
- workout-aware commute route extension
- imported workout metadata / commute workout-fit summaries

These are documentation issues, but they also hint at implementation ambiguity. If the document repeats the same idea in multiple sections without distinction, the codebase may repeat it too.

### 4. “New Ride Routes” Remains Underdefined
The proposal mentions routes based on where people tend to ride near a start location. That is conceptually interesting, but technically different from:
- recommending historically proven personal routes
- recommending variants of known route groups
- generating genuinely novel rides

Those are not the same system. The proposal should not imply full new-route generation unless it is prepared to specify data sources, generation logic, and quality constraints.

---

## Architectural Recommendations

## 1. Define the Shared Services Layer Explicitly

The first engineering artifact should be service contracts, not Flask routes.

Recommended services:
- [`analysis_service.py`](services/analysis_service.py)
- [`commute_service.py`](services/commute_service.py)
- [`planner_service.py`](services/planner_service.py)
- [`route_library_service.py`](services/route_library_service.py)
- [`trainerroad_service.py`](services/trainerroad_service.py)
- [`status_service.py`](services/status_service.py)
- [`scheduler_service.py`](services/scheduler_service.py)

Each service should have:
- stable inputs
- stable outputs
- typed result objects or schema contracts
- explicit failure modes

## 2. Use a Snapshot-Oriented Web Model
The web application should not recompute everything in request handlers. Instead:
- background workflows create recommendation snapshots
- request handlers read snapshot and metadata state
- on-demand runs update state asynchronously or with visible progress

This approach matches Raspberry Pi constraints and keeps the UI fast.

## 3. Treat TrainerRoad Integration as an Input Adapter
TrainerRoad support should not leak throughout the system. It should enter through a dedicated adapter/service that translates ICS data into internal workout constraints.

Internal model should look more like:
- workout date/time
- minimum duration
- minimum distance if inferable
- workout type / intent
- confidence in constraint inference

The rest of the application should reason about workout constraints, not raw ICS events.

## 4. Keep Route Generation Claims Conservative
For v1, I recommend distinguishing:
- **historical route recommendation**
- **historical route extension**
- **variant suggestion**
from
- **novel route generation**

Only the first three are clearly supported by the current proposal and codebase foundations.

---

## Maintainability Risks

### 1. Route and Recommendation Logic Fragmentation
There is a risk of duplicating ranking logic between:
- commute recommendations
- long ride planner
- repeat-a-past-ride flow
- workout-aware commute extension

These should share a scoring framework with mode-specific weighting.

### 2. Document and Code Drift
The proposal is ambitious enough that the implementation plan should become the canonical source for sequencing and boundary decisions. Otherwise, the proposal may remain aspirational while implementation becomes opportunistic.

### 3. Data Ownership Ambiguity
Every persistent concept should answer:
- where is the source of truth?
- what is cached?
- what is snapshot history?
- what can be rebuilt?

Without that, SQLite and file caches will become a maintenance burden rather than a simplification.

---

## Specific Proposal Changes I Recommend

### Accept
- shared services layer
- hybrid persistence
- local-first deployment
- route library in v1
- TrainerRoad workout-aware commute logic
- job history and degraded mode

### Modify
- narrow claims around “entirely new ride routes”
- state that v1 prioritizes recommendation and extension over true route generation
- define SQLite/file-cache ownership more explicitly
- define workout ingestion as an adapter boundary
- clean duplicated bullets and repeated state responsibilities

### Reject
I reject any interpretation of the proposal that implies:
- Flask route handlers become orchestration logic
- SQLite immediately replaces all existing caches
- novel route generation is guaranteed in v1

---

## Implementation Sequence I Support

### Phase 1
- service extraction
- domain model definition
- SQLite state model
- status/job plumbing
- dashboard shell

### Phase 2
- commute recommendation flow
- recommendation snapshot model
- route library read views
- planner on top of shared ranking logic

### Phase 3
- TrainerRoad ingestion adapter
- workout-aware commute extension
- degraded mode and rerun controls
- Pi validation and profiling

### Phase 4
- saved plans
- richer planner explanation
- GPX export
- additional UX polish

---

## Decisions Recommended for Owner Review

These are implementation decisions that should be made explicitly:

1. Should v1 include true novel route generation, or only recommendation of known and extended routes?
2. Should TrainerRoad workout accommodation be part of the initial v1 acceptance criteria or late-v1 scope?
3. Should SQLite remain limited to web state and snapshots, or should more route-analysis outputs move into it during v1?
4. Should manual analysis runs be synchronous with progress reporting or queued background jobs from the outset?

---

## Final Verdict

I recommend proceeding, with one condition: the shared services layer must be treated as the backbone of the project, not a refactor deferred until after the web UI exists.

If that condition is met, the proposal is both ambitious and maintainable.