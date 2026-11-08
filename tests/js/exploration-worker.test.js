// Unit tests for static/js/exploration-worker.js (Explore Phase 1 tour builder).
// The worker is a plain script written for a Web Worker scope, so it's
// evaluated in a vm context with a stub `self` and its functions read back.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadWorker() {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', 'static', 'js', 'exploration-worker.js'), 'utf8');
    const posted = [];
    const ctx = { self: { postMessage: (m) => posted.push(m) }, Math, Map, Set, Object, Array, Number, Error };
    vm.createContext(ctx);
    vm.runInContext(src + '\n;this.__w = { constructInsertionTour, optimize, minTilesPerKm, MAX_TOUR_STOPS, ROAD_DETOUR_FACTOR };', ctx);
    return { ...ctx.__w, posted };
}

const LAT0 = 41.99, LON0 = -87.70;
const KM_LAT = 1 / 111.32;
const KM_LON = 1 / (111.32 * Math.cos(LAT0 * Math.PI / 180));
const at = (east, north) => ({ lat: LAT0 + north * KM_LAT, lon: LON0 + east * KM_LON });
const start = at(0, 0);

/** A tour candidate: `tiles` tiles, waypoint at (east, north) km. */
function cand(east, north, tiles, zoom = 17) {
    const point = at(east, north);
    return {
        tiles: Array.from({ length: tiles }, (_, i) => ({ key: `${east},${north},${i}` })),
        point, centroid: point, zoom,
        distanceFromStart: Math.hypot(east, north),
    };
}

test('tour no longer starts from the farthest pocket', () => {
    const w = loadWorker();
    const far = cand(9, 0, 1);       // lone tile 9 km out — 18 km round trip for 1 tile
    const near = [cand(1, 0, 4), cand(1, 1, 4), cand(0, 1, 4)];
    const tour = w.constructInsertionTour(start, null, [far, ...near], 40, 'infill', new Map());
    assert.ok(!tour.includes(far), 'far single-tile pocket is not in the tour');
    assert.equal(tour.length, 3);
});

test('over-budget candidates are skipped, not a reason to stop', () => {
    const w = loadWorker();
    const huge = cand(20, 0, 200);   // great value but far beyond a 10 km budget
    const small = cand(0.5, 0.5, 3);
    const tour = w.constructInsertionTour(start, null, [huge, small], 10, 'tiles', new Map());
    // (Array comes from the vm realm, so compare by length + identity.)
    assert.equal(tour.length, 1);
    assert.equal(tour[0], small);
});

test('yield floor scales with tile size', () => {
    const w = loadWorker();
    // 1 tile, 3 km out (6 km detour): fine for a squadrat, not a squadratinho.
    assert.equal(w.constructInsertionTour(start, null, [cand(3, 0, 1, 14)], 40, 'tiles', new Map()).length, 1);
    assert.equal(w.constructInsertionTour(start, null, [cand(3, 0, 1, 17)], 40, 'tiles', new Map()).length, 0);
    assert.ok(w.minTilesPerKm(17, LAT0) > 5 * w.minTilesPerKm(14, LAT0));
});

test('tour stays within the stop cap and the straight-line budget', () => {
    const w = loadWorker();
    const cands = [];
    for (let i = 0; i < 80; i++) cands.push(cand((i % 9) * 0.6 - 2.4, Math.floor(i / 9) * 0.6 - 2.4, 6));
    const tour = w.constructInsertionTour(start, null, cands, 60, 'tiles', new Map());
    assert.ok(tour.length <= w.MAX_TOUR_STOPS);
    let km = 0, prev = start;
    const hav = (a, b) => {
        const dLat = (b.lat - a.lat) * Math.PI / 180, dLon = (b.lon - a.lon) * Math.PI / 180;
        const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
        return 2 * 6371 * Math.asin(Math.sqrt(h));
    };
    for (const z of tour) { km += hav(prev, z.point); prev = z.point; }
    km += hav(prev, start);
    assert.ok(km <= 60 * 1.15 / w.ROAD_DETOUR_FACTOR + 1e-9, `tour ${km} km`);
});

