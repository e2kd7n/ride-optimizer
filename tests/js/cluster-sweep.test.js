// The cluster rule: a route must not leave an unclaimed tile that is
// edge-adjacent to it and part of a cluster of unclaimed tiles, unless that
// tile is at the boundary/horizon (drawn area / loaded coverage), water, or
// unreachable by road.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const R = require(path.join(__dirname, '..', '..', 'static', 'js', 'explore-refine.js'));

const LAT0 = 41.99, LON0 = -87.70;
const KM_LAT = 1 / 111.32, KM_LON = 1 / (111.32 * Math.cos(LAT0 * Math.PI / 180));
const pt = (e, n) => [LAT0 + n * KM_LAT, LON0 + e * KM_LON];
function line(a, b) {
    const out = [];
    const n = Math.max(1, Math.round(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05));
    for (let i = 0; i <= n; i++) out.push(pt(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n));
    return out;
}
const Z = 17;

/** z17 grid: box around the origin all visited except `holes` ([x, y] or {x, y}). */
function grid(holes) {
    const visited = new Set();
    const a = R.latLonToTile(...pt(-3, 3), Z), b = R.latLonToTile(...pt(6, -3), Z);
    for (let x = a.x; x <= b.x; x++) for (let y = a.y; y <= b.y; y++) visited.add(`${x},${y}`);
    for (const h of holes) visited.delete(Array.isArray(h) ? `${h[0]},${h[1]}` : `${h.x},${h.y}`);
    return { zoom: Z, visited, isRoadless: () => false, tileRange: { minX: a.x, maxX: b.x, minY: a.y, maxY: b.y } };
}
const ON = R.latLonToTile(...pt(1.5, 0), Z);   // a tile the test route runs through
const ROUTE = line([0, 0], [4, 0]);

test('a cluster touching the route is returned whole', () => {
    const cluster = [[ON.x, ON.y - 1], [ON.x, ON.y - 2], [ON.x + 1, ON.y - 2]];
    const targets = R.clusterSweepTargets(ROUTE, [grid(cluster)]);
    const keys = new Set(targets.map(t => `${t.x},${t.y}`));
    for (const [x, y] of cluster) assert.ok(keys.has(`${x},${y}`), `cluster tile ${x},${y}`);
    for (const t of targets) assert.ok(R.pointInBounds([t.lat, t.lon], R.tileBounds(t.x, t.y, Z)), 'waypoint inside its tile');
});

test('a lone unclaimed tile beside the route is not required', () => {
    assert.equal(R.clusterSweepTargets(ROUTE, [grid([[ON.x, ON.y - 1]])]).length, 0);
});

test('a tile the route itself claims counts toward the cluster', () => {
    const targets = R.clusterSweepTargets(ROUTE, [grid([[ON.x, ON.y], [ON.x, ON.y - 1]])]);
    assert.deepEqual(targets.map(t => `${t.x},${t.y}`), [`${ON.x},${ON.y - 1}`]);
});

test('boundary/horizon tiles are exempt', () => {
    const cluster = [[ON.x, ON.y - 1], [ON.x, ON.y - 2]];
    const sw = pt(-1, -1), ne = pt(5, 0.05);
    assert.equal(R.clusterSweepTargets(ROUTE, [grid(cluster)], { bounds: [sw[0], sw[1], ne[0], ne[1]] }).length, 0, 'outside drawn area');
    const g = grid(cluster);
    g.tileRange = { minX: ON.x - 50, maxX: ON.x + 50, minY: ON.y, maxY: ON.y + 50 };
    assert.equal(R.clusterSweepTargets(ROUTE, [g]).length, 0, 'outside loaded coverage');
    const w = grid(cluster);
    w.isRoadless = (x, y) => y < ON.y;
    assert.equal(R.clusterSweepTargets(ROUTE, [w]).length, 0, 'water');
});

test('open frontier (huge component) only claims the row beside the route', () => {
    const holes = [];
    for (let dx = -15; dx <= 15; dx++) for (let dy = 1; dy <= 12; dy++) holes.push([ON.x + dx, ON.y - dy]);
    const targets = R.clusterSweepTargets(ROUTE, [grid(holes)], { maxComponent: 80 });
    assert.ok(targets.length > 0);
    for (const t of targets) assert.equal(t.y, ON.y - 1);
});

// ── refineRoute stage 5 against a fake straight-line router ──

