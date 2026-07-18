/**
 * exploration-worker.js — Browser-side route optimization Web Worker
 *
 * Runs clustering + TSP off the main thread so the UI stays responsive.
 * Generates one route per compass quadrant (NE/SE/SW/NW) that has reachable
 * unvisited tiles, streaming each as it finishes rather than waiting for all.
 *
 * Input message: {start, end?, distanceKm, mode, routeType, shape, coverageData, coverageDataSecondary?, optimizeFor}
 *   - start: {lat, lon}
 *   - end: {lat, lon} | null (null = round-trip back to start)
 *   - distanceKm: target route distance
 *   - mode: 'tiles' | 'roads'
 *   - routeType: 'round_trip' | 'point_to_point'
 *   - shape: 'loop' | 'out_and_back' | 'point_to_point' (#489) — for a
 *       round trip, whether outbound/return should be biased toward
 *       different corridors (loop) or deliberately retrace the same one
 *       (out_and_back). Ignored when routeType is 'point_to_point'.
 *   - coverageData: {visited: {"x,y": {...}}, total_in_bounds, bounds, zoom,
 *       water_tiles: ["x,y", ...]} — water_tiles (#525) are predominantly
 *       over-water tiles, excluded from candidate generation same as visited.
 *   - coverageDataSecondary: same shape as coverageData, at a different zoom | null
 *       When present ("Both" grid mode), routes are optimized against both
 *       grids at once — each grid's zones are found independently (tile
 *       adjacency only makes sense within a single zoom's coordinate space),
 *       then the best zones from each are merged into one route per quadrant.
 *   - optimizeFor: 'tiles' | 'efficiency'
 *   - areaBounds: [south, west, north, east] | null (#491) — rider-drawn
 *       target area. When present, further restricts reachable tiles to
 *       those inside the box, in addition to (not instead of) the reach
 *       radius derived from distanceKm.
 *   - windDirectionDeg/windSpeedKph: number | null (#453) — current wind, if
 *       available. Used only as a tie-break between otherwise-equal-yield
 *       tour orientations (headwind out, tailwind back) for round trips with
 *       ≥2 zones; ignored for point-to-point routes or when unavailable.
 *
 * Output messages (streamed):
 *   {type: 'route', route: {direction, waypoints, windLabel, stats}}  — one per generated route
 *   {type: 'done', totalRoutes, stats}                     — sent once, after all routes
 *   {type: 'error', message}                                — fatal error
 */

self.onmessage = function (e) {
    try {
        const summary = optimize(e.data);
        self.postMessage({ type: 'done', ...summary });
    } catch (err) {
        self.postMessage({ type: 'error', message: err.message });
    }
};

function reportProgress(message) {
    self.postMessage({ type: 'progress', message });
}

const QUADRANTS = ['NE', 'SE', 'SW', 'NW'];
const GRID_LABELS = { 14: 'squadrats', 17: 'squadratinhos' };

/**
 * Scan one coverage grid and bucket its reachable unvisited tiles by
 * compass quadrant from the start point. Bucketing individual tiles (not
 * zones) before flood-filling means one large contiguous unexplored area
 * still splits into a distinct route per direction rather than collapsing
 * into a single zone/route.
 */
function scanGrid(coverageData, start, reachRadius, areaBounds) {
    const bounds = coverageData.bounds;
    if (!bounds) throw new Error('Coverage data has no bounds');
    const zoom = coverageData.zoom || 14;

    const allTiles = buildTileSet(bounds, zoom);
    const visitedSet = new Set(Object.keys(coverageData.visited || {}));
    // #525: over-water tiles (lakes, bays, ocean) aren't reachable by bike or
    // foot — exclude them from "new tile" candidates entirely rather than
    // letting them pull generated routes toward water for coverage credit.
    const waterSet = new Set(coverageData.water_tiles || []);
    const unvisited = allTiles.filter(t => !visitedSet.has(t.key) && !waterSet.has(t.key));

    let reachableTiles = unvisited.filter(
        t => haversineKm(start.lat, start.lon, t.lat, t.lon) <= reachRadius
    );
    // #491: rider-drawn target area, additional to (not instead of) the
    // reach radius — a drawn box narrows which reachable tiles count,
    // it doesn't override how far the route is allowed to travel.
    if (areaBounds) {
        const [south, west, north, east] = areaBounds;
        reachableTiles = reachableTiles.filter(
            t => t.lat >= south && t.lat <= north && t.lon >= west && t.lon <= east
        );
    }

    const buckets = { NE: [], SE: [], SW: [], NW: [] };
    for (const t of reachableTiles) {
        buckets[quadrantFor(bearingDeg(start.lat, start.lon, t.lat, t.lon))].push(t);
    }

    return { zoom, unvisited, reachableTiles, buckets, visitedSet };
}

