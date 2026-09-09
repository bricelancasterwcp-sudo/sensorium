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
 * @returns {{src: string, out: NonNullable<ReturnType<typeof transformSource>>, file: string, code: string}}
 */
function runGolden(name) {
  const file = `${ROOT}/src/${name}`;
  const src = fs.readFileSync(path.join(GOLDEN_DIR, name), 'utf8');
  const out = transformSource(src, file, { root: ROOT, ts, rtPath: RT });
  assert.ok(out, `${name}: expected a transform result`);
  const code = out.code;
  assert.ok(code !== null, `${name}: parsed clean, so it must carry instrumented code`);
  return { src, out, file, code };
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
    const { code } = runGolden(name);
    const expected = fs.readFileSync(path.join(GOLDEN_DIR, expectedName), 'utf8');
    assert.equal(code, expected);
  });

  test(`golden ${name}: no edit inserts a newline`, () => {
    const { src, code } = runGolden(name);
    assert.equal(code.split('\n').length, src.split('\n').length);
  });

  test(`golden ${name}: input and output both parse clean`, () => {
    const { src, code, file } = runGolden(name);
    assert.deepEqual(parseDiagnosticsOf(file, src).map((d) => d.messageText), []);
    assert.deepEqual(parseDiagnosticsOf(file, code).map((d) => d.messageText), []);
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
    // R11: `module.exports = fn` is the module's default export, named as
    // `export default` is; `module.exports.x = fn` keeps the property's name.
    { qualname: 'default', line: 17, kind: 'function' },
    { qualname: '<anonymous>', line: 19, kind: 'function' },
    { qualname: '<anonymous>', line: 21, kind: 'function' },
    { qualname: 'default', line: 25, kind: 'function' },
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

test('R8: ordinary source is never wrapped, whatever the callback shape', () => {
  // The lens has a local `describe(label, formula, value)` in ordinary source.
  // Neither it, nor a call passing an inline arrow, nor `test(title, ident)` is
  // a task here: this file imports no harness and is not named like a test.
  const { code, out } = runGolden('not-a-task.ts');
  assert.equal(code.includes('__srt.task('), false);
  assert.equal(code.includes('__srt.suite('), false);
  assert.ok(code.includes('const mapped = describe("x", () => {const __sf='));
  assert.ok(code.includes('test("shared", sharedCase);'));
  assert.deepEqual(out.manifest.instrumented, [
    { qualname: 'describe', line: 3, kind: 'function' },
    { qualname: '<anonymous>', line: 9, kind: 'function' },
  ]);
});

test('R8: inside a test file every second argument is wrapped, identifiers too', () => {
  const { code } = runGolden('identifier-callback.test.ts');
  assert.ok(code.includes('test(...__srt.task(("identifier callback"), sharedCase,1));'));
  assert.ok(code.includes('it.each(table)(...__srt.task(("row %s"), sharedCase,3));'));
  assert.ok(code.includes('describe(...__srt.suite(("shared"),'));
});

test('R8a: an options object stays put and the callback is the third argument', () => {
  const { code } = runGolden('options-object.test.ts');
  const lines = code.split('\n');
  assert.ok(lines[2].startsWith('describe(...__srt.suite(("options"), { concurrent: true }, () => {'));
  assert.ok(lines[3].startsWith('  test(...__srt.task(("times out"), { timeout: 100 }, () => {'));
  // flags close the wrap, and the call's own later arguments stay outside it.
  assert.ok(lines[5].endsWith('},1), 5000);'), lines[5]);
  assert.ok(lines[6].endsWith('}), 1000);'), lines[6]);
  // an options object spanning lines is spliced like any other: it never moves
  assert.equal(lines[8], 'test(...__srt.task(("options across lines"), {');
  assert.equal(lines[9], '  timeout: 100,');
  assert.ok(lines[10].startsWith('}, () => {const __sf='));
});

test('R8c: a closer on our offset is spliced inside ours, not around it', () => {
  // The boundary's two closers are registered before the call's children are
  // visited, and `prependRight` renders in reverse registration order, so an
  // arrow title, a conditional callback and an `await` all close first.
  const { code } = runGolden('task-boundaries.test.ts');
  const lines = code.split('\n');
  assert.ok(
    lines[2].endsWith('throw __se}}), { timeout: 1 }, fn2,0));'),
    lines[2],
  );
  assert.ok(lines[4].endsWith('throw __se}},1));'), lines[4]);
  assert.equal(
    lines[7],
    '  test(...__srt.task(("e"), { timeout: 1 }, __srt.r(__sf,await __srt.y(__sf,(mk()),0)),1));',
  );
  // the same three shapes in the two-argument form
  assert.ok(lines[10].endsWith('throw __se}}), fn2,0));'), lines[10]);
  assert.ok(lines[12].endsWith('throw __se}},1));'), lines[12]);
  assert.equal(
    lines[15],
    '  test(...__srt.task(("f3"), __srt.r(__sf,await __srt.y(__sf,(mk()),0)),1));',
  );
});

test('R8a: `test(name, options)` with no callback is not a task', () => {
  const source = 'import { test } from "vitest";\ntest("x", { timeout: 1 });\n';
  const out = transformSource(source, `${ROOT}/src/a.ts`, { root: ROOT, ts, rtPath: RT });
  assert.ok(out && out.code !== null);
  assert.equal(out.code.includes('__srt.task('), false);
});

test('R8b: a type-only harness import does not make a test file', () => {
  const source = [
    'import type { Mock } from "vitest";',
    '',
    'export function label(): string {',
    '  return describe("shape", make, 2);',
    '}',
    '',
  ].join('\n');
  const out = transformSource(source, `${ROOT}/src/helpers.ts`, { root: ROOT, ts, rtPath: RT });
  assert.ok(out && out.code !== null);
  assert.equal(out.code.includes('__srt.suite('), false);
  assert.ok(out.code.includes('return __srt.ret(__sf,(describe("shape", make, 2)));'));
});

test('R10a: a TypeScript build with no parseDiagnostics is refused, not trusted', () => {
  const blind = /** @type {any} */ ({
    ...ts,
    /** @param {any[]} args */
    createSourceFile: (...args) => {
      const sf = /** @type {any} */ (/** @type {any} */ (ts.createSourceFile)(...args));
      delete sf.parseDiagnostics;
      return sf;
    },
  });
  assert.throws(
    () =>
      transformSource('export function f(): void {}\n', `${ROOT}/src/a.ts`, {
        root: ROOT,
        ts: blind,
        rtPath: RT,
      }),
    /** @param {unknown} err */
    (err) =>
      err instanceof Error &&
      err.message ===
        'sensorium-ts: this TypeScript build exposes no parseDiagnostics; refusing to transform blind',
  );
});

test('R8: a test file is one named like one, or one that imports a harness', () => {
  const opts = { root: ROOT, ts, rtPath: RT };
  /** @param {string} body @param {string} name */
  const wrapped = (body, name) => {
    const out = transformSource(body, `${ROOT}/src/${name}`, opts);
    assert.ok(out && out.code !== null);
    return out.code.includes('__srt.task(');
  };
  const call = 'test("t", () => {});\n';
  assert.equal(wrapped(call, 'helpers.ts'), false);
  assert.equal(wrapped(call, 'helpers.test.ts'), true);
  assert.equal(wrapped(call, 'helpers.spec.tsx'), true);
  assert.equal(wrapped(`import { test } from "vitest";\n${call}`, 'helpers.ts'), true);
  assert.equal(wrapped(`import { test } from "node:test";\n${call}`, 'helpers.ts'), true);
  assert.equal(wrapped(`const { test } = require("@jest/globals");\n${call}`, 'helpers.ts'), true);
  assert.equal(wrapped(`await import("vitest");\n${call}`, 'helpers.ts'), true);
  assert.equal(wrapped(`import { test } from "./local";\n${call}`, 'helpers.ts'), false);
  // R8b: a type-only import brings no `test` to call.
  assert.equal(wrapped(`import type { Mock } from "vitest";\n${call}`, 'helpers.ts'), false);
  assert.equal(wrapped(`import { type Mock } from "vitest";\n${call}`, 'helpers.ts'), false);
  assert.equal(wrapped(`import { type Mock, test } from "vitest";\n${call}`, 'helpers.ts'), true);
  assert.equal(wrapped(`import Runner, { type Mock } from "vitest";\n${call}`, 'helpers.ts'), true);
  assert.equal(wrapped(`import "vitest";\n${call}`, 'helpers.ts'), true);
});

test('R12: a statement-level bare `yield` and `return` keep ASI\'s semicolon', () => {
  // Without it the next line joins the spliced expression: `return\n(g)()` would
  // call the result of `ret(...)` — a TypeError where the original returned.
  const { code } = runGolden('asi.ts');
  const lines = code.split('\n');
  assert.equal(lines[1], '  __srt.r(__sf,yield __srt.y(__sf,(undefined),1));');
  assert.equal(lines[2], '  (g)()');
  assert.equal(lines[6], '  if (flag) return __srt.ret(__sf,undefined);');
  assert.equal(lines[7], '  (g)()');
});

test('R12: a bare `yield`/`return` that already has a semicolon gets no second', () => {
  const { code } = runGolden('yield.ts');
  assert.ok(code.includes('__srt.r(__sf,yield __srt.y(__sf,(undefined),1));'));
  assert.equal(code.includes(';;'), false);
  assert.equal(runGolden('block-body.ts').code.includes('undefined);;'), false);
});

test('R12: a nested bare `yield` takes no terminator', () => {
  const src = 'export function* g(): Generator<void> {\n  const x = yield;\n  use(x);\n}\n';
  const out = transformSource(src, `${ROOT}/src/nested-yield.ts`, { root: ROOT, ts, rtPath: RT });
  assert.ok(out && out.code !== null);
  assert.ok(out.code.includes('const x = __srt.r(__sf,yield __srt.y(__sf,(undefined),1));'));
  assert.equal(out.code.includes(';;'), false);
});

test('the runtime import path is spliced verbatim', () => {
  const src = fs.readFileSync(path.join(GOLDEN_DIR, 'block-body.ts'), 'utf8');
  const out = transformSource(src, `${ROOT}/src/block-body.ts`, {
    root: ROOT,
    ts,
    rtPath: '/tmp/sensorium/rt.mjs',
  });
  assert.ok(out);
  assert.ok(out.code !== null);
  assert.ok(out.code.startsWith('import * as __srt from "/tmp/sensorium/rt.mjs";'));
});

test('a shebang and a directive prologue stay ahead of the header', () => {
  // `'use client'` stops being a directive the moment an import precedes it.
  assert.ok(runGolden('directive.ts').code.startsWith("'use client';import * as __srt"));
  assert.ok(runGolden('shebang.js').code.startsWith('#!/usr/bin/env node\nimport * as __srt'));
  // A prologue written without its semicolon must be given one, or the header
  // is glued to it and the file stops parsing.
  assert.ok(runGolden('directive-nosemi.ts').code.startsWith("'use client';import * as __srt"));
  assert.ok(
    runGolden('shebang-directive.js').code
      .startsWith("#!/usr/bin/env node\n'use strict';import * as __srt"),
  );
});

test('a hires source map is returned for the original file', () => {
  const { out, file } = runGolden('block-body.ts');
  const map = out.map;
  assert.ok(map, 'a file that parsed clean carries a map');
  assert.deepEqual(map.sources, [file]);
  assert.ok(map.mappings.length > 0);
});

test('classify: eligible extensions under the root', () => {
  for (const ext of ['.ts', '.tsx', '.mts', '.js', '.jsx', '.mjs']) {
    assert.equal(classify(`${ROOT}/src/a${ext}`, ROOT), 'transform', ext);
  }
});

test('classify: CommonJS is skipped but counted — R9, `.cts` with `.cjs`', () => {
  for (const ext of ['.cjs', '.cts']) {
    assert.equal(classify(`${ROOT}/src/legacy${ext}`, ROOT), 'commonjs', ext);
    assert.equal(transformSource('module.exports = 1;\n', `${ROOT}/src/legacy${ext}`, {
      root: ROOT, ts, rtPath: RT,
    }), null, ext);
  }
});

test('classify: outside the root, node_modules, declarations and unknown extensions are skipped', () => {
  assert.equal(classify('/elsewhere/src/a.ts', ROOT), 'skip');
  assert.equal(classify(`${ROOT}/node_modules/dep/index.js`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/nested/node_modules/dep/index.js`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/types.d.ts`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/styles.css`, ROOT), 'skip');
  assert.equal(classify(`${ROOT}/src/types.d.mts`, ROOT), 'skip');
});

test('R9: `.mts` transforms exactly as `.ts`', () => {
  const src = 'export function f(): number {\n  return 1;\n}\n';
  assert.equal(classify(`${ROOT}/src/a.mts`, ROOT), 'transform');
  const mts = transformSource(src, `${ROOT}/src/a.mts`, { root: ROOT, ts, rtPath: RT });
  const tsFile = transformSource(src, `${ROOT}/src/a.ts`, { root: ROOT, ts, rtPath: RT });
  assert.ok(mts && tsFile && mts.code !== null && tsFile.code !== null);
  assert.equal(mts.code.replace('a.mts', 'a.ts').replace('a.mts', 'a.ts'), tsFile.code);
  assert.deepEqual(mts.manifest.instrumented, [{ qualname: 'f', line: 1, kind: 'function' }]);
});

test('R10: a file that does not parse is reported, never spliced', () => {
  const broken = 'export function f() {\n  g(\n}\n';
  const out = transformSource(broken, `${ROOT}/src/broken.ts`, { root: ROOT, ts, rtPath: RT });
  assert.ok(out, 'a parse failure is still ours: a manifest, not a bare null');
  assert.equal(out.code, null);
  assert.equal(out.map, null);
  assert.deepEqual(out.manifest.excluded, { 'parse-error': 1 });
  assert.deepEqual(out.manifest.instrumented, []);
  assert.equal(out.manifest.rel, 'src/broken.ts');
  assert.equal(out.manifest.sha256, crypto.createHash('sha256').update(broken).digest('hex'));
  const diagnostics = out.manifest.diagnostics;
  assert.ok(diagnostics && diagnostics.length > 0 && diagnostics.length <= 3);
  assert.ok(diagnostics.every((d) => typeof d === 'string'));
});

test('transformSource returns null — no manifest — for every skipped path', () => {
  const opts = { root: ROOT, ts, rtPath: RT };
  const src = 'export function f(): void {}\n';
  assert.equal(transformSource(src, '/elsewhere/src/a.ts', opts), null);
  assert.equal(transformSource(src, `${ROOT}/node_modules/dep/index.js`, opts), null);
  assert.equal(transformSource(src, `${ROOT}/src/types.d.ts`, opts), null);
  assert.equal(transformSource(src, `${ROOT}/src/styles.css`, opts), null);
});
