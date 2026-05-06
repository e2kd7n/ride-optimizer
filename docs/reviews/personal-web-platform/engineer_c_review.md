# Engineer C Review: Operations, Reliability, and Raspberry Pi Delivery

**Reviewer Role:** Senior engineer focused on deployment, reliability, runtime behavior, observability, failure handling, and low-ops operation  
**Review Target:** [`docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md`](docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md)  
**Date:** 2026-05-06

---

## Executive Summary

I support the proposal, but only if reliability is treated as a product feature rather than implementation detail. For a personal platform running on a Raspberry Pi, the biggest failure mode is not “feature incomplete.” It is “I stopped trusting it because I do not know whether it is fresh, healthy, or still working.”

The proposal already points in the right direction:
- local-first deployment
- job history
- degraded mode
- stale-data awareness
- low-ops architecture
- lightweight stack

That said, I think the document still understates the amount of operational discipline needed once this becomes a web app with background jobs, periodic syncs, and optional calendar ingestion.

---

## What the Proposal Gets Right

### 1. Infrastructure Choices Are Sensible
For a single-user deployment:
- Flask is fine
- SQLite is fine
- Podman is fine
- Raspberry Pi is fine
- local network only is correct

There is no evidence that a more complex stack would improve outcomes here.

### 2. Reliability Is Explicitly Mentioned
This is good and uncommon. The proposal already recognizes:
- stale data needs to be visible
- failures should degrade gracefully
- job history matters
- last-known-good recommendations have value

That is exactly the right mindset.

### 3. Snapshot-Friendly Architecture Is a Good Fit
A Pi-hosted app should prefer precomputed state where possible. Request-time heavy computation should be minimized.

---

## Main Concerns

### 1. Scheduler Complexity Is Underspecified
Once the app has:
- Strava sync
- weather refresh
- route recommendation generation
- TrainerRoad ICS ingestion
- cache cleanup
- possibly rerun support

it is no longer “just a Flask app.” It is a small job orchestration system. The proposal should treat that more explicitly.

### 2. TrainerRoad ICS Ingestion Adds a Reliability Surface
ICS import seems simple, but in practice introduces:
- fetch failures
- parsing failures
- stale calendar data
- duplicate event handling
- timezone interpretation problems
- workout changes after the event was already cached

This is manageable, but it needs explicit ownership and visible status reporting.

### 3. The Proposal Does Not Yet Define Recovery Paths Well Enough
If:
- weather refresh fails but Strava sync succeeds
- ICS import fails but commute data is otherwise current
- recommendation generation fails after upstream data refresh succeeded

the system should define exactly what the UI shows and what the operator can retry.

### 4. Raspberry Pi Validation Needs to Be More Concrete
“Performance tuning and Pi validation” is not enough. The implementation plan should specify:
- target hardware assumptions
- expected job runtime envelope
- memory budget assumptions
- storage growth assumptions
- behavior under low disk or stale cache conditions

---

## Reliability Recommendations

## 1. Treat Status as Structured Data, Not Loose Messaging
The system should maintain a simple internal status model for each major dependency and job stage:
- last successful run
- last attempted run
- current status
- error summary
- stale threshold
- retry eligibility

This should drive both UI and operational debugging.

## 2. Break Background Work into Named Stages
Recommended stages:
1. activity sync
2. weather refresh
3. workout calendar sync
4. route grouping refresh
5. recommendation generation
6. snapshot persistence
7. cleanup tasks

If a failure occurs, the operator should know which stage failed and whether downstream outputs remain usable.

## 3. Define Freshness Windows
The product should explicitly define what “fresh” means for:
- Strava data
- weather data
- TrainerRoad calendar data
- recommendation snapshots

Without that, the stale-data UX will be inconsistent.

## 4. Make Degraded Mode Specific
A strong degraded mode policy would be:

- if weather fails, show last known recommendation with weather stale warning
- if TrainerRoad ICS fails, continue normal commute recommendation and flag workout fit as unavailable
- if recommendation generation fails, continue serving last successful recommendation snapshot
- if route analysis refresh fails, preserve current route library and mark analysis freshness as stale

That level of specificity helps implementation and testing.

---

## Operational Recommendations

### 1. Keep Manual Recovery Simple
The user should be able to:
- rerun all jobs
- rerun a failed stage if supported
- view last errors
- know whether a rerun is likely to change the result

### 2. Use Conservative Storage Strategy
I support hybrid persistence because:
- SQLite is excellent for small structured state
- file caches are fine for bulky derived artifacts
- migrating everything into SQLite would create unnecessary operational risk

### 3. Bound Log and Cache Growth
For a Pi deployment, log retention and cache retention should be designed up front. This should not be deferred.

### 4. Backups Must Be Simple
There should be a documented backup set:
- [`config/config.yaml`](config/config.yaml)
- credential storage
- SQLite database
- optionally selected caches if rebuild cost is high

---

## Test and Validation Recommendations

## 1. Reliability Tests Matter as Much as Feature Tests
There should be test coverage for:
- upstream dependency failures
- stale data behavior
- missing TrainerRoad feed
- malformed ICS data
- scheduler stage failure recovery
- snapshot fallback behavior

## 2. Pi Validation Should Use Realistic Workloads
At minimum:
- repeated dashboard loads
- manual analysis run
- scheduled overnight run
- TrainerRoad sync present and absent
- low-disk warning scenario
- cold start after reboot

## 3. Timezone Handling Must Be Tested
Because calendar ingestion is involved, timezone bugs are now product bugs. This needs explicit testing.

---

## Proposal Changes I Recommend

### Accept
- local-first deployment
- low-ops design goal
- degraded mode
- job history
- manual and scheduled runs
- TrainerRoad integration, provided failure handling remains optional and isolated

### Modify
- strengthen operational requirements around stage-level statuses
- define freshness windows
- specify degraded-mode behavior for each upstream data source
- add backup expectations
- make Pi validation more concrete

### Reject
I reject any implementation approach that:
- hides job-stage failures behind generic “analysis failed” messages
- blocks the whole product because TrainerRoad ingestion failed
- treats request-time heavy recomputation as normal behavior
- postpones operational visibility until after feature delivery

---

## Decisions Recommended for Owner Review

1. Do you want stage-level job visibility in v1, or is high-level job status sufficient?
2. Should TrainerRoad ICS ingestion be best-effort optional from day one, or can workout-aware recommendations block only when explicitly enabled?
3. Should manual rerun support include stage-specific reruns in v1, or only full-run reruns?
4. What hardware baseline should v1 officially target: Pi 4 with SD card, or Pi 4 with SSD-recommended?

My recommendations:
- stage-level status in v1
- TrainerRoad ingestion best-effort and non-blocking
- full rerun first, stage reruns only where easy and safe
- Pi 4 supported, SSD recommended if sustained history volume grows

---

## Final Verdict

The proposal is viable, but only if reliability is implemented as part of the product contract. This system will be trusted or ignored based on whether it communicates health, freshness, and failure state clearly.