// Unit tests for static/js/explore-refine.js (Explore Phase 2 geometry).
// Run: node --test tests/js   (also run from pytest via tests/test_explore_js.py)
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const R = require(path.join(__dirname, '..', '..', 'static', 'js', 'explore-refine.js'));

const LAT0 = 41.99, LON0 = -87.70;
const KM_LAT = 1 / 111.32;
const KM_LON = 1 / (111.32 * Math.cos(LAT0 * Math.PI / 180));
/** Point `east` km east and `north` km north of the origin. */
const pt = (east, north) => [LAT0 + north * KM_LAT, LON0 + east * KM_LON];
/** Straight polyline sampled every 50 m between two km-offset points. */
function line(a, b) {
    const out = [];
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const n = Math.max(1, Math.round(d / 0.05));
    for (let i = 0; i <= n; i++) out.push(pt(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n));
    return out;
}
const concat = (...ls) => ls.reduce((acc, l) => acc.concat(acc.length ? l.slice(1) : l), []);

/** A z17 grid where every tile in a box around the origin is visited except `holes`. */
function gridWithHoles(holes, zoom = 17) {
    const visited = new Set();
    const a = R.latLonToTile(...pt(-5, 5), zoom), b = R.latLonToTile(...pt(10, -5), zoom);
    for (let x = a.x; x <= b.x; x++) for (let y = a.y; y <= b.y; y++) visited.add(`${x},${y}`);
    for (const h of holes) visited.delete(`${h.x},${h.y}`);
    return { zoom, visited, isRoadless: () => false };
}

test('analyzeRetrace: out-and-back is ~all retraced, a loop is clean', () => {
    const outBack = concat(line([0, 0], [3, 0]), line([3, 0], [0, 0]));
    assert.ok(R.analyzeRetrace(outBack).fraction > 0.85);

    const loop = concat(line([0, 0], [2, 0]), line([2, 0], [2, 2]), line([2, 2], [0, 2]), line([0, 2], [0, 0]));
    assert.ok(R.analyzeRetrace(loop).fraction < 0.05);
});

test('analyzeRetrace: attributes a spur to the waypoint at its tip', () => {
    // Square loop with a 1.5 km out-and-back spur north to waypoint S.
    const route = concat(
        line([0, 0], [2, 0]), line([2, 0], [2, 2]),
        line([2, 2], [2, 3.5]), line([2, 3.5], [2, 2]),   // spur
        line([2, 2], [0, 2]), line([0, 2], [0, 0]),
    );
    const waypoints = [pt(0, 0), pt(2, 0), pt(2, 3.5), pt(0, 2), pt(0, 0)];
    const r = R.analyzeRetrace(route, waypoints);
    assert.equal(r.worstWaypoint, 2);
    assert.ok(r.fraction > 0.2 && r.fraction < 0.6, `fraction ${r.fraction}`);
});

test('findPickups: picks an unclaimed tile beside the route, not far ones or crossed ones', () => {
    const route = line([0, 0], [4, 0]);
    const z = 17;
    const onRoute = R.latLonToTile(...pt(2, 0), z);
    const beside = { x: onRoute.x, y: onRoute.y - 1 };                     // one tile north
    const far = R.latLonToTile(...pt(2, 3), z);                            // 3 km away
    const crossed = R.latLonToTile(...pt(1, 0), z);                        // route goes through it
    const grid = gridWithHoles([beside, far, crossed], z);

    const picks = R.findPickups(route, [grid]);
    const keys = picks.map(p => `${p.x},${p.y}`);
    assert.ok(keys.includes(`${beside.x},${beside.y}`), 'beside tile picked');
    assert.ok(!keys.includes(`${far.x},${far.y}`), 'far tile not picked');
    assert.ok(!keys.includes(`${crossed.x},${crossed.y}`), 'crossed tile not picked');
    const p = picks.find(q => q.x === beside.x && q.y === beside.y);
    const tb = R.tileBounds(p.x, p.y, z);
    assert.ok(R.pointInBounds([p.lat, p.lon], tb), 'pickup waypoint is inside its tile');
});

