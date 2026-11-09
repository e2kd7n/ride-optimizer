// End-to-end Explore run against the real app (via ssh tunnel on :18083):
// real coverage, real water exclusion, real ORS routing through the app's
// own /api/exploration/route. Runs Phase 1 (worker) + Phase 2 (refineRoute)
// from a given code directory and prints independent metrics.
//
// usage:
//   ssh -N -L 18083:127.0.0.1:18083 admin@pi4        # tunnel to the app (separate shell)
//   node scripts/explore_benchmark/e2e.js <codeDir> [label] [direction|""] ['{"refineRouteOpt":...}']
//   codeDir holds explore.js, explore-refine.js, exploration-worker.js — e.g. "$(pwd)/static/js",
//   or a folder of files from `git show origin/main:static/js/<file>` for a baseline.
//   Env: SCENARIO=loop (default) | ptp; E2E_OUT=<dir> for the e2e-<label>.json route dump.
// Uses real ORS calls through the app (~10 per run; the backend memoizes repeats).
// Lake Michigan is approximated by a shoreline polyline (SHORE below) so the
// run doesn't depend on the Overpass water lookup.
// "spurs" are out-and-back stubs/lollipops (ExploreRefine.findSpurs); "wasted"
// ones claim no tile the rest of the route doesn't.
//
// Baseline 2026-11-08 (deployed 90a6974): km=98.2 newTiles=109 turns=278 uturns=27 clusterTilesLeft=11
//   spurs=64 wastedSpurs=42 (11.9 km); ptp: km=85.2 newTiles=96 uturns=20 wastedSpurs=31 (7.8 km).
// With pigtail cut (refineRoute stage 6): km=87.3 newTiles=109 turns=228 uturns=16 clusterTilesLeft=10
//   wastedSpurs=4 (0.5 km); ptp: km=79.0 newTiles=96 uturns=11 wastedSpurs=4 (0.8 km).
// See plans/own-router/ARCHITECTURE.md §6 — this is the seed of scripts/explore_benchmark/.
const fs = require('fs'), path = require('path'), vm = require('vm');
const codeDir = path.resolve(process.argv[2]);
const label = process.argv[3] || path.basename(codeDir);
const BASE = 'http://localhost:18083/api';

// Default scenario: Edgewater start, drawn box over Skokie/Lincolnwood/West
// Ridge, 150 min at 16 mph, Loop, Fill gaps, z17. SCENARIO=ptp switches to
// a wild point-to-point (West Ridge -> Rosehill) over the same area, like the
// 2026-11-08 pigtail screenshot.
const SCENARIOS = {
    loop: { start: { lat: 41.9880, lon: -87.6630 }, end: null, area: [41.983, -87.765, 42.062, -87.655], km: 40 * 1.609344 },
    ptp: { start: { lat: 41.9985, lon: -87.6930 }, end: { lat: 41.9875, lon: -87.6925 }, area: [41.975, -87.775, 42.050, -87.665], km: 35 * 1.609344 },
};
const SC = SCENARIOS[process.env.SCENARIO || 'loop'];
const START = SC.start, END = SC.end;
const AREA = SC.area;                                      // [S, W, N, E]
const TARGET_KM = SC.km;
const ZOOM = 17;

// ── tiny API client with cookie + CSRF ──
let cookie = '', csrf = null;
async function api(pathname, opts = {}) {
    if (!csrf) {
        const r = await fetch(`${BASE}/csrf-token`);
        cookie = (r.headers.getSetCookie?.() || []).map(c => c.split(';')[0]).join('; ');
        csrf = (await r.json()).csrf_token;
    }
    const r = await fetch(`${BASE}${pathname}`, {
        ...opts,
        headers: { 'Content-Type': 'application/json', Cookie: cookie, 'X-CSRFToken': csrf, ...(opts.headers || {}) },
    });
    const body = await r.json().catch(() => ({}));
    return body;
}
let routeCalls = 0;
const client = {
    async getExplorationRoute({ waypoints, surfacePreference = 'any', exclude, bounds }) {
        routeCalls++;
        const body = { waypoints, surface_preference: surfacePreference };
        if (exclude) body.exclude = exclude;
        if (bounds) body.bounds = bounds;
        return api('/exploration/route', { method: 'POST', body: JSON.stringify(body) });
    },
};

