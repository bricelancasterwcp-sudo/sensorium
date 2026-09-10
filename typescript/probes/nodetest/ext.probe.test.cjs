// CommonJS by its extension, which `classify` reaches before Node is asked
// anything: excluded, and COUNTED. `node --test` runs one child process per
// test file, so this file's child writes no spool at all and leaves one
// `_tally-<pid>.json` whose pid belongs to no spool -- reading
// `files_transformed: 0`, `excluded: {commonjs: 1}`.
//
// It requires nothing under the root but itself, on purpose: a second local
// `require` would be a second exclusion, and that count is the assertion.
const assert = require('node:assert/strict');
const { test } = require('node:test');

function add(a, b) {
  return a + b;
}

test('M3 a .cjs is excluded and counted', () => {
  assert.equal(add(1, 2), 3);
});
