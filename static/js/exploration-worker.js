/**
 * exploration-worker.js — Browser-side route optimization Web Worker
 *
 * Runs clustering + TSP off the main thread so the UI stays responsive.
 * Generates one route per compass quadrant (NE/SE/SW/NW) that has reachable
 * unvisited tiles, streaming each as it finishes rather than waiting for all.
 *
 * Input message: {start, end?, distanceKm, mode, routeType, coverageData, optimizeFor}
 *   - start: {lat, lon}
 *   - end: {lat, lon} | null (null = round-trip back to start)
 *   - distanceKm: target route distance
 *   - mode: 'tiles' | 'roads'
 *   - routeType: 'round_trip' | 'point_to_point'
 *   - coverageData: {visited: {"x,y": {...}}, total_in_bounds, bounds, zoom}
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

function optimize({ start, end, distanceKm, mode, routeType, coverageData, optimizeFor }) {
    const bounds = coverageData.bounds;
    if (!bounds) throw new Error('Coverage data has no bounds');
    const zoom = coverageData.zoom || 14;

    const isRoundTrip = routeType === 'round_trip' || !end;
    const reachRadius = distanceKm / (isRoundTrip ? 4 : 3);

    reportProgress('Scanning tile grid…');
    const allTiles = buildTileSet(bounds, zoom);
    const visitedSet = new Set(Object.keys(coverageData.visited || {}));
    const unvisited = allTiles.filter(t => !visitedSet.has(t.key));

    if (unvisited.length === 0) {
        return { totalRoutes: 0, stats: { unvisited: 0, zones: 0 } };
    }

    reportProgress(`Finding tiles within reach…`);
    const reachableTiles = unvisited.filter(
        t => haversineKm(start.lat, start.lon, t.lat, t.lon) <= reachRadius
    );

    if (reachableTiles.length === 0) {
        const zones = floodFillZones(unvisited);
        return {
            totalRoutes: 0,
            stats: { unvisited: unvisited.length, zones: zones.length, reachable: 0 },
        };
    }

    // Bucket individual tiles (not zones) by compass quadrant from the start
    // point *before* flood-filling, so one large contiguous unexplored area
    // still splits into a distinct route per direction rather than collapsing
    // into a single zone/route.
    const buckets = { NE: [], SE: [], SW: [], NW: [] };
    for (const t of reachableTiles) {
        buckets[quadrantFor(bearingDeg(start.lat, start.lon, t.lat, t.lon))].push(t);
    }

    let totalRoutes = 0;
    QUADRANTS.forEach((dir, i) => {
        reportProgress(`Optimizing ${dir} route (${i + 1}/${QUADRANTS.length})…`);
        const dirZones = floodFillZones(buckets[dir]).map(z => ({
            ...z,
            distanceFromStart: haversineKm(start.lat, start.lon, z.centroid.lat, z.centroid.lon),
        }));
        const candidates = scoreZones(dirZones, optimizeFor).slice(0, 6);
        if (candidates.length === 0) return;

        const points = candidates.map(z => z.centroid);
        const ordered = solveTSP(start, points, end);

        totalRoutes++;
        self.postMessage({
            type: 'route',
            route: {
                direction: dir,
                waypoints: ordered,
                stats: {
                    waypoints: ordered.length,
                    zones: candidates.length,
                    unvisited: candidates.reduce((sum, z) => sum + z.tiles.length, 0),
                    distanceKm: routeDistance(start, ordered, end),
                },
            },
        });
    });

    const allReachableZones = floodFillZones(reachableTiles);
    return {
        totalRoutes,
        stats: { unvisited: unvisited.length, zones: allReachableZones.length, reachable: allReachableZones.length },
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
