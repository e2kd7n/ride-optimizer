/**
 * explore-refine.js — pure geometry helpers for Explore's Phase 2 (road route)
 * refinement. Loaded as a plain <script> before explore.js (exposes
 * window.ExploreRefine) and require()-able from node for unit tests
 * (tests/js/explore-refine.test.js).
 *
 * Coordinates are [lat, lon] arrays throughout, matching the ORS route
 * response (`result.coordinates`) and explore.js's waypoint lists.
 *
 * What lives here:
 *   - tile math + "which unclaimed tiles does this polyline cross"
 *   - findPickups(): unclaimed tiles just off a routed line that a short
 *     detour would claim
 *   - analyzeRetrace(): how much of a routed line rides the same road twice,
 *     and which waypoint's spur is responsible
 *   - insertion/drop position choices for Phase 2 waypoint edits
 *   - fractionOutsideBounds(): did the route leave the rider's drawn area
 *
 * A drawn "area" (`bounds` below) is either a box [south, west, north, east]
 * or a polygon [[lat, lon], [lat, lon], ...] (3+ vertices, open ring) — every
 * bounds helper accepts both.
 */
(function (root) {
    'use strict';

    const EARTH_KM = 6371;
    const M_PER_DEG_LAT = 111320;

    function haversineKm(a, b) {
        const dLat = (b[0] - a[0]) * Math.PI / 180;
        const dLon = (b[1] - a[1]) * Math.PI / 180;
        const h = Math.sin(dLat / 2) ** 2 +
            Math.cos(a[0] * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
        return 2 * EARTH_KM * Math.asin(Math.sqrt(h));
    }

    function pathKm(points) {
        let total = 0;
        for (let i = 1; i < points.length; i++) total += haversineKm(points[i - 1], points[i]);
        return total;
    }

    // ── Tiles ──────────────────────────────────────────────────────

    function latLonToTile(lat, lon, zoom) {
        const n = Math.pow(2, zoom);
        const x = Math.floor((lon + 180) / 360 * n);
        const latRad = lat * Math.PI / 180;
        const y = Math.floor((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2 * n);
        return { x, y };
    }

    /** [south, west, north, east] of tile (x, y). */
    function tileBounds(x, y, zoom) {
        const n = Math.pow(2, zoom);
        const lonW = x / n * 360 - 180;
        const lonE = (x + 1) / n * 360 - 180;
        const latN = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI;
        const latS = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n))) * 180 / Math.PI;
        return [latS, lonW, latN, lonE];
    }

    function tileSideKm(zoom, lat) {
        return 40075.016686 * Math.cos(lat * Math.PI / 180) / Math.pow(2, zoom);
    }

    /** Same row-run water lookup as exploration-worker.js (#604). */
    function buildRoadlessLookup(runs) {
        if (!runs || runs.length === 0) return () => false;
        const byRow = new Map();
        for (const [y, x0, x1] of runs) {
            let row = byRow.get(y);
            if (!row) { row = []; byRow.set(y, row); }
            row.push(x0, x1);
        }
        return (x, y) => {
            const row = byRow.get(y);
            if (!row) return false;
            for (let i = 0; i < row.length; i += 2) {
                if (x >= row[i] && x <= row[i + 1]) return true;
            }
            return false;
        };
    }

    /**
     * Build a grid descriptor from explore.js's coverageData
     * ({zoom, visited: {"x,y": ...}, roadless_runs?}).
     */
    function makeGrid(coverage) {
        const zoom = coverage.zoom || 14;
        const grid = {
            zoom,
            visited: new Set(Object.keys(coverage.visited || {})),
            isRoadless: buildRoadlessLookup(coverage.roadless_runs),
            tileRange: null,
        };
        // Loaded coverage area = the horizon: tiles outside it have unknown
        // status and are never treated as unclaimed.
        if (coverage.bounds) {
            const [south, west, north, east] = coverage.bounds;
            const a = latLonToTile(north, west, zoom), b = latLonToTile(south, east, zoom);
            grid.tileRange = { minX: a.x, maxX: b.x, minY: a.y, maxY: b.y };
        }
        return grid;
    }

    /**
     * Densify a polyline so consecutive points are at most `stepKm` apart.
     * Returns [{p: [lat, lon], s: cumulativeKm}].
     */
    function densify(coords, stepKm) {
        const out = [];
        if (!coords || coords.length === 0) return out;
        let s = 0;
        out.push({ p: coords[0], s: 0 });
        for (let i = 1; i < coords.length; i++) {
            const a = coords[i - 1], b = coords[i];
            const d = haversineKm(a, b);
            const n = Math.max(1, Math.ceil(d / stepKm));
            for (let k = 1; k <= n; k++) {
                const t = k / n;
                out.push({ p: [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], s: s + d * t });
            }
            s += d;
        }
        return out;
    }

    /** Set of "x,y" keys of every tile (visited or not) the polyline enters. */
    function tilesTouched(coords, zoom) {
        const keys = new Set();
        if (!coords || coords.length === 0) return keys;
        const step = tileSideKm(zoom, coords[0][0]) / 6;
        for (const { p } of densify(coords, step)) {
            const { x, y } = latLonToTile(p[0], p[1], zoom);
            keys.add(`${x},${y}`);
        }
        return keys;
    }

    /** Unclaimed (not visited, not water) tiles the polyline enters, per grid. */
    function newTilesCrossed(coords, grid) {
        const out = new Set();
        for (const k of tilesTouched(coords, grid.zoom)) {
            if (grid.visited.has(k)) continue;
            const [x, y] = k.split(',').map(Number);
            if (grid.isRoadless(x, y)) continue;
            out.add(k);
        }
        return out;
    }

    function countNewTiles(coords, grids) {
        return grids.reduce((sum, g) => sum + newTilesCrossed(coords, g).size, 0);
    }

    // ── Local metric projection + spatial hash ─────────────────────

    function projector(lat0) {
        const mPerDegLon = M_PER_DEG_LAT * Math.cos(lat0 * Math.PI / 180);
        return (p) => [p[1] * mPerDegLon, p[0] * M_PER_DEG_LAT];
    }

    function buildHash(points, cellM) {
        const hash = new Map();
        points.forEach((pt, i) => {
            const k = `${Math.floor(pt.xy[0] / cellM)},${Math.floor(pt.xy[1] / cellM)}`;
            let bucket = hash.get(k);
            if (!bucket) { bucket = []; hash.set(k, bucket); }
            bucket.push(i);
        });
        return hash;
    }

    function* neighbours(hash, xy, cellM, radiusCells) {
        const cx = Math.floor(xy[0] / cellM), cy = Math.floor(xy[1] / cellM);
        for (let dx = -radiusCells; dx <= radiusCells; dx++) {
            for (let dy = -radiusCells; dy <= radiusCells; dy++) {
                const bucket = hash.get(`${cx + dx},${cy + dy}`);
                if (bucket) yield* bucket;
            }
        }
    }

    // ── Pickups: unclaimed tiles just off the routed line ──────────

    /**
     * Find unclaimed tiles the route passes close to but doesn't enter.
     *
     * For each grid, every unclaimed, non-water tile whose nearest edge is
     * within `maxReachM` of the routed line (and that the line doesn't
     * already cross) becomes a candidate. Its waypoint sits inside the tile
     * (the tile centre, or `insetM` in from the edge facing the route for
     * big tiles) so the router has to actually enter it. Each candidate
     * carries an estimated detour (out and back from the line, scaled for
     * roads) and a value (1 tile, plus a little for unclaimed neighbours a
     * detour into this block tends to clip as well).
     *
     * Returns candidates sorted best-first by value per detour km, already
     * filtered by `minTilesPerKmFraction` of the fresh-ground rate and to
     * `bounds` when given. Nearby duplicates (within one tile of a better
     * pick on the same grid) are dropped so a row of adjacent tiles along
     * the route doesn't become a row of separate detours.
     */
    /**
     * "Ride the next street over": runs of unclaimed tiles that lie in a
     * straight line right beside a stretch the route already rides.
     *
     * A run is 2+ consecutive unclaimed tiles in one row (or column) whose
     * neighbours one tile toward the route are all crossed by the route, so
     * the route runs parallel to them. Shifting that stretch over one street
     * costs about one jog out and one jog back (2 × a tile side × road
     * factor), however long the run. findPickups prices every tile as its
     * own out-and-back detour and keeps one tile per run, so it badly
     * undervalues these.
     *
     * Returns runs sorted by tiles per detour km:
     * [{zoom, tiles: [[x, y], ...], points: [[lat, lon], ...], detourKm, rate}].
     * Points are tile centres along the run (both ends, plus every other
     * tile between) so the router stays on the parallel street.
     */
    function findRowPickups(coords, grids, opts = {}) {
        const { roadFactor = 1.4, bounds = null, minRun = 2 } = opts;
        if (!coords || coords.length < 2 || !grids || grids.length === 0) return [];
        const out = [];
        for (const grid of grids) {
            const z = grid.zoom;
            const crossed = tilesTouched(coords, z);
            const sideKm = tileSideKm(z, coords[0][0]);
            const free = (x, y) => {
                const k = `${x},${y}`;
                return !crossed.has(k) && !grid.visited.has(k) && !grid.isRoadless(x, y);
            };
            const centre = (x, y) => { const b = tileBounds(x, y, z); return [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]; };
            const used = new Set();
            // Direction of the run (dx, dy) and the side the route is on (sx, sy).
            const dirs = [[1, 0, 0, 1], [1, 0, 0, -1], [0, 1, 1, 0], [0, 1, -1, 0]];
            for (const key of crossed) {
                const [cx, cy] = key.split(',').map(Number);
                for (const [dx, dy, sx, sy] of dirs) {
                    // Start of a run: the tile beside this crossed tile, with
                    // no run tile just before it.
                    const x0 = cx - sx, y0 = cy - sy;
                    if (!free(x0, y0) || used.has(`${z}:${x0},${y0}`)) continue;
                    if (free(x0 - dx, y0 - dy) && crossed.has(`${x0 - dx + sx},${y0 - dy + sy}`)) continue;
                    const tiles = [];
                    let x = x0, y = y0;
                    while (free(x, y) && crossed.has(`${x + sx},${y + sy}`)) {
                        tiles.push([x, y]);
                        x += dx; y += dy;
                    }
                    if (tiles.length < minRun) continue;
                    const points = tiles.filter((_, i) => i === 0 || i === tiles.length - 1 || i % 2 === 0).map(([tx, ty]) => centre(tx, ty));
                    if (bounds && !points.every(p => pointInBounds(p, bounds))) continue;
                    tiles.forEach(([tx, ty]) => used.add(`${z}:${tx},${ty}`));
                    const detourKm = 2 * sideKm * roadFactor + 0.05;
                    out.push({ zoom: z, tiles, points, detourKm, rate: tiles.length / detourKm });
                }
            }
        }
        return out.sort((a, b) => b.rate - a.rate);
    }

    function findPickups(coords, grids, opts = {}) {
        const {
            maxReachM = 350,
            insetM = 150,
            roadFactor = 1.4,
            // Same fraction of the fresh-ground rate as Phase 1's tour floor
            // (MIN_YIELD_FRACTION in exploration-worker.js): at z17 a tile
            // one block off the route (~0.75 km detour) clears it.
            minTilesPerKmFraction = 0.2,
            bounds = null,
        } = opts;
        if (!coords || coords.length < 2 || !grids || grids.length === 0) return [];

        const lat0 = coords[0][0];
        const proj = projector(lat0);
        const line = densify(coords, 0.02).map(d => ({ p: d.p, xy: proj(d.p) }));
        const cellM = 100;
        const hash = buildHash(line, cellM);
        const reachCells = Math.ceil(maxReachM / cellM) + 1;

        const distToLine = (xy) => {
            let best = Infinity, bestIdx = -1;
            for (const i of neighbours(hash, xy, cellM, reachCells)) {
                const d = Math.hypot(line[i].xy[0] - xy[0], line[i].xy[1] - xy[1]);
                if (d < best) { best = d; bestIdx = i; }
            }
            return { d: best, idx: bestIdx };
        };

        const out = [];
        for (const grid of grids) {
            const crossed = tilesTouched(coords, grid.zoom);
            const sideKm = tileSideKm(grid.zoom, lat0);
            const floor = minTilesPerKmFraction / sideKm;
            // Candidate tiles: every tile within reach of a line sample.
            const reachTiles = Math.ceil((maxReachM / 1000) / sideKm) + 1;
            const seen = new Set();
            const sampleEvery = Math.max(1, Math.floor((sideKm * 1000 / 2) / 20));
            for (let li = 0; li < line.length; li += sampleEvery) {
                const { x: tx, y: ty } = latLonToTile(line[li].p[0], line[li].p[1], grid.zoom);
                for (let dx = -reachTiles; dx <= reachTiles; dx++) {
                    for (let dy = -reachTiles; dy <= reachTiles; dy++) {
                        const x = tx + dx, y = ty + dy, key = `${x},${y}`;
                        if (seen.has(key)) continue;
                        seen.add(key);
                        if (crossed.has(key) || grid.visited.has(key) || grid.isRoadless(x, y)) continue;
                        const tb = tileBounds(x, y, grid.zoom);
                        // Nearest point of the tile to the line ≈ check the
                        // tile's edge midpoints, corners and centre.
                        const probes = [
                            [(tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2],
                            [tb[0], tb[1]], [tb[0], tb[3]], [tb[2], tb[1]], [tb[2], tb[3]],
                            [tb[0], (tb[1] + tb[3]) / 2], [tb[2], (tb[1] + tb[3]) / 2],
                            [(tb[0] + tb[2]) / 2, tb[1]], [(tb[0] + tb[2]) / 2, tb[3]],
                        ];
                        let nearest = { d: Infinity, idx: -1, probe: null };
                        for (const pr of probes) {
                            const r = distToLine(proj(pr));
                            if (r.d < nearest.d) nearest = { ...r, probe: pr };
                        }
                        if (nearest.d > maxReachM) continue;

                        // Waypoint: tile centre for small tiles; for big ones,
                        // insetM in from the nearest edge toward the centre.
                        const centre = probes[0];
                        let wp = centre;
                        const halfM = sideKm * 500;
                        if (halfM > insetM && nearest.probe !== centre) {
                            const t = insetM / halfM;
                            wp = [
                                nearest.probe[0] + (centre[0] - nearest.probe[0]) * t,
                                nearest.probe[1] + (centre[1] - nearest.probe[1]) * t,
                            ];
                        }
                        if (bounds && !pointInBounds(wp, bounds)) continue;

                        const wpDist = distToLine(proj(wp));
                        const detourKm = (2 * Math.min(wpDist.d, maxReachM * 2) / 1000) * roadFactor + 0.05;
                        let bonus = 0;
                        for (const [ax, ay] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
                            const nk = `${x + ax},${y + ay}`;
                            if (!crossed.has(nk) && !grid.visited.has(nk) && !grid.isRoadless(x + ax, y + ay)) bonus += 0.5;
                        }
                        const value = 1 + Math.min(bonus, 1);
                        const rate = value / detourKm;
                        if (rate < floor) continue;
                        out.push({
                            lat: wp[0], lon: wp[1], zoom: grid.zoom, x, y,
                            value, detourKm, rate,
                        });
                    }
                }
            }
        }

        out.sort((a, b) => b.rate - a.rate);
        const kept = [];
        for (const c of out) {
            const dup = kept.some(k => k.zoom === c.zoom && Math.abs(k.x - c.x) <= 1 && Math.abs(k.y - c.y) <= 1);
            if (!dup) kept.push(c);
        }
        return kept;
    }

    // ── Cluster sweep: never leave an adjacent cluster tile behind ──

    /**
     * Unclaimed tiles a route must still claim under the cluster rule:
     * an unclaimed tile that shares an edge with a tile the route enters,
     * and that belongs to a cluster (it has at least one unclaimed
     * neighbour, counting tiles the route itself claims), must be claimed —
     * unless it's at the boundary/horizon (outside the drawn area or the
     * loaded coverage), water, or in \`exclude\` (tried and unreachable).
     *
     * Applied to a final route this means: once the route touches a
     * cluster, it sweeps the whole cluster. So each touched cluster's full
     * 4-connected component is returned, not just the adjacent ring — except
     * components bigger than \`maxComponent\` tiles, which are open frontier
     * rather than a cluster to finish; for those only the adjacent ring is
     * returned.
     *
     * Returns [{x, y, zoom, lat, lon, component}] (lat/lon = waypoint inside
     * the tile, toward the route), grouped by component, nearest first.
     */
    function clusterSweepTargets(coords, grids, opts = {}) {
        const { bounds = null, exclude = new Set(), maxComponent = 80, insetM = 120 } = opts;
        if (!coords || coords.length < 2 || !grids || grids.length === 0) return [];
        const lat0 = coords[0][0];
        const proj = projector(lat0);
        const line = densify(coords, 0.02).map(d => ({ p: d.p, xy: proj(d.p) }));
        const cellM = 100;
        const hash = buildHash(line, cellM);
        const distToLine = (xy) => {
            for (let r = 1; r < 200; r *= 2) {
                let best = Infinity;
                for (const i of neighbours(hash, xy, cellM, r)) {
                    const d = Math.hypot(line[i].xy[0] - xy[0], line[i].xy[1] - xy[1]);
                    if (d < best) best = d;
                }
                if (best < Infinity) return best;
            }
            return Infinity;
        };

        const out = [];
        let componentId = 0;
        for (const grid of grids) {
            const z = grid.zoom;
            const crossed = tilesTouched(coords, z);
            const inHorizon = (x, y) => {
                const r = grid.tileRange;
                if (r && (x < r.minX || x > r.maxX || y < r.minY || y > r.maxY)) return false;
                if (bounds) {
                    const tb = tileBounds(x, y, z);
                    const c = [(tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2];
                    if (!pointInBounds(c, bounds)) return false;
                }
                return true;
            };
            // Unclaimed in ride history (crossed-by-route tiles included).
            const unclaimed = (x, y) => !grid.visited.has(`${x},${y}`) && !grid.isRoadless(x, y) && inHorizon(x, y);
            const N4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];

            const assigned = new Set();
            for (const key of crossed) {
                const [cx, cy] = key.split(',').map(Number);
                for (const [dx, dy] of N4) {
                    const x = cx + dx, y = cy + dy, k = `${x},${y}`;
                    if (assigned.has(k) || crossed.has(k) || !unclaimed(x, y)) continue;
                    // In a cluster? Needs an unclaimed neighbour of its own.
                    if (!N4.some(([ax, ay]) => unclaimed(x + ax, y + ay))) continue;

                    // Its component among unclaimed tiles (bounded BFS).
                    const comp = [];
                    const seen = new Set([k]);
                    const queue = [[x, y]];
                    let tooBig = false;
                    while (queue.length) {
                        const [qx, qy] = queue.shift();
                        comp.push([qx, qy]);
                        if (comp.length > maxComponent) { tooBig = true; break; }
                        for (const [ax, ay] of N4) {
                            const nx = qx + ax, ny = qy + ay, nk = `${nx},${ny}`;
                            if (!seen.has(nk) && unclaimed(nx, ny)) { seen.add(nk); queue.push([nx, ny]); }
                        }
                    }
                    let tiles;
                    if (tooBig) {
                        // Frontier: just the tiles directly adjacent to the route.
                        tiles = [[x, y]];
                    } else {
                        tiles = comp.filter(([tx, ty]) => !crossed.has(`${tx},${ty}`));
                    }
                    componentId++;
                    for (const [tx, ty] of tiles) {
                        const tk = `${tx},${ty}`;
                        if (assigned.has(tk)) continue;
                        assigned.add(tk);
                        if (exclude.has(`${z}:${tk}`)) continue;
                        const tb = tileBounds(tx, ty, z);
                        const centre = [(tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2];
                        const sideM = tileSideKm(z, lat0) * 1000;
                        let wp = centre;
                        if (sideM / 2 > insetM) {
                            // Big tile: aim just inside its edge nearest the route.
                            const probes = [
                                [tb[0], centre[1]], [tb[2], centre[1]], [centre[0], tb[1]], [centre[0], tb[3]],
                            ];
                            let near = probes[0], nd = Infinity;
                            for (const pr of probes) { const d = distToLine(proj(pr)); if (d < nd) { nd = d; near = pr; } }
                            const t = insetM / (sideM / 2);
                            wp = [near[0] + (centre[0] - near[0]) * t, near[1] + (centre[1] - near[1]) * t];
                        }
                        out.push({ x: tx, y: ty, zoom: z, lat: wp[0], lon: wp[1], component: componentId, dist: distToLine(proj(wp)) });
                    }
                }
            }
        }
        // Nearest components first, and within a component nearest tiles first.
        const compDist = new Map();
        for (const t of out) compDist.set(t.component, Math.min(compDist.get(t.component) ?? Infinity, t.dist));
        out.sort((a, b) => (compDist.get(a.component) - compDist.get(b.component)) || (a.component - b.component) || (a.dist - b.dist));
        return out;
    }

    /**
     * Insert sweep targets into a waypoint list, each at its cheapest
     * position (straight-line). Inserting a component's tiles nearest-first
     * grows a local detour out from where the route touches the cluster.
     * Returns {waypoints, meta}.
     */
    function insertSweepTargets(waypoints, meta, targets) {
        const wps = waypoints.map(w => [...w]);
        const m = meta.map(x => ({ ...x }));
        for (const t of targets) {
            const pt = [t.lat, t.lon];
            const { index } = cheapestInsertion(wps, pt);
            wps.splice(index, 0, pt);
            m.splice(index - 1, 0, { tiles: 1, sweep: true });
        }
        return { waypoints: wps, meta: m };
    }

    /**
     * Pick which clusters to sweep within a distance budget.
     *
     * `targets` come from clusterSweepTargets (tagged with `component`).
     * Clusters are taken whole, since sweeping half of one doesn't satisfy
     * the rule. They're taken best value first (tiles per estimated extra km)
     * while the estimated route stays within `budgetKm`. The estimate is the
     * straight-line insertion cost scaled by `roadRatio` (the route's measured
     * road km per straight-line km). Without a budget, a dense patchwork
     * cascades: each sweep detour touches new clusters, and the next round
     * sweeps those too.
     *
     * Returns {batch, skippedTiles}: batch is the chosen targets (still in
     * nearest-first order), skippedTiles the targets left out for budget or
     * waypoint room.
     */
    function budgetSweepBatch(waypoints, targets, { budgetKm = Infinity, roadRatio = 1.3, room = Infinity } = {}) {
        const comps = new Map();
        for (const t of targets) {
            if (!comps.has(t.component)) comps.set(t.component, []);
            comps.get(t.component).push(t);
        }
        const insertAll = (wps, ts) => {
            const out = wps.map(w => [...w]);
            for (const t of ts) {
                const { index } = cheapestInsertion(out, [t.lat, t.lon]);
                out.splice(index, 0, [t.lat, t.lon]);
            }
            return out;
        };
        const baseKm = pathKm(waypoints);
        const ranked = [...comps.entries()].map(([id, ts]) => {
            const cost = Math.max(0.05, pathKm(insertAll(waypoints, ts)) - baseKm);
            return { id, ts, value: ts.length / cost };
        }).sort((a, b) => b.value - a.value);

        let running = waypoints.map(w => [...w]);
        let used = 0;
        const chosen = new Set();
        for (const c of ranked) {
            if (used + c.ts.length > room) continue;
            const trial = insertAll(running, c.ts);
            if (pathKm(trial) * roadRatio > budgetKm) continue;
            running = trial;
            used += c.ts.length;
            chosen.add(c.id);
        }
        const batch = targets.filter(t => chosen.has(t.component));
        return { batch, skippedTiles: targets.length - batch.length };
    }

    // ── Waypoint ↔ route alignment ─────────────────────────────────

    /**
     * For each waypoint (in order), the index of the route coordinate it was
     * routed through — monotonic, first waypoint → 0, last → final index.
     * Used to place inserted waypoints on the correct leg.
     */
    function waypointRouteIndices(coords, waypoints) {
        const idx = [];
        let from = 0;
        for (let w = 0; w < waypoints.length; w++) {
            if (w === 0) { idx.push(0); continue; }
            if (w === waypoints.length - 1) { idx.push(coords.length - 1); continue; }
            let best = from, bestD = Infinity;
            for (let i = from; i < coords.length; i++) {
                const d = haversineKm(coords[i], waypoints[w]);
                if (d < bestD) { bestD = d; best = i; }
            }
            idx.push(best);
            from = best;
        }
        return idx;
    }

    /**
     * Insert pickups into a waypoint list at the leg the route actually
     * passes them on (by nearest route coordinate), preserving order along
     * the route. Returns {waypoints, meta} with meta entries for inserted
     * points marked {tiles: value, pickup: true}.
     */
    function insertPickups(coords, waypoints, meta, pickups) {
        const wpIdx = waypointRouteIndices(coords, waypoints);
        // Leg k runs from waypoint k to k+1; a pickup belongs to the last
        // waypoint whose route index is <= the pickup's line index.
        const proj = projector(coords[0][0]);
        const legOf = (p) => {
            let nearest = 0, bestD = Infinity;
            for (let i = 0; i < coords.length; i++) {
                const a = proj(coords[i]), b = proj([p.lat, p.lon]);
                const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
                if (d < bestD) { bestD = d; nearest = i; }
            }
            let leg = 0;
            for (let w = 0; w < wpIdx.length - 1; w++) if (wpIdx[w] <= nearest) leg = w;
            return { leg, at: nearest };
        };
        const placed = pickups.map(p => ({ p, ...legOf(p) }));
        placed.sort((a, b) => a.leg - b.leg || a.at - b.at);

        const outW = [waypoints[0]];
        const outM = [];
        let pi = 0;
        for (let w = 0; w < waypoints.length - 1; w++) {
            if (w > 0) { outW.push(waypoints[w]); outM.push(meta[w - 1]); }
            while (pi < placed.length && placed[pi].leg === w) {
                outW.push([placed[pi].p.lat, placed[pi].p.lon]);
                outM.push({ tiles: placed[pi].p.value, pickup: true });
                pi++;
            }
        }
        outW.push(waypoints[waypoints.length - 1]);
        return { waypoints: outW, meta: outM };
    }

    /**
     * Cheapest position (straight-line) to insert `pt` ([lat, lon]) into a
     * waypoint list whose first/last entries are fixed endpoints. Returns
     * {index, addedKm} where `index` is the splice position (1..length-1).
     */
    function cheapestInsertion(waypoints, pt) {
        let best = { index: 1, addedKm: Infinity };
        for (let i = 1; i < waypoints.length; i++) {
            const a = waypoints[i - 1], b = waypoints[i];
            const added = haversineKm(a, pt) + haversineKm(pt, b) - haversineKm(a, b);
            if (added < best.addedKm) best = { index: i, addedKm: added };
        }
        return best;
    }

    /**
     * Which inner waypoint to drop when a route is over its distance cap:
     * pure padding first, otherwise the one with the fewest tiles per km of
     * (straight-line) distance its removal saves. `meta[i]` describes
     * waypoints[i + 1]: {tiles?: number, padding?: boolean}.
     * Returns an index into `waypoints` (1..length-2), or -1 if none.
     */
    function chooseDropIndex(waypoints, meta) {
        if (waypoints.length <= 2) return -1;
        const pad = meta.findIndex(m => m && m.padding);
        if (pad !== -1) return pad + 1;
        let best = -1, bestRate = Infinity;
        for (let i = 1; i < waypoints.length - 1; i++) {
            const saved = haversineKm(waypoints[i - 1], waypoints[i]) + haversineKm(waypoints[i], waypoints[i + 1]) -
                haversineKm(waypoints[i - 1], waypoints[i + 1]);
            const tiles = (meta[i - 1] && typeof meta[i - 1].tiles === 'number') ? meta[i - 1].tiles : 1;
            const rate = tiles / Math.max(saved, 0.01);
            if (rate < bestRate) { bestRate = rate; best = i; }
        }
        return best;
    }

    // ── Retrace analysis ───────────────────────────────────────────

    /**
     * How much of a routed line rides the same road twice.
     *
     * The line is resampled every `stepM`; a sample counts as retraced when
     * another sample at least `minGapM` further along the route lies within
     * `nearM` of it (i.e. the route comes back over the same spot, not just
     * consecutive points). `fraction` is the share of route length on
     * retraced road — a pure out-and-back is ~1.0, a clean loop ~0.
     *
     * When `waypoints` are given, each retraced pair (i, j) is attributed to
     * the inner waypoint routed through between them that sits closest to
     * their midpoint — the tip of the spur — so the caller can try dropping
     * the waypoint responsible. `worstWaypoint` is that waypoint's index in
     * `waypoints` (or -1).
     */
    function analyzeRetrace(coords, waypoints = null, opts = {}) {
        // minGapM was 300, which missed any spur shorter than ~150 m each
        // way (both passes sat within the gap) — exactly the dead-end stubs
        // a mid-block waypoint produces. 100 still keeps ordinary corners
        // (samples either side of a turn are >25 m apart) from counting.
        const { stepM = 20, nearM = 25, minGapM = 100 } = opts;
        const result = { totalKm: 0, retracedKm: 0, fraction: 0, worstWaypoint: -1, byWaypoint: [] };
        if (!coords || coords.length < 2) return result;

        const proj = projector(coords[0][0]);
        const pts = densify(coords, stepM / 1000).map(d => ({ ...d, xy: proj(d.p) }));
        const total = pts[pts.length - 1].s;
        result.totalKm = total;
        const hash = buildHash(pts, nearM);
        const minGapKm = minGapM / 1000;

        const partner = new Array(pts.length).fill(-1);
        for (let i = 0; i < pts.length; i++) {
            let bestJ = -1, bestD = Infinity;
            for (const j of neighbours(hash, pts[i].xy, nearM, 1)) {
                if (Math.abs(pts[j].s - pts[i].s) < minGapKm) continue;
                const d = Math.hypot(pts[j].xy[0] - pts[i].xy[0], pts[j].xy[1] - pts[i].xy[1]);
                if (d <= nearM && d < bestD) { bestD = d; bestJ = j; }
            }
            partner[i] = bestJ;
        }

        let retraced = 0;
        for (let i = 1; i < pts.length; i++) {
            if (partner[i] !== -1) retraced += pts[i].s - pts[i - 1].s;
        }
        result.retracedKm = retraced;
        result.fraction = total > 0 ? retraced / total : 0;

        if (waypoints && waypoints.length > 2) {
            // Route-distance position of each waypoint.
            const wpIdx = waypointRouteIndices(coords, waypoints);
            const cum = [0];
            for (let i = 1; i < coords.length; i++) cum.push(cum[i - 1] + haversineKm(coords[i - 1], coords[i]));
            const wpS = wpIdx.map(i => cum[i]);
            const by = new Array(waypoints.length).fill(0);
            for (let i = 1; i < pts.length; i++) {
                const j = partner[i];
                if (j === -1) continue;
                const lo = Math.min(pts[i].s, pts[j].s), hi = Math.max(pts[i].s, pts[j].s);
                const mid = (lo + hi) / 2;
                let bestW = -1, bestD = Infinity;
                for (let w = 1; w < waypoints.length - 1; w++) {
                    if (wpS[w] <= lo || wpS[w] >= hi) continue;
                    const d = Math.abs(wpS[w] - mid);
                    if (d < bestD) { bestD = d; bestW = w; }
                }
                if (bestW !== -1) by[bestW] += pts[i].s - pts[i - 1].s;
            }
            result.byWaypoint = by;
            let worst = -1, worstKm = 0;
            for (let w = 1; w < by.length - 1; w++) {
                if (by[w] > worstKm) { worstKm = by[w]; worst = w; }
            }
            result.worstWaypoint = worst;
        }
        return result;
    }

    // ── Per-stop value check ───────────────────────────────────────

    /**
     * Inner waypoints whose detour claims nothing on its own.
     *
     * For each inner waypoint w, its span is the routed line from the
     * previous waypoint to the next one (the part that changes if w is
     * dropped). A new tile is *exclusive* to that span if the route touches
     * it only inside the span. Waypoints whose span has no exclusive new
     * tiles are returned (indices into \`waypoints\`): dropping one can't
     * lose a tile the rest of the route doesn't also claim — e.g. a stub
     * into a dead end that ended in already-claimed ground, or a stop whose
     * road snap missed its target tile. Stubs that do grab a fresh tile are
     * kept; those are cheap, legitimate tile collection.
     */
    function uselessStops(coords, waypoints, grids) {
        if (!coords || coords.length < 2 || !waypoints || waypoints.length < 3 || !grids || grids.length === 0) return [];
        const wpIdx = waypointRouteIndices(coords, waypoints);
        // Per new tile: first and last route segment that touches it.
        const range = new Map();
        for (const grid of grids) {
            const step = tileSideKm(grid.zoom, coords[0][0]) / 6;
            for (let i = 1; i < coords.length; i++) {
                for (const { p } of densify([coords[i - 1], coords[i]], step)) {
                    const { x, y } = latLonToTile(p[0], p[1], grid.zoom);
                    const k = `${x},${y}`;
                    if (grid.visited.has(k) || grid.isRoadless(x, y)) continue;
                    const key = `${grid.zoom}:${k}`;
                    const r = range.get(key);
                    if (!r) range.set(key, [i, i]);
                    else { if (i < r[0]) r[0] = i; if (i > r[1]) r[1] = i; }
                }
            }
        }
        const out = [];
        for (let w = 1; w < waypoints.length - 1; w++) {
            // Segment i joins coords[i-1]→coords[i]; the span covers
            // segments (wpIdx[w-1], wpIdx[w+1]].
            const lo = wpIdx[w - 1], hi = wpIdx[w + 1];
            let exclusive = 0;
            for (const [first, last] of range.values()) {
                if (first > lo && last <= hi) { exclusive++; break; }
            }
            if (exclusive === 0) out.push(w);
        }
        return out;
    }

    // ── Spurs: out-and-back excursions ─────────────────────────────

    /**
     * Find the route's spurs: stretches where it rides out along a road and
     * comes straight back along it (a dead-end stub, or a "lollipop": out a
     * stem, around a loop, back down the stem). The router only does this to
     * reach a waypoint, so every spur has one or more waypoints inside it.
     *
     * Each spur is {fromKm, toKm, stemKm, waypoints, exclusiveTiles}. It
     * covers route distance [fromKm, toKm]. stemKm is the length of road ridden
     * both ways. waypoints holds indices into `waypoints` of the inner stops
     * routed through inside it. exclusiveTiles counts new tiles the route
     * touches only inside the spur (0 means the excursion claims nothing the
     * rest of the route doesn't, so it's pure overhead). Unlike uselessStops,
     * this judges the excursion itself, not the whole leg between the stop's
     * neighbours, which usually claims something legitimately.
     *
     * Nested spurs are all reported: a lollipop can contain a stub of its own.
     */
    function findSpurs(coords, waypoints, grids, opts = {}) {
        return spurAnalysis(coords, waypoints, grids, opts).spurs;
    }

    function spurAnalysis(coords, waypoints, grids, opts = {}) {
        const { stepM = 20, nearM = 25, minGapM = 60, minStemM = 30, maxLoopM = 1200 } = opts;
        if (!coords || coords.length < 2) return { spurs: [], hits: new Map() };
        const proj = projector(coords[0][0]);
        const pts = densify(coords, stepM / 1000).map(d => ({ ...d, xy: proj(d.p) }));
        const hash = buildHash(pts, nearM);
        const minGapKm = minGapM / 1000;

        // Forward partner: the closest later sample on the same road, far
        // enough along the route that it isn't just the next sample.
        const partner = new Array(pts.length).fill(-1);
        for (let i = 0; i < pts.length; i++) {
            let bestJ = -1, bestD = Infinity;
            for (const j of neighbours(hash, pts[i].xy, nearM, 1)) {
                if (j <= i || pts[j].s - pts[i].s < minGapKm) continue;
                const d = Math.hypot(pts[j].xy[0] - pts[i].xy[0], pts[j].xy[1] - pts[i].xy[1]);
                if (d <= nearM && d < bestD) { bestD = d; bestJ = j; }
            }
            partner[i] = bestJ;
        }

        // Antiparallel runs: as i walks out the stem, its partner walks back
        // down it (j decreasing). The run's first pair bounds the spur.
        const runs = [];
        let run = null;
        for (let i = 0; i < pts.length; i++) {
            const j = partner[i];
            if (j === -1) continue;
            if (run && i - run.i1 <= 2 && j <= run.j1 + 2 && j >= run.j1 - 6) {
                run.i1 = i; run.j1 = j;
            } else {
                if (run) runs.push(run);
                run = { i0: i, j0: j, i1: i, j1: j };
            }
        }
        if (run) runs.push(run);

        // Route distance of each waypoint, for attribution.
        let wpS = [];
        if (waypoints && waypoints.length > 2) {
            const wpIdx = waypointRouteIndices(coords, waypoints);
            const cum = [0];
            for (let i = 1; i < coords.length; i++) cum.push(cum[i - 1] + haversineKm(coords[i - 1], coords[i]));
            wpS = wpIdx.map(i => cum[i]);
        }

        // Samples touching each new tile, in route order.
        const hits = new Map();
        for (const grid of grids || []) {
            pts.forEach(({ p }, i) => {
                const { x, y } = latLonToTile(p[0], p[1], grid.zoom);
                const k = `${x},${y}`;
                if (grid.visited.has(k) || grid.isRoadless(x, y)) return;
                const key = `${grid.zoom}:${k}`;
                const h = hits.get(key);
                if (!h) hits.set(key, [i]);
                else h.push(i);
            });
        }

        const spurs = [];
        for (const r of runs) {
            if (r.j1 < r.i1) continue;
            const stemKm = pts[r.i1].s - pts[r.i0].s;
            if (stemKm * 1000 < minStemM) continue;
            // A road the route happens to reuse much later is not a spur.
            if ((pts[r.j1].s - pts[r.i1].s) * 1000 > maxLoopM) continue;
            const a = r.i0, b = r.j0;
            const fromKm = pts[a].s, toKm = pts[b].s;
            const wps = [];
            for (let w = 1; w < wpS.length - 1; w++) {
                if (wpS[w] > fromKm && wpS[w] < toKm) wps.push(w);
            }
            let exclusiveTiles = 0;
            for (const h of hits.values()) {
                if (h[0] >= a && h[h.length - 1] <= b) exclusiveTiles++;
            }
            spurs.push({ fromKm, toKm, stemKm, waypoints: wps, exclusiveTiles, a, b, base: pts[a].p });
        }
        return { spurs, hits };
    }

    /**
     * Which spurs to cut off, and where to anchor the route instead.
     *
     * Picks wasted spurs (they claim no tile exclusively and contain stops),
     * longest first, but only while every new tile they touch is still
     * touched somewhere outside all the spurs picked so far. Two spurs that
     * share a tile can each look non-exclusive, and cutting both would lose
     * it. Returns [{waypoints, base}]: replace the spur's stops with one
     * waypoint at `base` (where the spur leaves the route) so the rest of
     * the leg is routed as before and only the excursion disappears.
     */
    function planSpurPrune(coords, waypoints, grids, opts = {}) {
        const { spurs, hits } = spurAnalysis(coords, waypoints, grids, opts);
        const cands = spurs
            .filter(sp => sp.exclusiveTiles === 0 && sp.waypoints.length > 0)
            .sort((p, q) => (q.b - q.a) - (p.b - p.a));
        const chosen = [];
        const covered = (i, extra) => (i >= extra.a && i <= extra.b) || chosen.some(c => i >= c.a && i <= c.b);
        for (const c of cands) {
            if (chosen.some(o => c.a <= o.b && c.b >= o.a)) continue; // overlaps (or nests in) a pick
            let safe = true;
            for (const h of hits.values()) {
                if (!h.some(i => i >= c.a && i <= c.b)) continue;
                if (h.every(i => covered(i, c))) { safe = false; break; }
            }
            if (safe) chosen.push(c);
        }
        return chosen.map(c => ({ waypoints: c.waypoints, base: c.base }));
    }

    /** Apply planSpurPrune's result: each spur's stops become one anchor at its base. */
    function applySpurPrune(waypoints, meta, plan) {
        const replace = new Map(), remove = new Set();
        for (const { waypoints: ws, base } of plan) {
            replace.set(ws[0], base);
            ws.slice(1).forEach(w => remove.add(w));
        }
        const outW = [], outM = [];
        waypoints.forEach((wp, i) => {
            if (remove.has(i)) return;
            const inner = i > 0 && i < waypoints.length - 1;
            if (replace.has(i)) {
                outW.push([...replace.get(i)]);
                if (inner) outM.push({ tiles: 0, anchor: true });
                return;
            }
            outW.push(wp);
            if (inner) outM.push(meta[i - 1]);
        });
        return { waypoints: outW, meta: outM };
    }

    // ── Bounds (box or polygon) ────────────────────────────────────

    /** True when `area` is a polygon ([[lat, lon], ...]) rather than a box. */
    function isPolygonArea(area) {
        return Array.isArray(area) && Array.isArray(area[0]);
    }

    /** Box [south, west, north, east] enclosing a box or polygon area. */
    function areaBBox(area) {
        if (!isPolygonArea(area)) return area;
        let s = Infinity, w = Infinity, n = -Infinity, e = -Infinity;
        for (const [lat, lon] of area) {
            if (lat < s) s = lat;
            if (lat > n) n = lat;
            if (lon < w) w = lon;
            if (lon > e) e = lon;
        }
        return [s, w, n, e];
    }

    function pointInPolygon(p, poly) {
        const [lat, lon] = p;
        let inside = false;
        for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
            const [yi, xi] = poly[i];
            const [yj, xj] = poly[j];
            if ((yi > lat) !== (yj > lat) && lon < xi + (lat - yi) * (xj - xi) / (yj - yi)) {
                inside = !inside;
            }
        }
        return inside;
    }

    function pointInBounds(p, bounds) {
        if (isPolygonArea(bounds)) return pointInPolygon(p, bounds);
        const [south, west, north, east] = bounds;
        return p[0] >= south && p[0] <= north && p[1] >= west && p[1] <= east;
    }

    /** Nearest point on a polygon's boundary to `p`, and the distance in metres. */
    function nearestOnPolygonEdge(p, poly) {
        const mLon = M_PER_DEG_LAT * Math.cos(p[0] * Math.PI / 180);
        let best = { d: Infinity, pt: poly[0] };
        for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
            // Local metres relative to p.
            const ax = (poly[j][1] - p[1]) * mLon, ay = (poly[j][0] - p[0]) * M_PER_DEG_LAT;
            const bx = (poly[i][1] - p[1]) * mLon, by = (poly[i][0] - p[0]) * M_PER_DEG_LAT;
            const dx = bx - ax, dy = by - ay;
            const len2 = dx * dx + dy * dy;
            const t = len2 > 0 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2)) : 0;
            const cx = ax + t * dx, cy = ay + t * dy;
            const d = Math.hypot(cx, cy);
            if (d < best.d) best = { d, pt: [p[0] + cy / M_PER_DEG_LAT, p[1] + cx / mLon] };
        }
        return best;
    }

    /**
     * Share of route length more than `toleranceM` outside `bounds` (box or
     * polygon). The tolerance absorbs a road running along the area's edge.
     */
    function fractionOutsideBounds(coords, bounds, toleranceM = 60) {
        if (!coords || coords.length < 2 || !bounds) return 0;
        let isOutside;
        if (isPolygonArea(bounds)) {
            isOutside = (p) => !pointInPolygon(p, bounds) && nearestOnPolygonEdge(p, bounds).d > toleranceM;
        } else {
            const [south, west, north, east] = bounds;
            const dLat = toleranceM / M_PER_DEG_LAT;
            const dLon = toleranceM / (M_PER_DEG_LAT * Math.cos(((south + north) / 2) * Math.PI / 180));
            const padded = [south - dLat, west - dLon, north + dLat, east + dLon];
            isOutside = (p) => !pointInBounds(p, padded);
        }
        const pts = densify(coords, 0.05);
        let outside = 0;
        for (let i = 1; i < pts.length; i++) {
            if (isOutside(pts[i].p)) outside += pts[i].s - pts[i - 1].s;
        }
        const total = pts[pts.length - 1].s;
        return total > 0 ? outside / total : 0;
    }

    /** Clamp a point into bounds (used for any padding point). For a
     *  polygon, an outside point moves to the nearest spot on its edge. */
    function clampToBounds(p, bounds) {
        if (isPolygonArea(bounds)) {
            return pointInPolygon(p, bounds) ? p : nearestOnPolygonEdge(p, bounds).pt;
        }
        const [south, west, north, east] = bounds;
        return [Math.min(Math.max(p[0], south), north), Math.min(Math.max(p[1], west), east)];
    }

    /** True when any two non-adjacent edges of a polygon cross. */
    function polygonSelfIntersects(poly) {
        const n = poly.length;
        const orient = (a, b, c) => Math.sign((b[1] - a[1]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[1] - a[1]));
        for (let i = 0; i < n; i++) {
            const a = poly[i], b = poly[(i + 1) % n];
            for (let j = i + 1; j < n; j++) {
                if (j === i || (j + 1) % n === i || j === (i + 1) % n) continue;
                const c = poly[j], d = poly[(j + 1) % n];
                if (orient(a, b, c) * orient(a, b, d) < 0 && orient(c, d, a) * orient(c, d, b) < 0) return true;
            }
        }
        return false;
    }

    /**
     * Squadrats "yard": the largest 4-connected group of collected tiles in
     * which every tile has all four N/E/S/W neighbours collected (diagonals
     * don't matter). `visited` is the coverage grid's `visited` map, keyed
     * "x,y". Returns a Set of "x,y" keys, empty when no tile qualifies; on a
     * tie the first group found wins. Only a fallback now: the server sends
     * the full-history yard as `coverage.yard` (find_yard in
     * src/coverage_tracker.py). Run on bbox-bounded coverage, a yard running
     * past the loaded area's edge comes out smaller than it is, because
     * neighbours outside that area look uncollected.
     */
    function findYard(visited) {
        const yard = new Set();
        if (!visited || typeof visited !== 'object') return yard;
        const has = (x, y) => Object.prototype.hasOwnProperty.call(visited, x + ',' + y);
        const interior = new Set();
        for (const key of Object.keys(visited)) {
            const [x, y] = key.split(',').map(Number);
            if (has(x + 1, y) && has(x - 1, y) && has(x, y + 1) && has(x, y - 1)) interior.add(x + ',' + y);
        }
        const seen = new Set();
        let best = [];
        for (const start of interior) {
            if (seen.has(start)) continue;
            seen.add(start);
            const group = [start];
            for (let i = 0; i < group.length; i++) {
                const [x, y] = group[i].split(',').map(Number);
                for (const k of [(x + 1) + ',' + y, (x - 1) + ',' + y, x + ',' + (y + 1), x + ',' + (y - 1)]) {
                    if (interior.has(k) && !seen.has(k)) { seen.add(k); group.push(k); }
                }
            }
            if (group.length > best.length) best = group;
        }
        for (const k of best) yard.add(k);
        return yard;
    }

    /**
     * Outline of a set of tiles: every tile edge that borders a tile outside
     * the set, as [[lat, lon], [lat, lon]] segments (fits one multi-segment
     * L.polyline). Drawing a yard as fill plus this outline keeps grid lines
     * out of its interior, so it reads as one region.
     */
    function tileSetOutline(tileKeys, zoom) {
        const segs = [];
        const n = Math.pow(2, zoom);
        const lon = x => x / n * 360 - 180;
        const lat = y => Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI;
        for (const key of tileKeys) {
            const [x, y] = key.split(',').map(Number);
            const w = lon(x), e = lon(x + 1), no = lat(y), so = lat(y + 1);
            if (!tileKeys.has(x + ',' + (y - 1))) segs.push([[no, w], [no, e]]);
            if (!tileKeys.has(x + ',' + (y + 1))) segs.push([[so, w], [so, e]]);
            if (!tileKeys.has((x - 1) + ',' + y)) segs.push([[so, w], [no, w]]);
            if (!tileKeys.has((x + 1) + ',' + y)) segs.push([[so, e], [no, e]]);
        }
        return segs;
    }

    const api = {
        haversineKm, pathKm, latLonToTile, tileBounds, tileSideKm, buildRoadlessLookup, makeGrid,
        densify, tilesTouched, newTilesCrossed, countNewTiles,
        findPickups, findRowPickups, clusterSweepTargets, budgetSweepBatch, insertSweepTargets, waypointRouteIndices, insertPickups, cheapestInsertion, chooseDropIndex,
        analyzeRetrace, uselessStops, findSpurs, planSpurPrune, applySpurPrune, pointInBounds, fractionOutsideBounds, clampToBounds,
        isPolygonArea, areaBBox, pointInPolygon, polygonSelfIntersects,
        findYard, tileSetOutline,
    };
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.ExploreRefine = api;
})(typeof self !== 'undefined' ? self : this);
