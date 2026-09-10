// The ES-module extension with no types in it at all: Node reports `module`,
// the hook hands `module` back with the instrumented source, and the file is
// loaded as written. The pair of this and the `.mts` beside it is what says
// the hook reads NODE's verdict rather than the file's extension.
import assert from 'node:assert/strict';
import { test } from 'node:test';

function double(n) {
  return n * 2;
}

test('M2 an .mjs is instrumented with nothing to erase', () => {
  assert.equal(double(21), 42);
});