function makeApi(transform = (w) => w) {
    const calls = [];
    return {
        calls,
        async getExplorationRoute({ waypoints, bounds }) {
            const wps = waypoints.map(transform);
            calls.push({ waypoints: wps });
            const coords = [];
            for (let i = 1; i < wps.length; i++) {
                const a = wps[i - 1], b = wps[i];
                const n = Math.max(1, Math.round(R.haversineKm(a, b) / 0.05));
                for (let k = i === 1 ? 0 : 1; k <= n; k++) coords.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]);
            }
            return { status: 'success', coordinates: coords, distance_km: R.pathKm(wps) * 1.3, duration_min: 1 };
        },
    };
}
function loadRefine(api) {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', 'static', 'js', 'explore.js'), 'utf8');
    const stub = new Proxy(function () {}, { get: (t, k) => (k === Symbol.toPrimitive ? () => '' : stub), apply: () => stub, construct: () => stub });
    const ctx = {
        window: { ExploreRefine: R, debounce: (fn) => fn }, document: { addEventListener() {}, getElementById: () => stub },
        L: stub, APIClient: function () { return api; }, Math, Map, Set, Object, Array, Number, Error, Promise, console,
    };
    vm.createContext(ctx);
    vm.runInContext(src + '\n;this.__refine = refineRoute;', ctx);
    return ctx.__refine;
}
const LOOP = [pt(0, 0), pt(3, 0), pt(3, -1), pt(0, -1), pt(0, 0)];

test('refineRoute sweeps a touched 3x3 cluster completely', async () => {
    const holes = [];
    for (let dx = 0; dx < 3; dx++) for (let dy = 1; dy <= 3; dy++) holes.push([ON.x + dx, ON.y - dy]);
    const g = grid(holes);
    const api = makeApi();
    const out = await loadRefine(api)(LOOP, { targetKm: 11, mode: 'cap', surfacePref: 'any', grids: [g] });
    assert.equal(R.clusterSweepTargets(out.route.coordinates, [g]).length, 0, 'no adjacent cluster tile left');
    assert.equal(R.countNewTiles(out.route.coordinates, [g]), holes.length, 'all 9 tiles claimed');
    assert.ok(out.stats.sweepAdded > 0);
    assert.equal(out.stats.sweepRemaining, 0);
});

test('refineRoute reports tiles the router cannot reach instead of looping', async () => {
    const blocked = [ON.x, ON.y - 2];
    const tb = R.tileBounds(blocked[0], blocked[1], Z);
    // Waypoints inside the blocked tile get snapped back onto the route line.
    const api = makeApi((w) => (R.pointInBounds(w, tb) ? [pt(0, 0)[0], w[1]] : w));
    const g = grid([[ON.x, ON.y - 1], blocked]);
    const out = await loadRefine(api)(LOOP, { targetKm: 11, mode: 'cap', surfacePref: 'any', grids: [g] });
    assert.ok(out.route);
    assert.equal(out.stats.sweepUnreachable, 1);
    assert.ok(api.calls.length < 15, `calls ${api.calls.length}`);
});

test('refineRoute sweep stays within the distance budget instead of cascading', async () => {
    // A small cluster (2 tiles) and a big one (8x8 = 64 tiles, under the
    // frontier limit) both touch the route. Sweeping the big one would more
    // than double the route, so it's skipped and reported; the small one is
    // still swept.
    const small = [[ON.x, ON.y - 1], [ON.x, ON.y - 2]];
    const far = R.latLonToTile(...pt(3, 0), Z);
    const big = [];
    for (let dx = 0; dx < 8; dx++) for (let dy = 1; dy <= 8; dy++) big.push([far.x - 4 + dx, far.y + dy]);
    const g = grid([...small, ...big]);
    const api = makeApi();
    const targetKm = 11;
    const out = await loadRefine(api)(LOOP, { targetKm, mode: 'cap', surfacePref: 'any', grids: [g] });
    assert.ok(out.route.distance_km <= targetKm * 1.25 * 1.05, `km ${out.route.distance_km}`);
    assert.equal(out.stats.sweepOverBudget, true);
    const claimed = R.newTilesCrossed(out.route.coordinates, g);
    assert.ok(small.every(([x, y]) => claimed.has(`${x},${y}`)), 'small cluster swept');
    assert.ok(out.stats.sweepRemaining > 0, 'big cluster reported as left');
});

test('budgetSweepBatch takes whole clusters, best value first, within budget', () => {
    const wps = [pt(0, 0), pt(4, 0), pt(0, 0)];
    const mk = (comp, e, n) => ({ component: comp, lat: pt(e, n)[0], lon: pt(e, n)[1] });
    const near = [mk(1, 1, 0.2), mk(1, 1.2, 0.2)];            // cheap
    const farC = [mk(2, 2, 3), mk(2, 2.2, 3), mk(2, 2.4, 3)]; // ~6 km detour
    const { batch, skippedTiles } = R.budgetSweepBatch(wps, [...near, ...farC], { budgetKm: 8 * 1.3 + 1, roadRatio: 1.3 });
    assert.deepEqual(batch, near);
    assert.equal(skippedTiles, 3);
    const all = R.budgetSweepBatch(wps, [...near, ...farC], { budgetKm: 100, roadRatio: 1.3 });
    assert.equal(all.batch.length, 5);
    const roomed = R.budgetSweepBatch(wps, [...near, ...farC], { budgetKm: 100, roadRatio: 1.3, room: 2 });
    assert.deepEqual(roomed.batch, near, 'a cluster that does not fit the waypoint room is skipped whole');
});