test('a big unclaimed block becomes several stops, not one corner tag', () => {
    const w = loadWorker();
    const zoom = 17, n = 2 ** zoom;
    const tileX = (lon) => Math.floor((lon + 180) / 360 * n);
    const tileY = (lat) => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    const sw = at(-4, -4), ne = at(4, 4);
    const visited = {};
    for (let x = tileX(sw.lon); x <= tileX(ne.lon); x++) {
        for (let y = tileY(ne.lat); y <= tileY(sw.lat); y++) visited[`${x},${y}`] = 1;
    }
    // One 6x5-tile unclaimed block ~2 km NE of start.
    const b = at(1.5, 1.5);
    const blockKeys = new Set();
    for (let dx = 0; dx < 6; dx++) for (let dy = 0; dy < 5; dy++) {
        const k = `${tileX(b.lon) + dx},${tileY(b.lat) + dy}`;
        delete visited[k];
        blockKeys.add(k);
    }
    w.optimize({
        start, end: null, distanceKm: 30, mode: 'tiles', routeType: 'round_trip', shape: 'loop',
        coverageData: { visited, bounds: [sw.lat, sw.lon, ne.lat, ne.lon], zoom },
        optimizeFor: 'tiles', areaBounds: null,
    });
    const route = w.posted.filter(m => m.type === 'route').find(m => m.route.direction === 'NE' || m.route.direction === 'NW');
    assert.ok(route, 'a route toward the block');
    const inBlock = route.route.waypoints.filter(p => blockKeys.has(`${tileX(p.lon)},${tileY(p.lat)}`)
        || blockKeys.has(`${tileX(p.lon) - 1},${tileY(p.lat)}`) || blockKeys.has(`${tileX(p.lon)},${tileY(p.lat) - 1}`));
    assert.ok(inBlock.length >= 3, `stops in block: ${inBlock.length}`);
});

test('dense home area: distant clusters of small pockets still yield real tours, never empty ones', () => {
    // Regression: with stop-sized pockets judged one at a time, everything
    // within ~4 km claimed + clusters 5-9 km out produced 0-stop "routes"
    // (0.0 mi after road routing).
    const zoom = 17, n = 2 ** zoom;
    const tileX = (lon) => Math.floor((lon + 180) / 360 * n);
    const tileY = (lat) => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    const sw = at(-12, -12), ne = at(12, 12);
    const build = (clusters) => {
        const visited = {};
        for (let x = tileX(sw.lon); x <= tileX(ne.lon); x++) {
            for (let y = tileY(ne.lat); y <= tileY(sw.lat); y++) visited[`${x},${y}`] = 1;
        }
        let s = 3; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
        for (const [cx, cy, holes] of clusters) {
            for (let i = 0; i < holes; i++) {
                const p = at(cx + rnd() - 0.5, cy + rnd() - 0.5);
                delete visited[`${tileX(p.lon)},${tileY(p.lat)}`];
            }
        }
        return visited;
    };
    const run = (visited) => {
        const w = loadWorker();
        w.optimize({
            start, end: null, distanceKm: 64, mode: 'tiles', routeType: 'round_trip', shape: 'loop',
            coverageData: { visited, bounds: [sw.lat, sw.lon, ne.lat, ne.lon], zoom },
            optimizeFor: 'infill', areaBounds: null,
        });
        return w.posted.filter(m => m.type === 'route');
    };

    const withClusters = run(build([[6, 6, 25], [-7, 5, 25], [6, -7, 25], [-6, -6, 25]]));
    assert.ok(withClusters.length >= 1, 'found tours');
    for (const m of withClusters) assert.ok(m.route.waypoints.length >= 3, `${m.route.direction}: ${m.route.waypoints.length} stops`);

    // Only a couple of lone holes far out: nothing worth the ride — no routes,
    // rather than empty ones.
    const lone = run(build([[8, 8, 1], [-9, -8, 1]]));
    for (const m of lone) assert.ok(m.route.waypoints.length >= 1, 'no empty routes');
});

test('optimize: posts routes whose waypoints carry tile counts', () => {
    const w = loadWorker();
    const zoom = 17, n = 2 ** zoom;
    const tileX = (lon) => Math.floor((lon + 180) / 360 * n);
    const tileY = (lat) => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    const sw = at(-3, -3), ne = at(3, 3);
    const visited = {};
    for (let x = tileX(sw.lon); x <= tileX(ne.lon); x++) {
        for (let y = tileY(ne.lat); y <= tileY(sw.lat); y++) visited[`${x},${y}`] = 1;
    }
    // Unclaimed 2x2 pockets in each quadrant, ~1.5 km out.
    for (const [e, nn] of [[1.5, 1.5], [-1.5, 1.5], [1.5, -1.5], [-1.5, -1.5]]) {
        const p = at(e, nn);
        for (const dx of [0, 1]) for (const dy of [0, 1]) delete visited[`${tileX(p.lon) + dx},${tileY(p.lat) + dy}`];
    }
    const summary = w.optimize({
        start, end: null, distanceKm: 20, mode: 'tiles', routeType: 'round_trip', shape: 'loop',
        coverageData: { visited, bounds: [sw.lat, sw.lon, ne.lat, ne.lon], zoom },
        optimizeFor: 'infill', areaBounds: null,
    });
    const routes = w.posted.filter(m => m.type === 'route');
    assert.ok(summary.totalRoutes >= 1 && routes.length === summary.totalRoutes);
    for (const m of routes) {
        assert.ok(m.route.waypoints.length >= 1);
        for (const wp of m.route.waypoints) assert.equal(typeof wp.tiles, 'number');
    }
});