function optimize({ start, end, distanceKm, mode, routeType, shape, coverageData, coverageDataSecondary, optimizeFor, corridorConstraint, areaBounds, windDirectionDeg, windSpeedKph }) {
    const isRoundTrip = routeType === 'round_trip' || !end;
    // Default to 'loop' for round trips when the caller doesn't specify —
    // matches the pre-#489 behaviour of drawing from whichever quadrant the
    // road network happens to support.
    const effectiveShape = !isRoundTrip ? 'point_to_point' : (shape === 'out_and_back' ? 'out_and_back' : 'loop');
    const reachRadius = distanceKm / (isRoundTrip ? 4 : 3);

    reportProgress('Scanning tile grid…');
    const primary = scanGrid(coverageData, start, reachRadius, areaBounds);
    const secondary = coverageDataSecondary ? scanGrid(coverageDataSecondary, start, reachRadius, areaBounds) : null;
    const grids = secondary ? [primary, secondary] : [primary];

    const totalUnvisited = grids.reduce((sum, g) => sum + g.unvisited.length, 0);
    if (totalUnvisited === 0) {
        return { totalRoutes: 0, stats: { unvisited: 0, zones: 0 } };
    }

    const totalReachable = grids.reduce((sum, g) => sum + g.reachableTiles.length, 0);
    if (totalReachable === 0) {
        const zoneCount = grids.reduce((sum, g) => sum + floodFillZones(g.unvisited).length, 0);
        return {
            totalRoutes: 0,
            stats: { unvisited: totalUnvisited, zones: zoneCount, reachable: 0 },
        };
    }

    // Per grid, candidate zone pool per quadrant. When merging two grids,
    // cap each grid's contribution so the combined pool the insertion
    // construction searches over stays a reasonable size.
    const perGridCap = secondary ? 8 : 12;
    // Seeds each quadrant's running claimed-tiles set (#451) with the real
    // ride history, keyed by zoom since tile coordinate spaces differ per grid.
    const visitedSetsByZoom = new Map(grids.map(g => [g.zoom, g.visitedSet]));

    let totalRoutes = 0;
    QUADRANTS.forEach((dir, i) => {
        reportProgress(`Optimizing ${dir} route (${i + 1}/${QUADRANTS.length})…`);

        // #489: 'loop' pulls zones from this quadrant AND its clockwise
        // neighbour so outbound/return legs are biased toward different
        // corridors instead of both living in one compass slice.
        // 'out_and_back' deliberately keeps a single quadrant and takes only
        // its single best zone, accepting the retrace rather than fighting
        // the road network for a loop that may not exist there.
        const scanDirs = effectiveShape === 'loop' ? [dir, nextQuadrant(dir)] : [dir];
        const zoneCap = effectiveShape === 'out_and_back' ? 1 : perGridCap;

        const pool = grids.flatMap(g => {
            const bucketTiles = scanDirs.flatMap(d => g.buckets[d]);
            const dirZones = floodFillZones(bucketTiles).map(z => ({
                ...z,
                distanceFromStart: haversineKm(start.lat, start.lon, z.centroid.lat, z.centroid.lon),
            }));
            const scored = scoreZones(dirZones, optimizeFor);
            const penalised = applyOverlapPenalty(scored, start, g.visitedSet, g.zoom);
            return penalised.slice(0, zoneCap).map(z => ({
                ...z,
                zoom: g.zoom,
                point: bestCornerPoint(z.tiles, g.zoom, start.lat, start.lon),
            }));
        });
        if (pool.length === 0) return;

        const selected = constructInsertionTour(start, end, pool, distanceKm, optimizeFor, visitedSetsByZoom);

        // #453: once outbound/return phases exist (≥2 zones, round trip),
        // prefer whichever traversal direction faces the wind on the way out
        // and rides it on the way back. Reversing the visit order doesn't
        // change which zones/tiles are claimed — only which end of the tour
        // is "outbound" — so this is a pure tie-break, never a factor in
        // which zones got selected above.
        let windLabel = null;
        if (isRoundTrip && selected.length > 1 && windDirectionDeg != null && windSpeedKph != null) {
            const forwardBearing = bearingDeg(start.lat, start.lon, selected[0].point.lat, selected[0].point.lon);
            const reverseBearing = bearingDeg(start.lat, start.lon, selected[selected.length - 1].point.lat, selected[selected.length - 1].point.lon);
            const forwardHeadwind = headwindComponent(windSpeedKph, windDirectionDeg, forwardBearing);
            const reverseHeadwind = headwindComponent(windSpeedKph, windDirectionDeg, reverseBearing);
            if (reverseHeadwind > forwardHeadwind) selected.reverse();
            const chosenHeadwind = Math.max(forwardHeadwind, reverseHeadwind);
            if (chosenHeadwind > 0) {
                windLabel = `↰ headwind out, tailwind back · ${Math.round(windSpeedKph)} km/h`;
            }
        }
        const ordered = selected.map(z => z.point);

        const byZoom = new Map();
        for (const z of selected) {
            if (!byZoom.has(z.zoom)) byZoom.set(z.zoom, []);
            byZoom.get(z.zoom).push(z);
        }
        const breakdown = [...byZoom.entries()].map(([zoom, zones]) => ({
            zoom,
            label: GRID_LABELS[zoom] || `zoom ${zoom}`,
            count: zones.reduce((sum, z) => sum + z.tiles.length, 0),
        }));

        // Collect per-zoom new tile lists for map highlighting.
        const newTilesByZoom = [...byZoom.entries()].map(([zoom, zones]) => ({
            zoom,
            tiles: zones.flatMap(z => z.tiles.map(t => ({ x: t.x, y: t.y }))),
        }));

        // Leftover pool zones that Phase 1 didn't select (budget-capped or
        // below the tiles/km bar) — passed through so Phase 2 (explore.js
        // refineRoute) can pull one in if the plotted road route comes back
        // short of the distance target, instead of only being able to pad
        // with a straight-line displacement that may not follow any road.
        const leftoverCandidates = pool
            .filter(z => !selected.includes(z))
            .map(z => ({ lat: z.point.lat, lon: z.point.lon }));

        totalRoutes++;
        self.postMessage({
            type: 'route',
            route: {
                direction: dir,
                shape: effectiveShape,
                waypoints: ordered,
                windLabel,
                newTilesByZoom,
                stats: {
                    waypoints: ordered.length,
                    zones: selected.length,
                    unvisited: breakdown.reduce((sum, b) => sum + b.count, 0),
                    breakdown: secondary ? breakdown : null,
                    distanceKm: routeDistance(start, ordered, end),
                },
            },
            candidates: leftoverCandidates,
        });
    });

    const totalReachableZones = grids.reduce((sum, g) => sum + floodFillZones(g.reachableTiles).length, 0);
    return {
        totalRoutes,
        stats: { unvisited: totalUnvisited, zones: totalReachableZones, reachable: totalReachableZones },
    };
}

