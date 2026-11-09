// Tests for explore.js's refineRoute() stage orchestration (cap/trim, no
// padding, pickups, retrace fix, area fence) against a fake road router.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const R = require(path.join(__dirname, '..', '..', 'static', 'js', 'explore-refine.js'));
const ROAD = 1.3;

/** Fake router: straight segments between waypoints (50 m samples), road km = 1.3 × straight. */
function makeApi() {
    const calls = [];
    return {
        calls,
        async getExplorationRoute({ waypoints, bounds }) {
            calls.push({ waypoints: waypoints.map(w => [...w]), bounds });
            const coords = [];
            for (let i = 1; i < waypoints.length; i++) {
                const a = waypoints[i - 1], b = waypoints[i];
                const n = Math.max(1, Math.round(R.haversineKm(a, b) / 0.05));
                for (let k = i === 1 ? 0 : 1; k <= n; k++) coords.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]);
            }
            return { status: 'success', coordinates: coords, distance_km: R.pathKm(waypoints) * ROAD, duration_min: 1 };
        },
    };
}

function loadExplore(api) {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', 'static', 'js', 'explore.js'), 'utf8');
    const win = { ExploreRefine: R, debounce: (fn) => fn };
    // explore.js does `const api = new APIClient('/api')` — hand it the fake.
    // Catch-all stub for page-level globals (Leaflet's L, etc.) touched at load.
    const stub = new Proxy(function () {}, { get: (t, k) => (k === Symbol.toPrimitive ? () => '' : stub), apply: () => stub, construct: () => stub });
    const ctx = { window: win, document: { addEventListener() {}, getElementById: () => stub }, L: stub, APIClient: function () { return api; }, Math, Map, Set, Object, Array, Number, Error, Promise, console };
    vm.createContext(ctx);
    vm.runInContext(src + '\n;this.__refine = refineRoute;', ctx);
    return ctx.__refine;
}

const LAT0 = 41.99, LON0 = -87.70;
const KM_LAT = 1 / 111.32, KM_LON = 1 / (111.32 * Math.cos(LAT0 * Math.PI / 180));
const pt = (e, n) => [LAT0 + n * KM_LAT, LON0 + e * KM_LON];

test('cap mode: a short route is returned as-is, never padded', async () => {
    const api = makeApi();
    const refine = loadExplore(api);
    const wps = [pt(0, 0), pt(1, 0), pt(1, 1), pt(0, 0)];
    const out = await refine(wps, { targetKm: 60, mode: 'cap', surfacePref: 'any' });
    assert.ok(out.route);
    assert.equal(api.calls.length, 1);
    assert.ok(out.route.distance_km < 10);
});

test('cap mode: trims lowest-value waypoints until the route fits', async () => {
    const api = makeApi();
    const refine = loadExplore(api);
    const wps = [pt(0, 0)];
    const meta = [];
    for (let i = 0; i < 12; i++) {
        const a = (i / 12) * 2 * Math.PI;
        // One low-value stop sticks out as a spike — expensive and worth little.
        const r = i === 3 ? 7 : 4;
        wps.push(pt(r * Math.cos(a), r * Math.sin(a)));
        meta.push({ tiles: i === 3 ? 1 : 10 });
    }
    wps.push(pt(0, 0));
    const out = await refine(wps, { targetKm: 25, mode: 'cap', surfacePref: 'any', baseMeta: meta });
    assert.ok(out.route.distance_km <= 25 * 1.05, `got ${out.route.distance_km}`);
    const final = api.calls[api.calls.length - 1].waypoints;
    assert.ok(!final.some(w => w[0] === wps[4][0] && w[1] === wps[4][1]), 'low-value waypoint dropped');
});

test('retrace fix drops the waypoint at the tip of a spur; out-and-back keeps it', async () => {
    const spur = [pt(0, 0), pt(2, 0), pt(2, 4), pt(2, 0.05), pt(0, 2), pt(0, 0)];
    for (const allowRetrace of [false, true]) {
        const api = makeApi();
        const refine = loadExplore(api);
        const out = await refine(spur, { targetKm: 60, mode: 'cap', surfacePref: 'any', allowRetrace });
        const final = api.calls[api.calls.length - 1].waypoints;
        const hasTip = final.some(w => w[0] === spur[2][0] && w[1] === spur[2][1]);
        assert.equal(hasTip, allowRetrace, `allowRetrace=${allowRetrace}`);
        assert.ok(out.route);
    }
});

test('pickups: an unclaimed tile beside the route gets added within the cap', async () => {
    const api = makeApi();
    const refine = loadExplore(api);
    const z = 17;
    const beside = R.latLonToTile(...pt(1.5, 0.25), z);
    const visited = new Set();
    const a = R.latLonToTile(...pt(-2, 3), z), b = R.latLonToTile(...pt(4, -3), z);
    for (let x = a.x; x <= b.x; x++) for (let y = a.y; y <= b.y; y++) visited.add(`${x},${y}`);
    visited.delete(`${beside.x},${beside.y}`);
    const grid = { zoom: z, visited, isRoadless: () => false };

    const wps = [pt(0, 0), pt(3, 0), pt(3, -1), pt(0, -1), pt(0, 0)];
    const out = await refine(wps, { targetKm: 30, mode: 'cap', surfacePref: 'any', grids: [grid] });
    assert.equal(out.stats.pickupsAdded, 1);
    assert.equal(R.countNewTiles(out.route.coordinates, [grid]), 1);
});

