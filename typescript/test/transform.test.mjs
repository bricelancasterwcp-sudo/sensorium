// Goldens for the source transform. Every `test/golden/<name>.<ext>` has a
// hand-written `<name>.expected.<ext>`: the comparison is byte-exact, the line
// count of the output must equal the input's (no edit contains a newline), and
// the output must parse with no syntax diagnostics under the consumer's own
// TypeScript. The expected files were written by hand from the design's splice
// forms — never pasted from this transform's output, which would pin nothing.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

import { classify, transformSource } from '../src/transform.mjs';

const require = createRequire(import.meta.url);
const ts = require('typescript');

const GOLDEN_DIR = fileURLToPath(new URL('./golden/', import.meta.url));
const ROOT = '/w';
const RT = 'RT';

const FRAME_KINDS = new Set(['function', 'coroutine', 'generator', 'async_generator']);
const EXCLUSION_REASONS = new Set([
  'vitest-hoisted-factory',
  'overload-signature',
  'ambient',
  'abstract',
  'commonjs',
]);

/**
 * @param {string} file
 * @returns {import('typescript').ScriptKind}
 */
function scriptKindFor(file) {
  const ext = path.extname(file);
  if (ext === '.tsx') return ts.ScriptKind.TSX;
  if (ext === '.ts') return ts.ScriptKind.TS;
  return ts.ScriptKind.JSX;
}

/**
 * @param {string} file
 * @param {string} code
 * @returns {readonly import('typescript').Diagnostic[]}
 */
function parseDiagnosticsOf(file, code) {
  const sf = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, false, scriptKindFor(file));
  return /** @type {any} */ (sf).parseDiagnostics;
}

/** @returns {string[]} the golden input basenames, sorted */
function goldenInputs() {
  return fs
    .readdirSync(GOLDEN_DIR)
    .filter((name) => !name.includes('.expected.'))
    .filter((name) => ['.ts', '.tsx', '.js', '.jsx', '.mjs'].includes(path.extname(name)))
    .sort();
}

/**
 * @param {string} name basename of a golden input
 * @returns {{src: string, out: NonNullable<ReturnType<typeof transformSource>>, file: string}}
 */
function runGolden(name) {
  const file = `${ROOT}/src/${name}`;
  const src = fs.readFileSync(path.join(GOLDEN_DIR, name), 'utf8');
  const out = transformSource(src, file, { root: ROOT, ts, rtPath: RT });
  assert.ok(out, `${name}: expected a transform result`);
  return { src, out, file };
}

/**
 * @param {string} name
 * @returns {Record<string, unknown>[]}
 */
function instrumentedOf(name) {
  return /** @type {Record<string, unknown>[]} */ (runGolden(name).out.manifest.instrumented);
}

const inputs = goldenInputs();

test('the golden set is not empty', () => {
  assert.ok(inputs.length >= 13, `only ${inputs.length} goldens found`);
});

for (const name of inputs) {
  const expectedName = name.replace(/(\.[^.]+)$/, '.expected$1');

  test(`golden ${name}: byte-exact`, () => {
    const { src, out, file } = runGolden(name);
    const expected = fs.readFileSync(path.join(GOLDEN_DIR, expectedName), 'utf8');
    assert.equal(out.code, expected);
  });

  test(`golden ${name}: no edit inserts a newline`, () => {
    const { src, out } = runGolden(name);
    assert.equal(out.code.split('\n').length, src.split('\n').length);
  });

  test(`golden ${name}: input and output both parse clean`, () => {
    const { src, out, file } = runGolden(name);
    assert.deepEqual(parseDiagnosticsOf(file, src).map((d) => d.messageText), []);
    assert.deepEqual(parseDiagnosticsOf(file, out.code).map((d) => d.messageText), []);
  });

  test(`golden ${name}: manifest is well formed`, () => {
    const { src, out, file } = runGolden(name);
    assert.equal(out.manifest.file, file);
    assert.equal(out.manifest.rel, `src/${name}`);
    assert.equal(out.manifest.sha256, crypto.createHash('sha256').update(src).digest('hex'));
    for (const row of /** @type {Record<string, unknown>[]} */ (out.manifest.instrumented)) {
      assert.ok(typeof row.qualname === 'string' && row.qualname.length > 0);
      assert.ok(typeof row.line === 'number' && row.line >= 1);
      assert.ok(FRAME_KINDS.has(/** @type {string} */ (row.kind)), `kind ${String(row.kind)}`);
    }
    for (const reason of Object.keys(out.manifest.excluded)) {
      assert.ok(EXCLUSION_REASONS.has(reason), `unnamed exclusion ${reason}`);
    }
  });
}

test('qualnames: JavaScript spelling, file-local, no ordinals', () => {
  assert.deepEqual(instrumentedOf('qualnames.ts'), [
    { qualname: 'ns.fn', line: 2, kind: 'function' },
    { qualname: 'outer', line: 5, kind: 'function' },
    { qualname: 'outer.inner', line: 6, kind: 'function' },
    { qualname: 'onClick', line: 11, kind: 'function' },
    { qualname: 'onBlur', line: 12, kind: 'function' },
    { qualname: 'Store.reset', line: 15, kind: 'function' },
    { qualname: 'legacy', line: 16, kind: 'function' },
    { qualname: '<anonymous>', line: 18, kind: 'function' },
    { qualname: '<anonymous>', line: 20, kind: 'function' },
    { qualname: 'default', line: 24, kind: 'function' },
  ]);
});