// Weight applied when penalising routes that overlap already-visited tiles (#410).
// 0 disables the penalty entirely; raise to 1.0+ to strongly avoid overlap.
const OVERLAP_PENALTY_WEIGHT = 0.5;

function latLonToTileXY(lat, lon, zoom) {
    const n = Math.pow(2, zoom);
    const x = Math.floor((lon + 180) / 360 * n);
    const y = Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    return { x, y };
}

/**
 * Sample the tile keys a straight-line corridor between two points crosses,
 * at ~1 sample per 250m. Shared by the historical overlap estimate below and
 * by the in-progress-tour overlap tracking in constructInsertionTour (#451).
 */
function sampleCorridorTileKeys(latA, lonA, latB, lonB, zoom) {
    const distKm = haversineKm(latA, lonA, latB, lonB);
    const steps = Math.max(2, Math.round(distKm * 4));
    const keys = [];
    for (let i = 1; i < steps; i++) {
        const t = i / steps;
        const { x, y } = latLonToTileXY(latA + (latB - latA) * t, lonA + (lonB - lonA) * t, zoom);
        keys.push(`${x},${y}`);
    }
    return keys;
}

function countKeysInSet(keys, set) {
    let count = 0;
    for (const k of keys) if (set.has(k)) count++;
    return count;
}

