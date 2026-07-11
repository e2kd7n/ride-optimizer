/**
 * exploration-worker.js — Browser-side route optimization Web Worker
 *
 * Runs clustering + TSP off the main thread so the UI stays responsive.
 * Generates one route per compass quadrant (NE/SE/SW/NW) that has reachable
 * unvisited tiles, streaming each as it finishes rather than waiting for all.
 *
 * Input message: {start, end?, distanceKm, mode, routeType, coverageData, coverageDataSecondary?, optimizeFor}
 *   - start: {lat, lon}
 *   - end: {lat, lon} | null (null = round-trip back to start)
 *   - distanceKm: target route distance
 *   - mode: 'tiles' | 'roads'
 *   - routeType: 'round_trip' | 'point_to_point'
 *   - coverageData: {visited: {"x,y": {...}}, total_in_bounds, bounds, zoom}
 *   - coverageDataSecondary: same shape as coverageData, at a different zoom | null
 *       When present ("Both" grid mode), routes are optimized against both
 *       grids at once — each grid's zones are found independently (tile
 *       adjacency only makes sense within a single zoom's coordinate space),
 *       then the best zones from each are merged into one route per quadrant.
 *   - optimizeFor: 'tiles' | 'distance' | 'efficiency' | 'infill' | 'frontier'
 *
 * Output messages (streamed):
 *   {type: 'route', route: {direction, waypoints, stats}}  — one per generated route
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
function scanGrid(coverageData, start, reachRadius, optimizeFor) {
    const bounds = coverageData.bounds;
    if (!bounds) throw new Error('Coverage data has no bounds');
    const zoom = coverageData.zoom || 14;

    const allTiles = buildTileSet(bounds, zoom);
    const visitedSet = new Set(Object.keys(coverageData.visited || {}));
    const unvisited = allTiles.filter(t => !visitedSet.has(t.key));

    // #404 / #406: filter unvisited set before bucketing based on mode.
    let candidates = unvisited;
    if (optimizeFor === 'infill') {
        // Infill: tiles with ≥ 2 visited 4-neighbours (interior gaps).
        candidates = unvisited.filter(t => countVisitedNeighbours(t, visitedSet) >= 2);
    } else if (optimizeFor === 'frontier') {
        // Frontier: tiles with ≥ 1 visited neighbour, sorted by low surrounding density.
        candidates = unvisited.filter(t => countVisitedNeighbours(t, visitedSet) >= 1);
    }

    const reachableTiles = candidates.filter(
        t => haversineKm(start.lat, start.lon, t.lat, t.lon) <= reachRadius
    );

    const buckets = { NE: [], SE: [], SW: [], NW: [] };
    for (const t of reachableTiles) {
        buckets[quadrantFor(bearingDeg(start.lat, start.lon, t.lat, t.lon))].push(t);
    }

    return { zoom, unvisited, reachableTiles, buckets, visitedSet };
}

/** Count how many of the 4 cardinal neighbours of tile `t` are in `visitedSet`. */
function countVisitedNeighbours(t, visitedSet) {
    return [
        `${t.x},${t.y - 1}`,
        `${t.x},${t.y + 1}`,
        `${t.x - 1},${t.y}`,
        `${t.x + 1},${t.y}`,
    ].filter(k => visitedSet.has(k)).length;
}