test('findPickups: respects the drawn area', () => {
    const route = line([0, 0], [4, 0]);
    const z = 17;
    const onRoute = R.latLonToTile(...pt(2, 0), z);
    const beside = { x: onRoute.x, y: onRoute.y - 1 };
    const grid = gridWithHoles([beside], z);
    // Box that ends just north of the route line — the tile above is outside.
    const sw = pt(-1, -1), ne = pt(5, 0.05);
    const picks = R.findPickups(route, [grid], { bounds: [sw[0], sw[1], ne[0], ne[1]] });
    assert.equal(picks.length, 0);
});

test('insertPickups: places each pickup on the leg the route passes it on', () => {
    const waypoints = [pt(0, 0), pt(2, 0), pt(2, 2), pt(0, 0)];
    const coords = concat(line([0, 0], [2, 0]), line([2, 0], [2, 2]), line([2, 2], [0, 0]));
    const meta = [{ tiles: 3 }, { tiles: 4 }];
    const near1 = { lat: pt(1, 0.1)[0], lon: pt(1, 0.1)[1], value: 1 };    // beside leg 0
    const near2 = { lat: pt(2.1, 1)[0], lon: pt(2.1, 1)[1], value: 1 };    // beside leg 1
    const out = R.insertPickups(coords, waypoints, meta, [near2, near1]);
    assert.equal(out.waypoints.length, 6);
    assert.deepEqual(out.waypoints[1], [near1.lat, near1.lon]);
    assert.deepEqual(out.waypoints[3], [near2.lat, near2.lon]);
    assert.equal(out.meta.length, 4);
    assert.ok(out.meta[0].pickup && out.meta[2].pickup);
    assert.equal(out.meta[1].tiles, 3);
});

test('chooseDropIndex: padding first, else lowest tiles per km saved', () => {
    const wps = [pt(0, 0), pt(1, 0), pt(5, 0), pt(1, 1), pt(0, 0)];
    assert.equal(R.chooseDropIndex(wps, [{ tiles: 5 }, { tiles: 5 }, { padding: true, tiles: 0 }]), 3);
    // The 5 km-out waypoint saves the most distance for the same tiles.
    assert.equal(R.chooseDropIndex(wps, [{ tiles: 5 }, { tiles: 5 }, { tiles: 5 }]), 2);
    assert.equal(R.chooseDropIndex([pt(0, 0), pt(1, 1)], []), -1);
});

test('cheapestInsertion: picks the leg the point is next to', () => {
    const wps = [pt(0, 0), pt(4, 0), pt(4, 4), pt(0, 0)];
    assert.equal(R.cheapestInsertion(wps, pt(4.2, 2)).index, 2);
});

test('fractionOutsideBounds and clampToBounds', () => {
    const sw = pt(0, -1), ne = pt(2, 1);
    const box = [sw[0], sw[1], ne[0], ne[1]];
    assert.ok(R.fractionOutsideBounds(line([0.5, 0], [1.5, 0]), box) === 0);
    const half = R.fractionOutsideBounds(line([1, 0], [3, 0]), box);
    assert.ok(half > 0.4 && half < 0.6, `half ${half}`);
    const c = R.clampToBounds(pt(5, 5), box);
    assert.ok(R.pointInBounds(c, box));
});

test('countNewTiles counts only unclaimed, non-water tiles the route enters', () => {
    const z = 17;
    const a = R.latLonToTile(...pt(1, 0), z), b = R.latLonToTile(...pt(2, 0), z);
    const grid = gridWithHoles([a, b], z);
    assert.equal(R.countNewTiles(line([0, 0], [3, 0]), [grid]), 2);
    grid.isRoadless = (x, y) => x === a.x && y === a.y;
    assert.equal(R.countNewTiles(line([0, 0], [3, 0]), [grid]), 1);
});

test('analyzeRetrace: catches a short dead-end stub', () => {
    // 2 km loop leg with a 120 m in-and-out stub in the middle.
    const route = concat(line([0, 0], [1, 0]), line([1, 0], [1, 0.12]), line([1, 0.12], [1, 0]), line([1, 0], [2, 0]));
    assert.ok(R.analyzeRetrace(route).retracedKm > 0.15);
});