/**
 * Estimate how many visited tiles lie along the straight-line corridor from
 * `start` to the zone centroid by sampling the tile grid at intervals.
 * Uses only the already-loaded visitedSet — no extra API calls.
 */
function estimateCorridorOverlap(zone, start, visitedSet, zoom) {
    return countKeysInSet(
        sampleCorridorTileKeys(start.lat, start.lon, zone.centroid.lat, zone.centroid.lon, zoom),
        visitedSet
    );
}

/**
 * Order zones by the user's chosen priority before capping to the top few
 * per direction:
 *   - 'tiles'      : biggest contiguous unexplored areas first (default)
 *   - 'efficiency' : most new tiles per km of travel to reach them
 * After primary sort, a secondary overlap penalty (#410) nudges tied zones
 * toward paths that re-cover fewer visited tiles.
 */
function scoreZones(zones, optimizeFor) {
    const scored = [...zones];
    if (optimizeFor === 'efficiency') {
        scored.sort((a, b) =>
            (b.tiles.length / Math.max(b.distanceFromStart, 0.1)) -
            (a.tiles.length / Math.max(a.distanceFromStart, 0.1))
        );
    } else {
        scored.sort((a, b) => b.tiles.length - a.tiles.length);
    }
    return scored;
}

/**
 * Apply overlap-avoidance as a secondary sort across any mode (#410).
 * `start` and `visitedSet`/`zoom` come from the calling scanGrid context.
 */
function applyOverlapPenalty(zones, start, visitedSet, zoom) {
    if (OVERLAP_PENALTY_WEIGHT === 0 || zones.length <= 1) return zones;
    return zones.map(z => ({
        ...z,
        _overlapScore: z.tiles.length - OVERLAP_PENALTY_WEIGHT * estimateCorridorOverlap(z, start, visitedSet, zoom),
    })).sort((a, b) => b._overlapScore - a._overlapScore);
}

function bearingDeg(lat1, lon1, lat2, lon2) {
    const phi1 = lat1 * Math.PI / 180, phi2 = lat2 * Math.PI / 180;
    const dLambda = (lon2 - lon1) * Math.PI / 180;
    const y = Math.sin(dLambda) * Math.cos(phi2);
    const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLambda);
    return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

/**
 * Headwind component (positive) / tailwind (negative) of `windSpeed` for a
 * bearing of `travelBearing`, given wind blowing FROM `windDirection` (#453).
 * Mirrors WindImpactCalculator.calculate_wind_component (src/weather_fetcher.py)
 * so client and server agree on what counts as a headwind.
 */
function headwindComponent(windSpeed, windDirection, travelBearing) {
    let relative = (windDirection - travelBearing) % 360;
    if (relative > 180) relative -= 360;
    if (relative < -180) relative += 360;
    return windSpeed * Math.cos(relative * Math.PI / 180);
}

function quadrantFor(bearing) {
    if (bearing < 90) return 'NE';
    if (bearing < 180) return 'SE';
    if (bearing < 270) return 'SW';
    return 'NW';
}

/** Clockwise-adjacent quadrant, used to pull a loop's return leg from a
 *  different corridor than its outbound leg (#489). */
function nextQuadrant(dir) {
    const i = QUADRANTS.indexOf(dir);
    return QUADRANTS[(i + 1) % QUADRANTS.length];
}

// ── Tile utilities ──────────────────────────────────────────────