test('per-stop check drops a stub into claimed ground, keeps a tile-grabbing one', async () => {
    const api = makeApi();
    const refine = loadExplore(api);
    const z = 17;
    const fresh = R.latLonToTile(...pt(3, 0.4), z);
    const visited = new Set();
    const a = R.latLonToTile(...pt(-2, 3), z), b = R.latLonToTile(...pt(6, -3), z);
    for (let x = a.x; x <= b.x; x++) for (let y = a.y; y <= b.y; y++) visited.add(`${x},${y}`);
    visited.delete(`${fresh.x},${fresh.y}`);
    const grid = { zoom: z, visited, isRoadless: () => false };
    // Fake router draws straight lines, so model the stubs as there-and-back stops.
    const wps = [pt(0, 0), pt(1, 0), pt(1, 0.4), pt(1, 0.01), pt(3, 0), pt(3, 0.4), pt(3, 0.01), pt(4, 0), pt(4, -1), pt(0, -1), pt(0, 0)];
    const out = await refine(wps, { targetKm: 40, mode: 'cap', surfacePref: 'any', grids: [grid], allowRetrace: true });
    const final = api.calls[api.calls.length - 1].waypoints;
    const has = (p) => final.some(w => w[0] === p[0] && w[1] === p[1]);
    assert.ok(!has(pt(1, 0.4)), 'claimed-ground stub tip dropped');
    assert.ok(has(pt(3, 0.4)), 'tile-grabbing stub tip kept');
    assert.ok(out.stats.uselessDropped >= 1);
    assert.equal(R.countNewTiles(out.route.coordinates, [grid]), 1);
});

test('pigtail cut: a dead-end stub that claims nothing is replaced by an anchor at its base', async () => {
    // Fake router with one dead end: reaching TIP means riding up from the
    // junction J and straight back down. That's the spur a real router makes
    // for a stop snapped to a dead-end street.
    const J = pt(1, 0), TIP = pt(1, 0.4);
    const isTip = (w) => w[0] === TIP[0] && w[1] === TIP[1];
    const calls = [];
    const api = {
        async getExplorationRoute({ waypoints }) {
            calls.push(waypoints.map(w => [...w]));
            const path = [];
            waypoints.forEach((w, i) => { if (isTip(w) && i > 0) path.push(J, w, J); else path.push(w); });
            const coords = [];
            for (let i = 1; i < path.length; i++) {
                const a = path[i - 1], b = path[i];
                const n = Math.max(1, Math.round(R.haversineKm(a, b) / 0.05));
                for (let k = i === 1 ? 0 : 1; k <= n; k++) coords.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]);
            }
            return { status: 'success', coordinates: coords, distance_km: R.pathKm(coords) * ROAD, duration_min: 1 };
        },
    };
    const refine = loadExplore(api);
    const z = 17;
    // Fresh tiles on the main road either side of the junction, so the stop's
    // leg (start to pt(3,0)) claims something and the leg-based per-stop
    // check keeps it. Only the excursion itself claims nothing.
    const freshA = R.latLonToTile(...pt(0.5, 0), z), freshB = R.latLonToTile(...pt(2, 0), z);
    const freshC = R.latLonToTile(...pt(1.5, -1), z);   // keeps the loop's return leg worth riding
    const visited = new Set();
    const a = R.latLonToTile(...pt(-2, 3), z), b = R.latLonToTile(...pt(6, -3), z);
    for (let x = a.x; x <= b.x; x++) for (let y = a.y; y <= b.y; y++) visited.add(`${x},${y}`);
    visited.delete(`${freshA.x},${freshA.y}`);
    visited.delete(`${freshB.x},${freshB.y}`);
    visited.delete(`${freshC.x},${freshC.y}`);
    const grid = { zoom: z, visited, isRoadless: () => false };
    const wps = [pt(0, 0), TIP, pt(3, 0), pt(3, -1), pt(0, -1), pt(0, 0)];
    const out = await refine(wps, { targetKm: 40, mode: 'cap', surfacePref: 'any', grids: [grid] });
    const final = calls[calls.length - 1];
    assert.ok(!final.some(isTip), 'stub tip dropped');
    assert.ok(R.haversineKm(final[1], J) < 0.05, 'anchored at the junction');
    assert.equal(out.stats.spursPruned, 1);
    assert.equal(R.countNewTiles(out.route.coordinates, [grid]), 3);
    assert.ok(out.route.distance_km < (R.pathKm([pt(0, 0), J, TIP, J, pt(3, 0), pt(3, -1), pt(0, -1), pt(0, 0)]) * ROAD) - 0.9);
});

test('fence bounds are sent with every routing call', async () => {
    const api = makeApi();
    const refine = loadExplore(api);
    const box = [...pt(-5, -5), ...pt(5, 5)];
    const bounds = [box[0], box[1], box[2], box[3]];
    await refine([pt(0, 0), pt(1, 0), pt(0, 0)], { targetKm: 30, mode: 'cap', surfacePref: 'any', fenceBounds: bounds });
    assert.ok(api.calls.length >= 1);
    for (const c of api.calls) assert.deepEqual(c.bounds, bounds);
});

test('match mode padding stays inside the drawn area', async () => {
    const api = makeApi();
    const refine = loadExplore(api);
    const sw = pt(-1, -1), ne = pt(3, 1);
    const area = [sw[0], sw[1], ne[0], ne[1]];
    await refine([pt(0, 0), pt(2, 0)], { targetKm: 12, mode: 'match', surfacePref: 'any', dirBearing: 225, areaBounds: area });
    for (const c of api.calls) for (const w of c.waypoints) assert.ok(R.pointInBounds(w, area), `waypoint ${w} outside area`);
});