// ── independent metrics ──
const R0 = require(path.join(__dirname, '..', '..', 'static', 'js', 'explore-refine.js'));   // tile math only
function hav(a, b) {
    const dLat = (b[0] - a[0]) * Math.PI / 180, dLon = (b[1] - a[1]) * Math.PI / 180;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    return 2 * 6371000 * Math.asin(Math.sqrt(h));
}
function bearing(a, b) {
    const y = Math.sin((b[1] - a[1]) * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180);
    const x = Math.cos(a[0] * Math.PI / 180) * Math.sin(b[0] * Math.PI / 180) -
        Math.sin(a[0] * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180) * Math.cos((b[1] - a[1]) * Math.PI / 180);
    return Math.atan2(y, x) * 180 / Math.PI;
}
/** Turns in a road polyline: resample to ~25 m, heading change between 40 m legs. */
function turnStats(coords) {
    const pts = [coords[0]];
    let acc = 0;
    for (let i = 1; i < coords.length; i++) {
        acc += hav(coords[i - 1], coords[i]);
        if (acc >= 25) { pts.push(coords[i]); acc = 0; }
    }
    pts.push(coords[coords.length - 1]);
    let turns = 0, uturns = 0, lastTurnIdx = -10;
    for (let i = 2; i < pts.length - 2; i++) {
        const h1 = bearing(pts[i - 2], pts[i]), h2 = bearing(pts[i], pts[i + 2]);
        let d = Math.abs(h2 - h1); if (d > 180) d = 360 - d;
        if (d >= 60 && i - lastTurnIdx > 2) { turns++; if (d >= 150) uturns++; lastTurnIdx = i; }
    }
    return { turns, uturns };
}
function sweepLeft(coords, grid) {
    // Independent re-implementation of the cluster rule check.
    const crossed = R0.tilesTouched(coords, ZOOM);
    const unclaimed = (x, y) => {
        if (grid.visited.has(`${x},${y}`) || grid.isRoadless(x, y)) return false;
        const tb = R0.tileBounds(x, y, ZOOM), c = [(tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2];
        return c[0] >= AREA[0] && c[0] <= AREA[2] && c[1] >= AREA[1] && c[1] <= AREA[3];
    };
    const N4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    const left = new Set();
    for (const k of crossed) {
        const [cx, cy] = k.split(',').map(Number);
        for (const [dx, dy] of N4) {
            const x = cx + dx, y = cy + dy;
            if (crossed.has(`${x},${y}`) || !unclaimed(x, y)) continue;
            if (N4.some(([ax, ay]) => unclaimed(x + ax, y + ay))) left.add(`${x},${y}`);
        }
    }
    return left.size;
}

(async () => {
    // Coverage + water for a box padded around the area.
    const pad = 0.03;
    const cb = { south: AREA[0] - pad, west: AREA[1] - pad, north: AREA[2] + pad, east: AREA[3] + pad };
    const cov = await api(`/exploration/tiles?south=${cb.south}&west=${cb.west}&north=${cb.north}&east=${cb.east}&zoom=${ZOOM}`);
    if (cov.status !== 'success') { console.error('coverage failed', cov); process.exit(1); }
    // The Pi's water lookup for this cell is currently broken (legacy-format
    // cache + Overpass timeouts), so approximate Lake Michigan: every tile
    // east of this shoreline polyline is water.
    const SHORE = [[41.97, -87.650], [41.99, -87.653], [42.005, -87.662], [42.02, -87.666], [42.04, -87.671], [42.06, -87.675], [42.10, -87.680]];
    const shoreLon = (lat) => {
        for (let i = 1; i < SHORE.length; i++) {
            if (lat <= SHORE[i][0]) {
                const [la, lo] = SHORE[i - 1], [lb, lob] = SHORE[i];
                return lo + (lob - lo) * (lat - la) / (lb - la);
            }
        }
        return SHORE[SHORE.length - 1][1];
    };
    const n = 2 ** ZOOM;
    const tx = lon => Math.floor((lon + 180) / 360 * n);
    const ty = lat => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    const runs = [];
    for (let y = ty(cb.north); y <= ty(cb.south); y++) {
        const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 0.5) / n))) * 180 / Math.PI;
        runs.push([y, tx(shoreLon(lat)) + 1, tx(cb.east) + 5]);
    }
    cov.roadless_runs = runs;
    cov.zoom = ZOOM;
    if (!cov.bounds) cov.bounds = [cb.south, cb.west, cb.north, cb.east];

    // Phase 1
    const posted = [];
    const wctx = { self: { postMessage: m => posted.push(m) }, Math, Map, Set, Object, Array, Number, Error };
    vm.createContext(wctx);
    vm.runInContext(fs.readFileSync(path.join(codeDir, 'exploration-worker.js'), 'utf8') + '\n;this.__opt = optimize;', wctx);
    wctx.__opt({ start: START, end: END, distanceKm: TARGET_KM, mode: 'tiles',
        routeType: END ? 'point_to_point' : 'round_trip', shape: END ? 'point_to_point' : 'loop', ptpWild: !!END,
        coverageData: cov, optimizeFor: 'infill', areaBounds: AREA, windDirectionDeg: null, windSpeedKph: null });
    const routes = posted.filter(m => m.type === 'route');
    const dirArg = process.argv[4];
    const pick = dirArg ? routes.find(m => m.route.direction === dirArg)
        : routes.reduce((b, m) => (!b || m.route.stats.unvisited > b.route.stats.unvisited ? m : b), null);
    if (!pick) { console.error('no phase-1 routes', posted.filter(m => m.type !== 'route')); process.exit(1); }

    // Phase 2
    const R = require(path.join(codeDir, 'explore-refine.js'));
    const stub = new Proxy(function () {}, { get: (t, k) => (k === Symbol.toPrimitive ? () => '' : stub), apply: () => stub, construct: () => stub });
    const ctx = { window: { ExploreRefine: R, debounce: f => f }, document: { addEventListener() {}, getElementById: () => stub },
        L: stub, APIClient: function () { return client; }, Math, Map, Set, Object, Array, Number, Error, Promise, console };
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(path.join(codeDir, 'explore.js'), 'utf8') + '\n;this.__refine = refineRoute;', ctx);
    const grid = R.makeGrid(cov);
    const fin = END || START;
    const base = [[START.lat, START.lon], ...pick.route.waypoints.map(w => [w.lat, w.lon]), [fin.lat, fin.lon]];
    const t0 = Date.now();
    const out = await ctx.__refine(base, {
        targetKm: TARGET_KM, mode: END ? 'match' : 'cap', surfacePref: 'any', candidates: posted.find(m => m === pick).candidates || [],
        dirBearing: 45, roadFilters: {}, fenceBounds: AREA, areaBounds: AREA,
        baseMeta: pick.route.waypoints.map(w => ({ tiles: w.tiles || 1 })), grids: [grid], allowRetrace: false,
        ...(process.argv[5] ? JSON.parse(process.argv[5]) : {}),
    });
    if (!out.route) { console.error('refine failed', out.message); process.exit(1); }
    const coords = out.route.coordinates;
    const tiles = R0.countNewTiles(coords, [{ zoom: ZOOM, visited: grid.visited, isRoadless: grid.isRoadless }]);
    const km = out.route.distance_km;
    const { turns, uturns } = turnStats(coords);
    // Spurs (out-and-back stubs / lollipops), outermost only. "Wasted" means
    // the spur claims no new tile the rest of the route doesn't.
    const all = R0.findSpurs(coords, null, [{ zoom: ZOOM, visited: grid.visited, isRoadless: grid.isRoadless }]);
    const outer = all.filter(s => !all.some(o => o !== s && o.fromKm <= s.fromKm && o.toKm >= s.toKm &&
        (o.toKm - o.fromKm) > (s.toKm - s.fromKm)));
    const wasted = outer.filter(s => s.exclusiveTiles === 0);
    const wastedKm = wasted.reduce((t, s) => t + s.toKm - s.fromKm, 0);
    const outDir = process.env.E2E_OUT || __dirname;
    fs.writeFileSync(path.join(outDir, `e2e-${label}.json`), JSON.stringify({ coords, stats: out.stats, spurs: outer }));
    console.log(`${label} [${pick.route.direction}] km=${km.toFixed(1)} newTiles=${tiles} tiles/km=${(tiles / km).toFixed(2)} ` +
        `turns=${turns} (${(turns / km).toFixed(2)}/km) uturns=${uturns} clusterTilesLeft=${sweepLeft(coords, grid)} ` +
        `spurs=${outer.length} wastedSpurs=${wasted.length} (${wastedKm.toFixed(1)} km) ` +
        `orsRequests=${routeCalls} ${((Date.now() - t0) / 1000).toFixed(0)}s stats=${JSON.stringify(out.stats)}`);
})();