function buildTileSet(bounds, zoom = 14) {
    const [south, west, north, east] = bounds;
    const n = Math.pow(2, zoom);
    const minX = Math.floor((west + 180) / 360 * n);
    const maxX = Math.floor((east + 180) / 360 * n);
    const minY = Math.floor((1 - Math.asinh(Math.tan(north * Math.PI / 180)) / Math.PI) / 2 * n);
    const maxY = Math.floor((1 - Math.asinh(Math.tan(south * Math.PI / 180)) / Math.PI) / 2 * n);

    const tiles = [];
    for (let x = minX; x <= maxX; x++) {
        for (let y = minY; y <= maxY; y++) {
            const lat = tileCenterLat(y, zoom);
            const lon = tileCenterLon(x, zoom);
            tiles.push({ key: `${x},${y}`, x, y, lat, lon });
        }
    }
    return tiles;
}

function tileCenterLat(y, zoom) {
    const n = Math.pow(2, zoom);
    const latRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 0.5) / n)));
    return latRad * 180 / Math.PI;
}

function tileCenterLon(x, zoom) {
    const n = Math.pow(2, zoom);
    return (x + 0.5) / n * 360 - 180;
}

const INSET_M = 5;

/**
 * For a zone (array of tiles), find the single best corner waypoint that
 * maximises the number of unvisited zone tiles claimed in one pass.
 *
 * A tile corner is a grid intersection shared by up to 4 tiles:
 *   tile (x,y) NE corner == (x+1,y) NW == (x,y-1) SE == (x+1,y-1) SW
 *
 * We enumerate every corner of every tile in the zone, count how many
 * zone tiles share it, then pick the highest-scoring corner that is on
 * the approach side (closest to fromLat/fromLon).  The returned point is
 * inset ~5 m diagonally toward the zone centre so the GPS uncertainty
 * doesn't lose the tiles.
 */
function bestCornerPoint(zone, zoom, fromLat, fromLon) {
    const tileSet = new Set(zone.map(t => t.key));
    const n = Math.pow(2, zoom);
    const INSET_LAT = INSET_M / 111320;

    // Map corner key "cx,cy" → {lat, lon, score}
    // A corner (cx, cy) is shared by tiles (cx-1,cy-1), (cx,cy-1), (cx-1,cy), (cx,cy).
    const corners = new Map();

    for (const t of zone) {
        // Each tile has 4 corners: (x,y), (x+1,y), (x,y+1), (x+1,y+1)
        for (const [cx, cy] of [[t.x, t.y], [t.x+1, t.y], [t.x, t.y+1], [t.x+1, t.y+1]]) {
            const key = `${cx},${cy}`;
            if (!corners.has(key)) {
                // Compute exact lat/lon for this grid corner
                const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * cy / n))) * 180 / Math.PI;
                const lon = cx / n * 360 - 180;
                corners.set(key, { lat, lon, score: 0, cx, cy });
            }
            // Count how many zone tiles this corner touches
            // (the 4 tiles that share corner (cx,cy) are (cx-1,cy-1),(cx,cy-1),(cx-1,cy),(cx,cy))
            let score = 0;
            for (const [dx, dy] of [[0,0],[1,0],[0,1],[1,1]]) {
                if (tileSet.has(`${cx - dx},${cy - dy}`)) score++;
            }
            corners.get(key).score = Math.max(corners.get(key).score, score);
        }
    }

    // Pick best corner: highest score, tie-break by proximity to fromLat/fromLon
    let best = null;
    for (const c of corners.values()) {
        if (!best || c.score > best.score ||
            (c.score === best.score &&
             Math.hypot(c.lat - fromLat, (c.lon - fromLon) * Math.cos(fromLat * Math.PI / 180)) <
             Math.hypot(best.lat - fromLat, (best.lon - fromLon) * Math.cos(fromLat * Math.PI / 180)))) {
            best = c;
        }
    }

    if (!best) {
        // Fallback: use first tile's center
        return { lat: zone[0].lat, lon: zone[0].lon };
    }

    // Inset the corner ~5 m toward the zone centroid so we're safely inside all tiles.
    const centLat = zone.reduce((s, t) => s + t.lat, 0) / zone.length;
    const centLon = zone.reduce((s, t) => s + t.lon, 0) / zone.length;
    const dLat = centLat - best.lat;
    const dLon = centLon - best.lon;
    const dist = Math.hypot(dLat, dLon * Math.cos(best.lat * Math.PI / 180)) || 1;
    const insetLon = INSET_M / (111320 * Math.cos(best.lat * Math.PI / 180));

    return {
        lat: best.lat + (dLat / dist) * INSET_LAT,
        lon: best.lon + (dLon / dist) * insetLon,
    };
}