test('class members: methods, constructor, and both accessors on their own lines', () => {
  assert.deepEqual(instrumentedOf('class.ts'), [
    { qualname: 'Fog.onTick', line: 3, kind: 'function' },
    { qualname: 'Fog.constructor', line: 7, kind: 'function' },
    { qualname: 'Fog.radius', line: 12, kind: 'function' },
    { qualname: 'Fog.radius', line: 16, kind: 'function' },
    { qualname: 'Fog.make', line: 20, kind: 'function' },
  ]);
});

test('frame kinds: async, generator, async generator', () => {
  assert.deepEqual(instrumentedOf('await.ts').map((r) => r.kind), ['coroutine', 'coroutine']);
  assert.deepEqual(instrumentedOf('yield.ts').map((r) => r.kind), ['generator', 'async_generator']);
});

test('vi.mock: nothing inside a hoisted factory is instrumented, and the count is named', () => {
  const { out } = runGolden('vi-mock.ts');
  assert.deepEqual(out.manifest.instrumented, [
    { qualname: 'useSeed', line: 11, kind: 'function' },
  ]);
  assert.deepEqual(out.manifest.excluded, { 'vitest-hoisted-factory': 3 });
});

test('bodiless functions are excluded, each under its own reason', () => {
  const { out } = runGolden('overloads.ts');
  assert.deepEqual(out.manifest.instrumented, [
    { qualname: 'pick', line: 3, kind: 'function' },
    { qualname: 'Shape.describeArea', line: 12, kind: 'function' },
  ]);
  assert.deepEqual(out.manifest.excluded, {
    'overload-signature': 2,
    ambient: 1,
    abstract: 1,
  });
});

test('a file with nothing to exclude reports an empty exclusion tally', () => {
  assert.deepEqual(runGolden('block-body.ts').out.manifest.excluded, {});
});

test('a call whose callback is not written inline is left alone', () => {
  // The lens has a local `describe(label, formula, value)` in ordinary source.
  // Wrapping on the callee's name alone would rewrite it and change what the
  // program does; only an inline arrow or function expression is a task.
  const { out } = runGolden('not-a-task.ts');
  assert.equal(out.code.includes('__srt.task('), false);
  assert.equal(out.code.includes('__srt.suite('), false);
  assert.deepEqual(out.manifest.instrumented, [
    { qualname: 'describe', line: 3, kind: 'function' },
  ]);
});

test('the runtime import path is spliced verbatim', () => {
  const src = fs.readFileSync(path.join(GOLDEN_DIR, 'block-body.ts'), 'utf8');
  const out = transformSource(src, `${ROOT}/src/block-body.ts`, {
    root: ROOT,
    ts,
    rtPath: '/tmp/sensorium/rt.mjs',
  });
  assert.ok(out);
  assert.ok(out.code.startsWith('import * as __srt from "/tmp/sensorium/rt.mjs";'));
});

test('a shebang and a directive prologue stay ahead of the header', () => {
  // `'use client'` stops being a directive the moment an import precedes it.
  assert.ok(runGolden('directive.ts').out.code.startsWith("'use client';import * as __srt"));
  assert.ok(runGolden('shebang.js').out.code.startsWith('#!/usr/bin/env node\nimport * as __srt'));
});

test('a hires source map is returned for the original file', () => {
  const { out, file } = runGolden('block-body.ts');
  assert.deepEqual(out.map.sources, [file]);
  assert.ok(out.map.mappings.length > 0);
});

test('classify: eligible extensions under the root', () => {
  for (const ext of ['.ts', '.tsx', '.js', '.jsx', '.mjs']) {
    assert.equal(classify(`${ROOT}/src/a${ext}`, ROOT), 'transform', ext);
  }
});

test('classify: CommonJS is skipped but counted', () => {
  assert.equal(classify(`${ROOT}/src/legacy.cjs`, ROOT), 'commonjs');
  assert.equal(transformSource('module.exports = 1;\n', `${ROOT}/src/legacy.cjs`, {
    root: ROOT, ts, rtPath: RT,
  }), null);
});

test('classify: outside the root, node_modules, declarations and unknown extensions are skipped', () => {
  assert.equal(classify('/elsewhere/src/a.ts', ROOT), 'skip');
  assert.equal(classify(`${ROOT}/node_modules/dep/index.js`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/nested/node_modules/dep/index.js`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/types.d.ts`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/styles.css`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/legacy.mts`, ROOT), 'skip');
});

test('transformSource returns null — no manifest — for every skipped path', () => {
  const opts = { root: ROOT, ts, rtPath: RT };
  const src = 'export function f(): void {}\n';
  assert.equal(transformSource(src, '/elsewhere/src/a.ts', opts), null);
  assert.equal(transformSource(src, `${ROOT}/node_modules/dep/index.js`, opts), null);
  assert.equal(transformSource(src, `${ROOT}/src/types.d.ts`, opts), null);
  assert.equal(transformSource(src, `${ROOT}/src/styles.css`, opts), null);
});