test('uselessStops: flags a stub into claimed ground, keeps one that grabs a tile', () => {
    const z = 17;
    const fresh = R.latLonToTile(...pt(3, 0.4), z);
    const grid = gridWithHoles([fresh], z);
    // Loop with two stubs: one north at x=1 (all claimed), one north at x=3 (into the fresh tile).
    const wps = [pt(0, 0), pt(1, 0.4), pt(3, 0.4), pt(4, 0), pt(4, -1), pt(0, -1), pt(0, 0)];
    const coords = concat(
        line([0, 0], [1, 0]), line([1, 0], [1, 0.4]), line([1, 0.4], [1, 0]),
        line([1, 0], [3, 0]), line([3, 0], [3, 0.4]), line([3, 0.4], [3, 0]),
        line([3, 0], [4, 0]), line([4, 0], [4, -1]), line([4, -1], [0, -1]), line([0, -1], [0, 0]),
    );
    const useless = R.uselessStops(coords, wps, [grid]);
    assert.ok(useless.includes(1), 'claimed-ground stub flagged');
    assert.ok(!useless.includes(2), 'tile-grabbing stub kept');
});

// ── Polygon areas ────────────────────────────────────────────────
// L-shaped area: 4 km x 4 km with the north-east 2 km x 2 km quadrant cut out.
const L_AREA = [pt(0, 0), pt(4, 0), pt(4, 2), pt(2, 2), pt(2, 4), pt(0, 4)];

test('pointInBounds handles polygons, including the notch of an L', () => {
    assert.equal(R.isPolygonArea(L_AREA), true);
    assert.equal(R.isPolygonArea([1, 2, 3, 4]), false);
    assert.equal(R.pointInBounds(pt(1, 1), L_AREA), true);
    assert.equal(R.pointInBounds(pt(3, 1), L_AREA), true);
    assert.equal(R.pointInBounds(pt(3, 3), L_AREA), false);   // the cut-out
    assert.equal(R.pointInBounds(pt(5, 1), L_AREA), false);
});

test('areaBBox encloses a polygon', () => {
    const [s, w, n, e] = R.areaBBox(L_AREA);
    assert.ok(Math.abs(s - LAT0) < 1e-9 && Math.abs(w - LON0) < 1e-9);
    assert.ok(Math.abs(n - pt(0, 4)[0]) < 1e-9 && Math.abs(e - pt(4, 0)[1]) < 1e-9);
});

test('fractionOutsideBounds counts route length in the cut-out of a polygon', () => {
    assert.ok(R.fractionOutsideBounds(line([0.5, 1], [3.5, 1]), L_AREA) < 0.01);
    // West→east at y=3: the last ~half (x 2→4) runs through the cut-out.
    const f = R.fractionOutsideBounds(line([0.5, 3], [3.5, 3]), L_AREA);
    assert.ok(f > 0.4 && f < 0.55, `fraction ${f}`);
    // Hugging the inner edge (30 m inside the cut-out) is within tolerance.
    assert.ok(R.fractionOutsideBounds(line([2.03, 2.5], [2.03, 3.5]), L_AREA) < 0.01);
});

test('clampToBounds moves an outside point onto the polygon edge', () => {
    const inside = pt(1, 1);
    assert.deepEqual(R.clampToBounds(inside, L_AREA), inside);
    const c = R.clampToBounds(pt(3, 2.5), L_AREA);     // in the cut-out, nearest the y=2 edge
    assert.ok(Math.abs(c[0] - pt(3, 2)[0]) < 1e-6 && Math.abs(c[1] - pt(3, 2)[1]) < 1e-6);
});

test('polygonSelfIntersects spots a bow-tie', () => {
    assert.equal(R.polygonSelfIntersects(L_AREA), false);
    assert.equal(R.polygonSelfIntersects([pt(0, 0), pt(2, 2), pt(2, 0), pt(0, 2)]), true);
});
