# Own Router: Architecture for Explore's Next Generation

**Status:** Proposed. Unscheduled; it's a multi-release epic.
**Scope:** Replace ORS-driven route construction on the Explore page with a planner that runs on our own copy of the street-and-path network.
**Written:** 2026-11-08, after the Explore routing overhaul (#627 → 90a6974 → 9ab942a).

---

## 1. Why

Explore today builds routes in two phases:

1. **Phase 1** ([static/js/exploration-worker.js](../../static/js/exploration-worker.js)) picks *stops* from unclaimed tiles. It uses straight-line geometry and knows nothing about roads.
2. **Phase 2** ([static/js/explore.js](../../static/js/explore.js) `refineRoute()`) asks OpenRouteService (ORS) to connect the stops, then patches the result through several stages: trim, nearby pickups, per-stop check, retrace fix and cluster sweep. Every stage is another ORS round trip.

That design has hit a ceiling we can measure. On the reference scenario (Edgewater start, Skokie/Lincolnwood box, 40 mi Loop, Fill gaps, squadratinhos), the deployed version produces:

| km | new tiles | tiles/km | turns | U-turns | cluster tiles left |
|---|---|---|---|---|---|
| 98.2 | 109 | 1.11 | 278 (2.83/km) | 27 | 11 (all unreachable) |

Three limits can't be fixed from inside the current design:

- **Turns are out of our hands.** ORS has no turn cost. It picks the fastest road between consecutive stops. Lawnmower sweeps, turn-aware stop reordering, and turn penalties on optional detours were all tried on real data, and none reduced turns on the routed result. (They are kept unmerged on branch `worktree-explore-fewer-turns`.) The router decides how a block is threaded, and we only decide where the stops go.
- **Paths and cut-throughs are invisible to the planner.** Neighbourhoods joined only by a footpath, like the dead-end streets along the Lake–Cook county line, are reachable only if ORS chooses to use the path. ORS's bike profile treats walking-only paths conservatively, and the planner can't tell which tiles a path would unlock.
- **Every decision costs a network call.** Each refinement stage is an ORS request: our own limit is 20 a minute, ORS's free tier allows 2,000 a day and 40 a minute, and Pi threads are scarce. The cluster rule (below) needs a verify-and-retry loop because we only learn which tiles a route crosses *after* ORS returns it.

A planner that holds the network itself can price turns directly, include rideable and walkable paths, and know the exact tiles of every candidate route *before* committing to it. That makes the cluster rule something the planner satisfies by construction, not something it patches in afterwards.

## 2. Requirements

### Hard
- **R1. The cluster rule.** A route must not leave an unclaimed tile that is edge-adjacent to it and part of a cluster of unclaimed tiles. Exempt are tiles at the boundary or horizon (outside the drawn area or the loaded coverage), water, or tiles with no reachable way. In practice: once a route touches a cluster, it sweeps the whole cluster. This overrides the distance target. (Stated by the rider 2026-11-08, implemented as `refineRoute` stage 5 and `ExploreRefine.clusterSweepTargets`.)
- **R2. Stay inside a drawn area,** exactly, when start and end are inside it.
- **R3. Legal routing.** Respect bicycle access, one-way rules for bikes (including `oneway:bicycle=no`) and access restrictions. Walking a bike is an explicit, priced, user-controllable mode, never silent.
- **R4. Runs on today's deployment.** A Raspberry Pi 4 (1.8 GB RAM) runs one gunicorn worker with 4 threads ([gunicorn.conf.py](../../gunicorn.conf.py)). The browser does the heavy planning, like Phase 1 does today. No new always-on server processes on the Pi.
- **R5. No hard dependency on flaky third parties at request time.** Overpass already fails from the Pi (the water saga, #598/#603/9ab942a). ORS may stay as a fallback, never a requirement.

### Goals (acceptance targets against the reference scenario)
- At least the current tile count (109) with **at least 30% fewer turns** and **at least 50% fewer U-turns**.
- Cluster tiles left: **0**, other than genuinely unreachable ones.
- Distance no worse than today for the same tiles. The target is to get back under the distance target where R1 allows.
- Plan time under 5 s in the browser on a mid-range phone for a 40 mi loop.

### Non-goals
- Turn-by-turn navigation and voice guidance. Riders export GPX.
- Routing outside the configured regions. ORS stays as the fallback there.
- Elevation-aware planning. It could be added later as an edge cost.

## 3. Overview

```
 ┌──────────── offline (CI / dev box, monthly) ────────────┐
 │ Geofabrik OSM extract (.osm.pbf)                         │
 │   → osmium tags-filter + bbox per region                 │
 │   → tools/router/build_graph.py                          │
 │       • bike-access model (R3)  • edge attributes        │
 │       • tile index per zoom (14, 17)                     │
 │       • roadless tiles = tiles with no usable way        │
 │   → region package: graph.bin + manifest.json            │
 └──────────────────────┬───────────────────────────────────┘
                        │ published as a GitHub release asset,
                        │ pulled onto the Pi's data volume
 ┌──────────── Pi (Flask) ┴─────────────────────────────────┐
 │ GET /api/router/regions          → manifest(s)           │
 │ GET /api/router/region/<id>.bin  → static file, ETag     │
 │ (coverage + visited tiles: unchanged)                    │
 └──────────────────────┬───────────────────────────────────┘
                        │ fetched once, HTTP-cached
 ┌──────────── browser ─┴───────────────────────────────────┐
 │ router-worker.js (Web Worker)                            │
 │   GraphStore  — typed arrays from graph.bin              │
 │   TurnAwarePath — A* on (node, incoming edge) states     │
 │   Planner     — select clusters → cover → connect →      │
 │                 improve → verify R1/R2 exactly           │
 │ explore.js    — UI, options, GPX export (unchanged UX)   │
 └──────────────────────────────────────────────────────────┘
```

The key decision is that **planning moves entirely into the browser, on a precompiled graph.** The Pi serves static files, so its CPU and threads stay free and nothing new runs on it. The browser already does Phase 1's heavy lifting in a Web Worker.

## 4. Components

### 4.1 Graph build pipeline (`tools/router/`)

**Input.** The Geofabrik Illinois extract (`.osm.pbf`). Regions are defined in `config/router_regions.yaml` as named bounding boxes, for example `chicago-north` covering the area the rider explores, plus a buffer.

**Steps.**
1. `osmium extract --bbox` per region, then `osmium tags-filter` keeping only `highway=*` ways plus the access-relevant tags.
2. **Bike-access model** (`access_model.py`), one table, unit-tested per tag combination:

   | OSM | Mode | Notes |
   |---|---|---|
   | `cycleway`, `path` with `bicycle` in {yes, designated} | ride | preferred |
   | `residential`, `living_street`, `unclassified`, `tertiary`, `service` (not `parking_aisle`/`driveway` unless needed) | ride | |
   | `secondary`, `primary` | ride | `busy` flag for an optional penalty |
   | `trunk`, `motorway` | excluded | unless `bicycle=yes` |
   | `footway`, `pedestrian`, `path` without bike permission, `bridleway` | **walk** | priced and toggleable (R3) |
   | `steps` | walk, heavy cost | off by default |
   | `access` or `bicycle` in {no, private} | excluded | |
   | `oneway=yes` | one direction | unless `oneway:bicycle=no` |

   Walk edges are what unlock the rider's Lake–Cook example (dead-end streets joined by a footpath).
3. **Topology.** Split ways at shared nodes into edges. Contract degree-2 chains *within* a single tile so each edge stays tile-accurate, and keep the full geometry for rendering and GPX.
4. **Per-edge attributes:** length (m), mode (ride/walk), class, `busy`, surface (paved/unpaved/unknown), oneway, compressed geometry, and **the tiles the edge crosses at z14 and z17**, computed with the same crossing math as [src/coverage_tracker.py](../../src/coverage_tracker.py) so claims match the backend exactly.
5. **Tile indexes:** tile → edges, at both zooms.
6. **Roadless tiles:** tiles crossed by no usable edge. This **replaces the Overpass water lookup** for Explore: "no way you can use" is the property routing actually needs. Water, rail yards and private campuses all fall out of it, with no Overpass dependency at request time.
7. **Serialization:** `graph.bin` holds little-endian typed-array sections in CSR layout (node coords as int32 microdegrees; edge from/to, length and flags; edge→tiles and tile→edges offsets; geometry deltas). `manifest.json` holds the region id, bbox, OSM timestamp, section offsets, sizes, a hash and the format version.

**Where it runs.** Never on the Pi (R4). The build runs on a dev box or a scheduled GitHub Action, and publishes the package as a release asset. The Pi pulls it onto the bind-mounted `data/` volume through a small cron job (pattern: [cron/](../../cron/)). Data packages ship separately from the container image, so a map refresh doesn't need a redeploy.

**Size budget.** To be measured in M0 (§7). The working hypothesis is that a dense ~30 × 30 km urban region is a few MB gzipped, light enough for one HTTP-cached download per device. If a region is too big, split it into fixed graph tiles (for example 0.1°) with boundary-node stitching, and have the browser load only the tiles the planning area touches.

**Licensing.** OSM data is ODbL. The map already credits OpenStreetMap. A derived database we distribute triggers ODbL share-alike for that database. The app is private today; this needs a decision before any public deployment.

### 4.2 Serving (`app/api/router_bp.py`)

- `GET /api/router/regions` returns the manifests of installed packages, so the UI knows where local routing is available.
- `GET /api/router/region/<id>.bin` returns the static file with `ETag`/`Cache-Control: immutable` (content-hashed names). Flask's `send_from_directory`, behind the existing front door.
- No planning endpoints. The Pi does no routing work.

### 4.3 Browser router (`static/js/router/`)

All of it runs in a dedicated Web Worker (`router-worker.js`), kept separate from `exploration-worker.js` until it replaces it.

**GraphStore.** Zero-copy views over `graph.bin`'s `ArrayBuffer`. Spatial lookup by tile.

**TurnAwarePath.** A* over states `(node, incomingEdge)`, so every transition can be priced:

```
cost(edge e after edge d) = length(e) · modeFactor(e) · surfaceFactor(e) · busyFactor(e)
                          + turnCost(angle(d, e))
turnCost = 0 for < 30°;  T · angle/90° otherwise;  + U for > 150° (U-turns)
```

`T` and `U` are in metre-equivalents and come from the "straighter ↔ more tiles" slider. Walk edges use `modeFactor` of about 3, roughly walking pace against riding pace. The heuristic is straight-line distance over the minimum factor, so A* stays admissible.

**Planner.** It replaces Phase 1 and Phase 2 for regions with a local graph. Its stages:

1. **Targets.** Unclaimed tiles from coverage minus roadless tiles, inside the horizon and drawn area. Group them into 4-connected clusters (the same definition as R1).
2. **Cluster selection** (an orienteering-style choice). Pick clusters by value per estimated cost, reusing today's cluster-value idea (6ddcacb) but with **graph distances**: a multi-source Dijkstra from the start gives the true approach cost per cluster.
3. **Cover each chosen cluster.** Choose a set of *required edges* whose tile sets cover the cluster: weighted set cover, greedy by tiles per (length + turn estimate), preferring long straight edges, followed by redundancy pruning. Because coverage is exact per edge, R1 is satisfied **by construction** for every cluster the route touches, and touching is checked on edges, not after the fact.
4. **Connect.** Order the required-edge groups and connect them with TurnAwarePath. This is a Rural Postman–style problem: required edges plus connecting paths. Heuristic: nearest-group ordering, then within-group sequencing by the cheapest turn-aware traversal (a small Eulerian augmentation over the group's subgraph).
5. **Improve.** Local search on the group order (2-opt, Or-opt) with true graph costs, including turns. This is what the waypoint-level experiments couldn't do, because ORS hid the turns.
6. **Verify exactly.** Recompute R1 from the final edge sequence's tile sets (no geometry guessing), check R2 against the area, then trim or expand clusters to respect the distance target where R1 allows.
7. **Emit.** The full geometry from edge polylines, plus distance, duration, surface mix, a walk-section list and turn and U-turn counts. GPX export uses this geometry. ORS isn't involved.

**Tile claims become exact and local.** The edge→tile index means the UI knows every tile a route claims without calling `/api/exploration/new-tiles`. The backend check can remain as a cross-check.

### 4.4 UI changes ([templates/explore.html](../../templates/explore.html), [static/js/explore.js](../../static/js/explore.js))
- **Route options:**
  - a **"Straighter ↔ More tiles"** slider, which sets `T` and `U`;
  - **"Allow walking connections"**, on by default, with the number of walk sections shown on the route card;
  - **"Avoid busy roads"**, which sets `busyFactor`.
- **Route card:** turns, U-turns, walk metres, and the existing tile and sweep badges.
- **Map:** walk sections drawn dashed.
- When no local region covers the area, the page falls back to the current ORS pipeline, labelled as such.

### 4.5 What stays
- **Coverage and visited tiles:** unchanged ([app/services/exploration_service.py](../../app/services/exploration_service.py), `coverage_tracker.py`).
- **ORS** (`compute_route`, fence, chunking): kept as the fallback outside local regions.
- **Phase 1 and Phase 2:** kept as the fallback path until the planner reaches parity. Then removed in a later release, together with ORS-only code that has no fallback role.

## 5. Data flow (one plan)

1. The page loads coverage (unchanged). `GET /api/router/regions` reports that `chicago-north` covers the area.
2. The worker loads `chicago-north.<hash>.bin`, from the HTTP cache after the first time.
3. The planner builds targets from coverage plus the graph's roadless set, then runs selection → cover → connect → improve → verify.
4. The result returns to the page, gets rendered, and the claimed tiles are shown exactly. GPX export follows.
5. **Zero Pi CPU** beyond static file serving, and **zero ORS calls.**

## 6. Evaluation

Reuse and promote the end-to-end harness built during the turn experiments (a scratch script today). It runs the real coverage and the real scenario and reports:

> km · new tiles · tiles/km · turns · U-turns · walk metres · cluster tiles left (independent R1 check) · plan time

- It gets checked in as `scripts/explore_benchmark/`, the same idea as [scripts/matching_benchmark/](../../scripts/matching_benchmark/).
- It covers 4–6 fixed scenarios: dense home, frontier, drawn box, point-to-point, and the Lake–Cook path example.
- It runs against both the ORS pipeline and the local planner. **Merge gate:** the local planner must meet the §2 goals on every scenario before it becomes the default.

## 7. Milestones

| # | Milestone | Deliverable | Exit criteria |
|---|---|---|---|
| M0 | **Spike** | A build script for one region, plus a debug map layer drawing the graph (ride/walk colours) | Package size measured; the Lake–Cook footpath connections are present as walk edges; roadless tiles match the lake and rail yards by eye |
| M1 | **Data pipeline** | `tools/router/`, `router_regions.yaml`, GitHub Action, Pi pull cron, `router_bp` | A monthly package is published and installed on the Pi; access-model unit tests pass |
| M2 | **Roadless from graph** | Explore uses graph roadless tiles where a region exists | No Overpass call for the Chicago area; water warnings gone |
| M3 | **Turn-aware A→B** | GraphStore + TurnAwarePath in a worker | Point-to-point routes plausible against ORS; turn counts drop with the slider; plan time under 200 ms for 20 km |
| M4 | **Cluster cover** | Stages 1, 3 and 6 replace `refineRoute` stage 5 | R1 holds by construction (0 cluster tiles left); a measured turn reduction on cluster sweeps |
| M5 | **Full planner** | Stages 2–7 replace Phase 1 and 2 in local regions | §2 goals met on all benchmark scenarios; ORS fallback is automatic outside regions |
| M6 | **UI and options** | Slider, walking toggle, busy-road toggle, card metrics, dashed walk sections | Design-principles review; mobile performance under 5 s |
| M7 | **Retire** | Remove superseded Phase 1/2 code paths in local regions | Benchmark parity kept for two releases |

M2 is worth shipping even if the rest stalls: it removes the Overpass dependency that caused the water outage.

## 8. Risks

| Risk | Mitigation |
|---|---|
| **Package size or mobile memory** too high for big regions | Measure in M0; graph tiles plus partial loading; int32/uint16 encodings; drop service roads that serve no tile |
| **OSM gaps** (a missing path, wrong access tag) | The walk toggle and the debug layer make problems visible; the rider can fix OSM upstream; the monthly rebuild picks fixes up |
| **Legality of footways** varies locally | Walk mode is priced, visible, toggleable, and never default-preferred over riding (R3) |
| **Planner quality** below ORS on plain A→B | M3 compares directly; ORS stays as the fallback |
| **Combinatorics**: cover plus connect is NP-hard | Greedy plus local search with time budgets; exact R1 verification means quality can degrade but correctness can't |
| **Maintenance**: a second routing stack | Keep it small and typed-array based; one access-model table; the benchmark guards regressions |
| **ODbL** if ever deployed publicly | Decide on share-alike for the derived graph before a public launch |

## 9. Open questions for the rider

1. **Regions:** just the north Chicago and North Shore area, or more? This sets package size and build cost.
2. **Walking:** on by default, and is any length acceptable, or should individual walk sections be capped (for example 300 m)?
3. **Turn preference:** one slider, or a few fixed presets ("efficient", "balanced", "straight")?
4. **ORS:** keep it as a fallback indefinitely, or drop it once the regions cover all riding?
5. **Devices:** the minimum phone to support for planning in the browser.

## 10. Related
- [#627](https://github.com/e2kd7n/ride-optimizer/pull/627): the first Explore efficiency pass, drawn-area fence and cached-water fallback.
- 4f326e2, 6ddcacb, 90a6974: stop-sized pockets, cluster value, cluster sweep and chunked ORS routing.
- 9ab942a: the background water download (the Overpass dependency that M2 removes).
- #581: the earlier osmnx-based road-segment feature, removed. That was graph work on the server; this design deliberately keeps graph work off the Pi.
- Branch `worktree-explore-fewer-turns` (unmerged): turn experiments and their measurements.
