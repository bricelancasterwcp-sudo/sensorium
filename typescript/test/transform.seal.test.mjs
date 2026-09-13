// The seal's transform half (2026-09-12 design §4.2): which functions get the
// DEFERRED exit, what their wrapper and their returns are spliced with, and —
// the other half of ruling R2 — that a function WITHOUT the shape comes out of
// this transform byte-for-byte as 0.3.0 left it.
//
// `transform.test.mjs` holds the golden harness and runs every golden in the
// directory, this one included; what is here is the seal's own reading of it,
// so a wrapper string that moved has a test that names the string rather than
// only a golden that no longer matches.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

import { sitesOf, transformSource } from '../src/transform.mjs';

const require = createRequire(import.meta.url);
const ts = require('typescript');

const GOLDEN_DIR = fileURLToPath(new URL('./golden/', import.meta.url));
const ROOT = '/w';
const RT = 'RT';

/**
 * @param {string} code
 * @param {string} [name]
 * @param {string[]} [focus]
 * @returns {string} the instrumented source
 */
function transform(code, name = 'a.ts', focus = []) {
  const out = transformSource(code, `${ROOT}/src/${name}`, { root: ROOT, ts, rtPath: RT, focus });
  assert.ok(out && out.code !== null, 'the fragment parses and is instrumented');
  return out.code;
}

/**
 * @param {string} code
 * @param {string} [name]
 * @returns {Record<string, unknown>[]}
 */
function sites(code, name = 'a.ts') {
  const out = sitesOf(code, `${ROOT}/src/${name}`, { root: ROOT, ts });
  assert.ok(out, 'the fragment is a file this recorder transforms');
  return /** @type {Record<string, unknown>[]} */ (out.sites);
}

// --- which functions pass one defers ---------------------------------------

test('sitesOf marks the function that returns through a finally, and only it', () => {
  // Four functions, one shape each: the seal's, a function with no `try` at
  // all, rung 2's `finally_return` shape (the return is IN the finally, and
  // nothing further guards it), and a return a nested arrow makes inside a
  // try-with-finally — that arrow's own exit, not this function's.
  const rows = sites([
    'export function settle(): number {',
    '  try {',
    '    return 1;',
    '  } finally {',
    '    cleanup();',
    '  }',
    '}',
    '',
    'export function plain(): number {',
    '  return 2;',
    '}',
    '',
    'export function swallow(): string {',
    '  try {',
    '    risky();',
    '  } finally {',
    "    return 'ok';",
    '  }',
    '}',
    '',
    'export function hands(): void {',
    '  try {',
    '    queue(() => {',
    '      return 3;',
    '    });',
    '  } finally {',
    '    cleanup();',
    '  }',
    '}',
    '',
  ].join('\n'));

  assert.deepEqual(rows.map((row) => [row.qualname, row.deferred]), [
    ['settle', true],
    ['plain', false],
    ['swallow', false],
    // The arrow is a site of its own, and its own body carries no `try`.
    ['hands', false],
    ['hands.<anonymous>', false],
  ]);
});

// --- R2: a function without the shape does not move ------------------------

test('a focused function with no try at all is byte-identical to its 0.3.0 golden', () => {
  // The control for R2, read against a golden this slice did not write:
  // `focus-loop.expected.ts` was hand-written at the focus tier and is
  // committed, so an edit that reached every wrapper — rather than only the
  // deferred ones — fails here as well as in `transform.test.mjs`.
  const src = fs.readFileSync(path.join(GOLDEN_DIR, 'focus-loop.ts'), 'utf8');
  const expected = fs.readFileSync(path.join(GOLDEN_DIR, 'focus-loop.expected.ts'), 'utf8');
  assert.equal(src.includes('finally'), false, 'the control carries no finally of its own');

  assert.equal(transform(src, 'focus-loop.ts', ['sum']), expected);
});

test('a return written INSIDE a finally keeps 0.3.0’s wrapper (the rule discriminates)', () => {
  // `finally-return.ts` is rung 2's case and the census's second exclusion:
  // the keyword is there, the shape is not, and its golden must not move.
  const src = fs.readFileSync(path.join(GOLDEN_DIR, 'finally-return.ts'), 'utf8');
  const expected = fs.readFileSync(path.join(GOLDEN_DIR, 'finally-return.expected.ts'), 'utf8');

  assert.equal(transform(src, 'finally-return.ts'), expected);
});

// --- what a deferred function is spliced with ------------------------------

test('a deferred function pends every return and seals in the wrapper’s finally', () => {
  const code = transform(
    fs.readFileSync(path.join(GOLDEN_DIR, 'focus-finally-return.ts'), 'utf8'),
    'focus-finally-return.ts', ['settle']);

  // Both of `settle`'s returns pend; the fallthrough close pends `undefined`.
  assert.ok(code.includes('return __srt.pend(__sf,(1));'), code);
  assert.ok(code.includes('return __srt.pend(__sf,(2));'), code);
  assert.ok(code.includes(
    ';__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}'),
  code);
  // `note` is NOT deferred, so its own wrapper and its own return are 0.3.0's.
  assert.ok(code.includes('return __srt.ret(__sf,(n));'), code);
  assert.equal((code.match(/__srt\.seal\(/g) ?? []).length, 1, 'one function was deferred');
  assert.equal((code.match(/__srt\.pend\(/g) ?? []).length, 3, "settle's two returns and its close");
});

test('a deferred generator seals before it gcloses, in one finally', () => {
  // §4.4: two exits would be two RETURN rows for one frame. `seal` runs first
  // and closes the frame; `gclose` then meets a closed frame and is the no-op
  // its own contract promises.
  const code = transform([
    'export function* rows(): Generator<number> {',
    '  try {',
    '    yield 1;',
    '    return 2;',
    '  } finally {',
    '    cleanup();',
    '  }',
    '}',
    '',
  ].join('\n'));

  assert.ok(code.includes(
    ';__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}'
    + 'finally{__srt.seal(__sf);__srt.gclose(__sf)}'), code);
  assert.equal(code.includes('__srt.ret('), false, 'a deferred body never rets');
});

test('a bare return in a deferred function pends undefined', () => {
  const code = transform([
    'export function bail(flag: boolean): void {',
    '  try {',
    '    if (flag) return;',
    '  } finally {',
    '    cleanup();',
    '  }',
    '}',
    '',
  ].join('\n'));

  assert.ok(code.includes('if (flag) return __srt.pend(__sf,undefined);'), code);
});
