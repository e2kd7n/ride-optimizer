// Worker protocol: every message echoes the request's runId (so the page can
// drop results from an abandoned run), and the workout-combo corridor
// constraint actually narrows which tiles count.
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
    vm.runInContext(src + '\n;this.__w = { distanceToPolylineKm, onmessage: self.onmessage };', ctx);
    return { ...ctx.__w, posted };
}

test('every message carries the request runId', () => {
    const w = loadWorker();
    // Bad request (no coverage bounds) -> progress + error, both tagged.
    w.onmessage({ data: { runId: 7, start: { lat: 41.9, lon: -87.7 }, distanceKm: 20,
        routeType: 'round_trip', coverageData: { visited: {} } } });
    assert.ok(w.posted.length >= 1);
    for (const m of w.posted) assert.equal(m.runId, 7, JSON.stringify(m));
    assert.equal(w.posted[w.posted.length - 1].type, 'error');
});

test('messages have no runId when the request had none', () => {
    const w = loadWorker();
    w.onmessage({ data: { start: { lat: 41.9, lon: -87.7 }, distanceKm: 20,
        routeType: 'round_trip', coverageData: { visited: {} } } });
    for (const m of w.posted) assert.equal(m.runId, undefined);
});

test('distanceToPolylineKm measures to the nearest segment, not just vertices', () => {
    const w = loadWorker();
    // Segment along the equator-ish line at lat 41.9 from lon -87.8 to -87.6.
    const line = [[41.9, -87.8], [41.9, -87.6]];
    // A point 1 km north of the segment's middle.
    const d = w.distanceToPolylineKm(41.9 + 1 / 111.32, -87.7, line);
    assert.ok(Math.abs(d - 1) < 0.01, `got ${d}`);
    // Beyond the end, distance is to the endpoint.
    const kmPerDegLon = 111.32 * Math.cos(41.9 * Math.PI / 180);
    const e = w.distanceToPolylineKm(41.9, -87.6 + 2 / kmPerDegLon, line);
    assert.ok(Math.abs(e - 2) < 0.01, `got ${e}`);
});
