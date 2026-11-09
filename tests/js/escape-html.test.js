// Regression test: escapeHtml() must neutralise every HTML metacharacter.
// It once replaced '&', '<' and '>' with themselves, leaving every
// "escaped" innerHTML sink open to injection via ride/route names.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const src = fs.readFileSync(path.join(__dirname, '..', '..', 'static', 'js', 'common.js'), 'utf8');
// Pull out just the function so the rest of common.js (DOM wiring) never runs.
const fnSrc = src.match(/function escapeHtml\(unsafe\) \{[\s\S]*?\n\}/)[0];
const ctx = {};
vm.runInNewContext(`${fnSrc}; this.escapeHtml = escapeHtml;`, ctx);
const { escapeHtml } = ctx;

test('escapes all five HTML metacharacters', () => {
    assert.equal(escapeHtml('<b>&"\''), '&lt;b&gt;&amp;&quot;&#039;');
});

test('an injected tag comes out inert', () => {
    assert.equal(escapeHtml('<img src=x onerror=alert(1)>'), '&lt;img src=x onerror=alert(1)&gt;');
});

test('ampersand is escaped first, so entities are not double-decoded', () => {
    assert.equal(escapeHtml('&lt;'), '&amp;lt;');
});

test('non-strings are stringified', () => {
    assert.equal(escapeHtml(42), '42');
});