// ── Flood-fill zone detection ───────────────────────────────────

function floodFillZones(tiles) {
    const lookup = new Map();
    for (const t of tiles) lookup.set(t.key, t);

    const visited = new Set();
    const zones = [];

    for (const t of tiles) {
        if (visited.has(t.key)) continue;

        const zone = [];
        const queue = [t];
        visited.add(t.key);

        while (queue.length > 0) {
            const curr = queue.shift();
            zone.push(curr);

            for (const [dx, dy] of [[0,1],[0,-1],[1,0],[-1,0]]) {
                const nk = `${curr.x + dx},${curr.y + dy}`;
                if (!visited.has(nk) && lookup.has(nk)) {
                    visited.add(nk);
                    queue.push(lookup.get(nk));
                }
            }
        }

        const centroid = {
            lat: zone.reduce((s, t) => s + t.lat, 0) / zone.length,
            lon: zone.reduce((s, t) => s + t.lon, 0) / zone.length,
        };
        zones.push({ tiles: zone, centroid });
    }
    return zones;
}

// ── Reward-weighted cheapest-insertion tour construction (#450) ─

// How far over the target distance the constructed tour may run before a
// candidate insertion is rejected for blowing the budget.
const INSERTION_DISTANCE_TOLERANCE = 1.15;
// A candidate must add at least this many new tiles per km of extra travel
// to be worth inserting at all — below this, further zones stop being added
// even if the distance budget has room left.
const MIN_TILES_PER_KM = 0.15;

/**
 * Build a tour by greedy cheapest insertion instead of distance-minimizing
 * TSP (#450). Minimizing distance is the wrong objective when the goal is
 * maximizing distinct tiles per distance budget: when candidates sit roughly
 * along one ray from `start`, the distance-optimal tour is "farthest zone,
 * straight back," which retraces already-claimed tiles on the return leg.
 *
 * Seeds the tour with the single farthest candidate, then repeatedly inserts
 * whichever remaining candidate scores highest — tiles gained per km of
 * extra travel the insertion costs — at whichever position in the tour is
 * cheapest, stopping once no candidate clears the minimum tiles/km floor or
 * the next insertion would exceed the distance budget.
 *
 * `visitedSetsByZoom` (Map<zoom, Set<tileKey>>) seeds a running "claimed
 * tiles" set per zoom (#451): after each insertion, the tiles along that
 * leg's approach/departure corridor are added to the running set, so a later
 * candidate whose approach path would retrace a corridor an earlier leg in
 * *this same tour* already claimed is penalised the same way retracing
 * historically-ridden tiles already is — not just against ride history.
 */
