// Squadrats yard: largest 4-connected group of collected tiles whose four
// N/E/S/W neighbours are all collected (diagonals irrelevant).
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const R = require(path.join(__dirname, '..', '..', 'static', 'js', 'explore-refine.js'));

/** visited map from a picture: '#' = collected, row index = y, col = x. */
function grid(rows) {
    const v = {};
    rows.forEach((row, y) => [...row].forEach((c, x) => { if (c === '#') v[`${x},${y}`] = true; }));
    return v;
}
const sorted = s => [...s].sort();

test('a 3x3 block has a single-tile yard at its centre', () => {
    assert.deepEqual(sorted(R.findYard(grid(['###', '###', '###']))), ['1,1']);
});

test('diagonal neighbours do not matter', () => {
    // Plus shape: centre has all 4 edge neighbours, corners missing.
    assert.deepEqual(sorted(R.findYard(grid(['.#.', '###', '.#.']))), ['1,1']);
});

test('no qualifying tile → empty yard', () => {
    assert.equal(R.findYard(grid(['##', '##'])).size, 0);
    assert.equal(R.findYard({}).size, 0);
    assert.equal(R.findYard(null).size, 0);
});

test('only the largest 4-connected group is the yard', () => {
    const v = grid([
        '#####.###',
        '#####.###',
        '#####.###',
    ]);
    // Left block interior: x=1..3, y=1 (3 tiles). Right block: x=7, y=1 (1 tile).
    assert.deepEqual(sorted(R.findYard(v)), ['1,1', '2,1', '3,1']);
});

test('interior tiles touching only diagonally are separate groups', () => {
    const v = grid([
        '###..',
        '###..',
        '#####',
        '..###',
        '..###',
    ]);
    // (1,1), (2,2) and (3,3) each have all four neighbours, but they only
    // touch diagonally — three one-tile groups, so the yard is one tile.
    const yard = R.findYard(v);
    assert.equal(yard.size, 1);
});

test('tileSetOutline traces only the boundary edges', () => {
    const one = new Set(['5,5']);
    assert.equal(R.tileSetOutline(one, 14).length, 4);
    const pair = new Set(['5,5', '6,5']);
    assert.equal(R.tileSetOutline(pair, 14).length, 6); // shared edge omitted
    const block = new Set(['0,0', '1,0', '0,1', '1,1']);
    assert.equal(R.tileSetOutline(block, 14).length, 8);
});
