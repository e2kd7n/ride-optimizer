# Point-to-Point Distance/Time Tolerance Redesign

**Milestone:** v0.19.0
**GitHub Issue:** [#540](https://github.com/e2kd7n/ride-optimizer/issues/540)
**Status:** ✅ Implemented — see [static/js/explore.js](../../static/js/explore.js) (`generateRoute()`, `refineRoute()`, `plotRoadRoute()`) and [static/js/exploration-worker.js](../../static/js/exploration-worker.js) (`optimize()`)

## Problem

Explore's point-to-point mode treats the user's requested distance as a hard target with a tight ±15% tolerance (`TOLERANCE = 0.15` in `refineRoute()`, [static/js/explore.js:1142](../../static/js/explore.js#L1142)). That's correct for loop/out-and-back routes — there's no other distance signal to aim for — but wrong for point-to-point: origin and destination already impose a natural minimum route length. If they're 5 miles apart in a straight line and the rider asks for an 8-mile route, forcing the router to hit 8 miles ±15% adds unnecessary padding detours to close a 3-mile gap that should simply be ignored. The efficient direct route is a perfectly good answer.

The tolerance should only really matter when the requested distance is *wildly* longer than an efficient point-to-point route — e.g. 40 miles requested between two points 5 miles apart — at which point the existing frontier/infill tile-collection expansion should kick in to actively route out of the way and collect more tiles.

Today there is no "efficient route baseline" concept for point-to-point at all:
- `reachRadius = distanceKm / 3` in [static/js/exploration-worker.js:110](../../static/js/exploration-worker.js#L110) sizes the Phase-1 candidate search zone off the raw requested distance uniformly for point-to-point and loop routes alike.
- `refineRoute()`'s ±15% target in [static/js/explore.js:1184](../../static/js/explore.js#L1184) does the same for Phase-2 road routing.
- Nothing anywhere computes or compares against the origin→destination gap.

## Proposed design

### 1. Efficient-route baseline

Before Phase 1 candidate generation, make one `api.getExplorationRoute()` call ([static/js/explore.js:1166](../../static/js/explore.js#L1166)) with just `[start, end]` and no intermediate waypoints. The returned `distance_km` is `efficientKm` — the actual routed (not straight-line) point-to-point distance. This reuses the existing `/api/exploration/route` endpoint; no backend changes needed.

### 2. Wild threshold

`PTP_WILD_MULTIPLIER = 2.0` in `static/js/explore.js` — this tunable only affects client-side route-generation behavior (no backend logic reads it), so it's a plain JS constant rather than a `config/config.yaml` entry, matching the existing `COVERAGE_MAX_BBOX_DEGREES` precedent in the same file.

`targetKm > efficientKm * PTP_WILD_MULTIPLIER` → "wild" (expansion mode). Otherwise → "not wild" (accept the efficient route).

### 3. Behavior split (point-to-point only; loop/out-and-back unaffected)

- **Not wild:** skip `refineRoute()`'s "too short → add candidate/padding" branch entirely. Accept the efficiently-routed result as-is (it may still incidentally claim nearby tiles, but the router shouldn't detour to chase more). The "too long → drop a waypoint" branch stays as a safety net but shouldn't fire since no artificial waypoints were added in this regime.
- **Wild:** keep today's candidate-insertion / padding-displacement loop unchanged, so frontier/infill expansion continues to work for genuinely long point-to-point requests.

### 4. Threading the change

- **[static/js/explore.js](../../static/js/explore.js)** — `plotRoadRoute()` (~line 1275) already has access to `routeType` and `endMarker`. It computes `efficientKm` via the one-off ORS call before branching into `refineRoute()`, then passes a not-wild/wild flag (or an effectively-infinite tolerance) down so `refineRoute()` (~line 1141) can skip its expansion branches when not wild.
- **[static/js/exploration-worker.js](../../static/js/exploration-worker.js)** — Phase 1's `reachRadius` sizing (line 110) and frontier/infill scoring (~lines 302-341) need the same not-wild/wild split, so Phase 1 doesn't over-search for candidates that Phase 2 will discard anyway when the request isn't wild. The origin→destination baseline should be computed once in `explore.js` and passed into the worker's `postMessage` payload alongside `distanceKm`.

### Out of scope (noted, not fixed here)

While investigating, found that `plotRoadRoute()`'s `baseWaypoints` always closed the route back to `startPos`, even in point-to-point mode, instead of closing at `endMarker`. This was a separate pre-existing bug, fixed independently in "Fix point-to-point explore routes always closing back to start."

## Verification

No backend/API surface changes. Manual verification once implemented:
1. Set start/end ~5mi apart, request 8mi point-to-point → route should closely follow the efficient direct route, no forced padding.
2. Same start/end, request 40mi point-to-point → frontier/infill expansion should kick in as it does today.
3. Loop and out-and-back requests should be unaffected — confirm via existing manual Explore workflow.