function constructInsertionTour(start, end, candidates, distanceKm, optimizeFor, visitedSetsByZoom) {
    if (candidates.length === 0) return [];

    const budgetKm = distanceKm * INSERTION_DISTANCE_TOLERANCE;
    const closePoint = end || start;

    const claimedByZoom = new Map();
    const claimedSetFor = (zoom) => {
        if (!claimedByZoom.has(zoom)) {
            claimedByZoom.set(zoom, new Set(visitedSetsByZoom?.get(zoom) || []));
        }
        return claimedByZoom.get(zoom);
    };
    const claimLeg = (fromPoint, toPoint, zoom) => {
        const claimed = claimedSetFor(zoom);
        for (const k of sampleCorridorTileKeys(fromPoint.lat, fromPoint.lon, toPoint.lat, toPoint.lon, zoom)) {
            claimed.add(k);
        }
    };
    const legOverlap = (fromPoint, toPoint, zoom) =>
        countKeysInSet(sampleCorridorTileKeys(fromPoint.lat, fromPoint.lon, toPoint.lat, toPoint.lon, zoom), claimedSetFor(zoom));

    const remaining = [...candidates];
    let seedIdx = 0;
    for (let i = 1; i < remaining.length; i++) {
        if (remaining[i].distanceFromStart > remaining[seedIdx].distanceFromStart) seedIdx = i;
    }
    const seed = remaining.splice(seedIdx, 1)[0];
    let tour = [seed];
    claimLeg(start, seed.point, seed.zoom);
    claimLeg(seed.point, closePoint, seed.zoom);

    // 'efficiency' weighs candidates strictly by tiles gained per km of
    // insertion cost. 'tiles' (default) still needs cost to compare
    // candidates and enforce the budget, but favors raw new-tile count more
    // strongly by discounting cost's influence on the score.
    const costExponent = optimizeFor === 'efficiency' ? 1 : 0.4;

    while (remaining.length > 0) {
        let best = null;
        for (let i = 0; i < remaining.length; i++) {
            const cand = remaining[i];
            for (let pos = 0; pos <= tour.length; pos++) {
                const prev = pos === 0 ? start : tour[pos - 1].point;
                const next = pos === tour.length ? closePoint : tour[pos].point;
                const insertCost = haversineKm(prev.lat, prev.lon, cand.point.lat, cand.point.lon) +
                    haversineKm(cand.point.lat, cand.point.lon, next.lat, next.lon) -
                    haversineKm(prev.lat, prev.lon, next.lat, next.lon);

                const overlap = legOverlap(prev, cand.point, cand.zoom) + legOverlap(cand.point, next, cand.zoom);
                const effectiveTiles = Math.max(cand.tiles.length - OVERLAP_PENALTY_WEIGHT * overlap, 0.1);

                const tilesPerKm = effectiveTiles / Math.max(insertCost, 0.01);
                if (tilesPerKm < MIN_TILES_PER_KM) continue;

                const score = effectiveTiles / Math.pow(Math.max(insertCost, 0.01), costExponent);
                if (!best || score > best.score) {
                    best = { i, pos, score, prev, next };
                }
            }
        }
        if (!best) break;

        const trial = [...tour];
        trial.splice(best.pos, 0, remaining[best.i]);
        if (routeDistance(start, trial.map(z => z.point), end) > budgetKm) break;

        const chosen = remaining[best.i];
        claimLeg(best.prev, chosen.point, chosen.zoom);
        claimLeg(chosen.point, best.next, chosen.zoom);

        tour = trial;
        remaining.splice(best.i, 1);
    }

    return tour;
}

// ── TSP (brute-force for ≤8 points) ─────────────────────────────

function solveTSP(start, points, end) {
    if (points.length <= 1) return points;

    const n = points.length;
    if (n > 8) {
        return nearestNeighborTSP(start, points, end);
    }

    const indices = points.map((_, i) => i);
    let bestDist = Infinity;
    let bestPerm = indices;

    const permute = (arr, l = 0) => {
        if (l === arr.length - 1) {
            const d = routeDistance(start, arr.map(i => points[i]), end);
            if (d < bestDist) {
                bestDist = d;
                bestPerm = [...arr];
            }
            return;
        }
        for (let i = l; i < arr.length; i++) {
            [arr[l], arr[i]] = [arr[i], arr[l]];
            permute(arr, l + 1);
            [arr[l], arr[i]] = [arr[i], arr[l]];
        }
    };
    permute(indices);

    return bestPerm.map(i => points[i]);
}

function nearestNeighborTSP(start, points, end) {
    const remaining = [...points];
    const ordered = [];
    let current = start;

    while (remaining.length > 0) {
        let bestIdx = 0;
        let bestDist = Infinity;
        for (let i = 0; i < remaining.length; i++) {
            const d = haversineKm(current.lat, current.lon, remaining[i].lat, remaining[i].lon);
            if (d < bestDist) {
                bestDist = d;
                bestIdx = i;
            }
        }
        current = remaining.splice(bestIdx, 1)[0];
        ordered.push(current);
    }
    return ordered;
}

function routeDistance(start, waypoints, end) {
    let total = 0;
    let prev = start;
    for (const wp of waypoints) {
        total += haversineKm(prev.lat, prev.lon, wp.lat, wp.lon);
        prev = wp;
    }
    if (end) {
        total += haversineKm(prev.lat, prev.lon, end.lat, end.lon);
    } else {
        total += haversineKm(prev.lat, prev.lon, start.lat, start.lon);
    }
    return total;
}

// ── Haversine ───────────────────────────────────────────────────

function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
}