function optimize({ start, end, distanceKm, mode, routeType, coverageData, coverageDataSecondary, optimizeFor, corridorConstraint }) {
    const isRoundTrip = routeType === 'round_trip' || !end;
    const reachRadius = distanceKm / (isRoundTrip ? 4 : 3);

    reportProgress('Scanning tile grid…');
    const primary = scanGrid(coverageData, start, reachRadius, optimizeFor, corridorConstraint);
    const secondary = coverageDataSecondary ? scanGrid(coverageDataSecondary, start, reachRadius, optimizeFor, corridorConstraint) : null;
    const grids = secondary ? [primary, secondary] : [primary];

    const totalUnvisited = grids.reduce((sum, g) => sum + g.unvisited.length, 0);
    if (totalUnvisited === 0) {
        return { totalRoutes: 0, stats: { unvisited: 0, zones: 0 } };
    }

    const totalReachable = grids.reduce((sum, g) => sum + g.reachableTiles.length, 0);
    if (totalReachable === 0) {
        // Graceful empty-result messages for infill/frontier modes (#404/#406).
        if (optimizeFor === 'infill') {
            reportProgress('No infill tiles found — yard interior may already be complete');
        } else if (optimizeFor === 'frontier') {
            reportProgress('No frontier tiles found — yard may be fully isolated');
        }
        const zoneCount = grids.reduce((sum, g) => sum + floodFillZones(g.unvisited).length, 0);
        return {
            totalRoutes: 0,
            stats: { unvisited: totalUnvisited, zones: zoneCount, reachable: 0 },
        };
    }

    // Per grid, top candidate zones per quadrant. When merging two grids,
    // cap each grid's contribution so the combined waypoint count per route
    // stays reasonable (TSP brute-force applies up to 8 points).
    const perGridCap = secondary ? 4 : 6;

    let totalRoutes = 0;
    QUADRANTS.forEach((dir, i) => {
        reportProgress(`Optimizing ${dir} route (${i + 1}/${QUADRANTS.length})…`);

        const gridCandidates = grids.map(g => {
            const dirZones = floodFillZones(g.buckets[dir]).map(z => ({
                ...z,
                distanceFromStart: haversineKm(start.lat, start.lon, z.centroid.lat, z.centroid.lon),
            }));
            const scored = scoreZones(dirZones, optimizeFor);
            const penalised = applyOverlapPenalty(scored, start, g.visitedSet, g.zoom);
            return {
                zoom: g.zoom,
                candidates: penalised.slice(0, perGridCap),
            };
        });

        const allCandidates = gridCandidates.flatMap(
            gc => gc.candidates.map(z => ({ ...z, zoom: gc.zoom }))
        );
        if (allCandidates.length === 0) return;

        // For each zone find the corner that claims the most tiles at once,
        // inset ~5 m toward the zone centroid so GPS uncertainty is absorbed.
        const points = allCandidates.map(z =>
            bestCornerPoint(z.tiles, z.zoom, start.lat, start.lon)
        );
        const ordered = solveTSP(start, points, end);

        const breakdown = gridCandidates
            .filter(gc => gc.candidates.length > 0)
            .map(gc => ({
                zoom: gc.zoom,
                label: GRID_LABELS[gc.zoom] || `zoom ${gc.zoom}`,
                count: gc.candidates.reduce((sum, z) => sum + z.tiles.length, 0),
            }));

        // Collect per-zoom new tile lists for map highlighting.
        const newTilesByZoom = gridCandidates
            .filter(gc => gc.candidates.length > 0)
            .map(gc => ({
                zoom: gc.zoom,
                tiles: gc.candidates.flatMap(z => z.tiles.map(t => ({ x: t.x, y: t.y }))),
            }));

        totalRoutes++;
        self.postMessage({
            type: 'route',
            route: {
                direction: dir,
                waypoints: ordered,
                newTilesByZoom,
                stats: {
                    waypoints: ordered.length,
                    zones: allCandidates.length,
                    unvisited: breakdown.reduce((sum, b) => sum + b.count, 0),
                    breakdown: secondary ? breakdown : null,
                    distanceKm: routeDistance(start, ordered, end),
                },
            },
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

/**
 * Estimate how many visited tiles lie along the straight-line corridor from
 * `start` to the zone centroid by sampling the tile grid at intervals.
 * Uses only the already-loaded visitedSet — no extra API calls.
 */
function estimateCorridorOverlap(zone, start, visitedSet, zoom) {
    const steps = Math.max(2, Math.round(zone.distanceFromStart * 4)); // ~1 sample per 250m
    const dlat = (zone.centroid.lat - start.lat) / steps;
    const dlon = (zone.centroid.lon - start.lon) / steps;
    let overlap = 0;
    for (let i = 1; i < steps; i++) {
        const lat = start.lat + dlat * i;
        const lon = start.lon + dlon * i;
        const n = Math.pow(2, zoom);
        const x = Math.floor((lon + 180) / 360 * n);
        const y = Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
        if (visitedSet.has(`${x},${y}`)) overlap++;
    }
    return overlap;
}

/**
 * Order zones by the user's chosen priority before capping to the top few
 * per direction:
 *   - 'tiles'    : biggest contiguous unexplored areas first (default)
 *   - 'distance' : closest to the start point first (shortest route)
 *   - 'efficiency': most new tiles per km of travel to reach them
 *   - 'infill'   : smallest zones first (interior gaps are typically smaller)
 *   - 'frontier' : zones with lower surrounding density ranked higher
 * After primary sort, a secondary overlap penalty (#410) nudges tied zones
 * toward paths that re-cover fewer visited tiles.
 */
function scoreZones(zones, optimizeFor) {
    const scored = [...zones];
    if (optimizeFor === 'distance') {
        scored.sort((a, b) => a.distanceFromStart - b.distanceFromStart);
    } else if (optimizeFor === 'efficiency') {
        scored.sort((a, b) =>
            (b.tiles.length / Math.max(b.distanceFromStart, 0.1)) -
            (a.tiles.length / Math.max(a.distanceFromStart, 0.1))
        );
    } else if (optimizeFor === 'infill') {
        // Smallest zones first — infill gaps are typically tight clusters.
        scored.sort((a, b) => a.tiles.length - b.tiles.length);
    } else if (optimizeFor === 'frontier') {
        // Low-density neighbourhoods ranked first (#406).
        // visitedSet is not available here, so proxy with zone size (smaller = sparser border).
        scored.sort((a, b) => a.tiles.length - b.tiles.length);
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

function quadrantFor(bearing) {
    if (bearing < 90) return 'NE';
    if (bearing < 180) return 'SE';
    if (bearing < 270) return 'SW';
    return 'NW';
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
