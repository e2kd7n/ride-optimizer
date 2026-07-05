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
 *   - optimizeFor: 'tiles' | 'distance' | 'efficiency'
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
function scanGrid(coverageData, start, reachRadius) {
    const bounds = coverageData.bounds;
    if (!bounds) throw new Error('Coverage data has no bounds');
    const zoom = coverageData.zoom || 14;

    const allTiles = buildTileSet(bounds, zoom);
    const visitedSet = new Set(Object.keys(coverageData.visited || {}));
    const unvisited = allTiles.filter(t => !visitedSet.has(t.key));
    const reachableTiles = unvisited.filter(
        t => haversineKm(start.lat, start.lon, t.lat, t.lon) <= reachRadius
    );

    const buckets = { NE: [], SE: [], SW: [], NW: [] };
    for (const t of reachableTiles) {
        buckets[quadrantFor(bearingDeg(start.lat, start.lon, t.lat, t.lon))].push(t);
    }

    return { zoom, unvisited, reachableTiles, buckets };
}

function optimize({ start, end, distanceKm, mode, routeType, coverageData, coverageDataSecondary, optimizeFor }) {
    const isRoundTrip = routeType === 'round_trip' || !end;
    const reachRadius = distanceKm / (isRoundTrip ? 4 : 3);

    reportProgress('Scanning tile grid…');
    const primary = scanGrid(coverageData, start, reachRadius);
    const secondary = coverageDataSecondary ? scanGrid(coverageDataSecondary, start, reachRadius) : null;
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
            return {
                zoom: g.zoom,
                candidates: scoreZones(dirZones, optimizeFor).slice(0, perGridCap),
            };
        });

        const allCandidates = gridCandidates.flatMap(
            gc => gc.candidates.map(z => ({ ...z, zoom: gc.zoom }))
        );
        if (allCandidates.length === 0) return;

        // For each zone pick a near-edge entry point instead of the centroid.
        // Find the tile in the zone closest to the start, then place the
        // waypoint just inside its incoming edge (~5 m from the boundary).
        const points = allCandidates.map(z => {
            const closest = z.tiles.reduce((best, t) => {
                const d = haversineKm(start.lat, start.lon, t.lat, t.lon);
                return d < best.d ? { t, d } : best;
            }, { t: z.tiles[0], d: Infinity }).t;
            return tileEntryPoint(closest, z.zoom, start.lat, start.lon);
        });
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

/**
 * Order zones by the user's chosen priority before capping to the top few
 * per direction:
 *   - 'tiles': biggest contiguous unexplored areas first (default)
 *   - 'distance': closest to the start point first (shortest route)
 *   - 'efficiency': most new tiles per km of travel to reach them
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
    } else {
        scored.sort((a, b) => b.tiles.length - a.tiles.length);
    }
    return scored;
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

/**
 * Return the actual lat/lng edges of a tile (not center).
 */
function tileBounds(x, y, zoom) {
    const n = Math.pow(2, zoom);
    const west  = x / n * 360 - 180;
    const east  = (x + 1) / n * 360 - 180;
    const north = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)))       * 180 / Math.PI;
    const south = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n))) * 180 / Math.PI;
    return { north, south, east, west };
}

/**
 * Given a tile and an approach point (fromLat/fromLon), return a waypoint
 * that is ~5 m inside the tile edge that faces the approach direction.
 * This ensures the route only needs to cross into the tile (not reach its center).
 *
 * INSET_DEG ≈ 5 m expressed in degrees:
 *   - latitude:  5 m / 111320 m per degree ≈ 0.000045°
 *   - longitude: adjusted by cos(lat) below
 */
const INSET_M = 5;
const INSET_LAT = INSET_M / 111320;

function tileEntryPoint(tile, zoom, fromLat, fromLon) {
    const b = tileBounds(tile.x, tile.y, zoom);
    const midLat = (b.north + b.south) / 2;
    const insetLon = INSET_M / (111320 * Math.cos(midLat * Math.PI / 180));

    // Determine which edge(s) the approach comes from and set the waypoint
    // just inside that edge, at the lateral midpoint of the tile.
    const fromNorth = fromLat > midLat;
    const fromEast  = fromLon > (b.west + b.east) / 2;

    // Use whichever axis has the greater angular separation to pick the
    // dominant entry edge, keeping the other axis at tile mid.
    const dLat = Math.abs(fromLat - midLat);
    const dLon = Math.abs(fromLon - (b.west + b.east) / 2) * Math.cos(midLat * Math.PI / 180);

    let lat, lon;
    if (dLat >= dLon) {
        // Enter through north or south edge
        lat = fromNorth ? b.north - INSET_LAT : b.south + INSET_LAT;
        lon = (b.west + b.east) / 2;
    } else {
        // Enter through east or west edge
        lat = midLat;
        lon = fromEast ? b.east - insetLon : b.west + insetLon;
    }

    return { lat, lon };
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
