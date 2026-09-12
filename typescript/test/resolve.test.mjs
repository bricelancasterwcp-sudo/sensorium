// The resolver, as the driver runs it: a real `node src/resolve.mjs` over a
// real directory, with the root and the specs in its environment and one JSON
// line on its stdout.
//
// The temporary root lives in the system temp directory, and its one
// `node_modules/typescript` is a symlink to the probe project's copy: the
// resolver resolves the consumer's own TypeScript from the ROOT, which is why
// these roots used to be written INSIDE `probes/` (CARRIED-DEBT's minor, and
// a run that died left `resolvetmp-*` directories inside the package). The
// symlink gives the root the one dependency it needs and leaves the package
// alone; the walk never enters a `node_modules`, so it changes nothing the
// resolver sees.
//
// What is pinned here is everything a refusal rests on: which files are walked
// at all, which function-likes are eligible, what an unmatched spec is offered
// instead, and what a spec that selected only functions this recorder never
// instruments is told. A resolver that quietly matched nothing would turn
// `--focus` into a whole-program recording; one that quietly matched an
// excluded function would refuse a run that had a perfectly good answer.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { SEP } from '../src/focus.mjs';
import { survey } from '../src/resolve.mjs';
import { sitesOf } from '../src/transform.mjs';

const PKG = fileURLToPath(new URL('../', import.meta.url));
const PROBES = path.join(PKG, 'probes');
const RESOLVE = path.join(PKG, 'src', 'resolve.mjs');

/**
 * A root in the system temp directory, with the files written into it and the
 * consumer's TypeScript linked in where a consumer's own would be.
 * @param {Record<string, string>} files
 * @returns {string} the root
 */
function writeRoot(files) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sensorium-resolve-'));
  for (const [rel, source] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
    fs.writeFileSync(path.join(root, rel), source);
  }
  fs.mkdirSync(path.join(root, 'node_modules'), { recursive: true });
  fs.symlinkSync(path.join(PROBES, 'node_modules', 'typescript'),
    path.join(root, 'node_modules', 'typescript'), 'dir');
  return root;
}

const require = createRequire(import.meta.url);
const ts = require('typescript');

/** A project with something of every kind the walk has to decide about. */
const FILES = {
  'package.json': '{"name": "resolvetmp", "type": "module"}\n',
  'src/cache.ts': [
    'export function refresh(): number {',
    '  return 1;',
    '}',
    '',
    'export function refreshAll(): number {',
    '  return refresh();',
    '}',
    '',
  ].join('\n'),
  'src/fog.ts': [
    'export class Fog {',
    '  compute(): number {',
    '    return 1;',
    '  }',
    '',
    '  render(): number {',
    '    return this.compute();',
    '  }',
    '}',
    '',
  ].join('\n'),
  // Two function-likes this recorder never instruments, and no eligible one
  // in sight: an ambient declaration and an abstract method.
  'src/decl.ts': [
    "declare module 'legacy-dep' {",
    '  export function legacy(a: number): number;',
    '  export function legacy(a: string): string;',
    '}',
    '',
    'export abstract class Shape {',
    '  abstract area(): number;',
    '}',
    '',
    // An overload signature with no implementation under it: the type
    // checker's problem, not this recorder's, and a function-like with no
    // body either way.
    'export function orphan(a: number): number;',
    '',
  ].join('\n'),
  // Overload signatures BESIDE an implementation: the excluded ones must not
  // hide the eligible one.
  'src/pick.ts': [
    'export function pick(a: number): number;',
    'export function pick(a: string): string;',
    'export function pick(a: unknown): unknown {',
    '  return a;',
    '}',
    '',
  ].join('\n'),
  'src/broken.ts': 'export function broken(): void {\n  g(\n}\n',
  // Neither of these is walked, and each holds a name nothing else does.
  'src/legacy.cjs': 'function hiddenInCjs() {}\nmodule.exports = { hiddenInCjs };\n',
  'node_modules/dep/index.js': 'export function hiddenInDep() {}\n',
  '.sensorium/tmp.ts': 'export function hiddenInSensorium(): void {}\n',
};

/**
 * Run the resolver over a written root and read its one line back.
 * @param {string[]} specs
 * @param {Record<string, string>} [files]
 * @param {Record<string, string|undefined>} [env] variables to add or remove
 * @returns {{res: import('node:child_process').SpawnSyncReturns<string>, json: any}}
 */
function resolve(specs, files = FILES, env = {}) {
  const root = writeRoot(files);
  try {
    // The child's environment is decided here and not inherited: a shell that
    // exported SENSORIUM_FOCUS would otherwise answer a different question.
    const inherited = { ...process.env };
    delete inherited.SENSORIUM_FOCUS;
    delete inherited.SENSORIUM_TS_ROOT;
    /** @type {Record<string, string>} */
    const vars = {
      ...inherited,
      SENSORIUM_TS_ROOT: root,
      SENSORIUM_TS_PKG: PKG,
      SENSORIUM_FOCUS: specs.join(SEP),
    };
    for (const [key, value] of Object.entries(env)) {
      if (value === undefined) delete vars[key];
      else vars[key] = value;
    }
    const res = spawnSync(process.execPath, [RESOLVE], {
      encoding: 'utf8',
      timeout: 30_000,
      env: vars,
      cwd: root,
    });
    let json = null;
    if (res.stdout.trim() !== '') json = JSON.parse(res.stdout);
    return { res, json };
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

test('a spec matching one function answers with that function alone', () => {
  const { res, json } = resolve(['cache.ts:refresh']);
  assert.equal(res.status, 0, res.stderr);
  assert.deepEqual(json.matched, [
    { rel: 'src/cache.ts', qualname: 'refresh', line: 1, kind: 'function', deferred: false },
  ]);
  assert.deepEqual(json.unmatched, []);
  assert.deepEqual(json.excluded_only, []);
  assert.equal(res.stdout.trimEnd().includes('\n'), false, 'one line');
});

test('a container spec matches every member under it', () => {
  const { json } = resolve(['Fog']);
  assert.deepEqual(json.matched, [
    { rel: 'src/fog.ts', qualname: 'Fog.compute', line: 2, kind: 'function', deferred: false },
    { rel: 'src/fog.ts', qualname: 'Fog.render', line: 6, kind: 'function', deferred: false },
  ]);
});

test('two specs selecting one function report it once', () => {
  const { json } = resolve(['refresh', 'cache.ts:refresh']);
  assert.deepEqual(json.matched.map((/** @type {any} */ m) => m.qualname), ['refresh']);
  assert.deepEqual(json.unmatched, []);
});

test('an unmatched spec is offered the closest eligible names', () => {
  const { json } = resolve(['Fig.compute']);
  assert.deepEqual(json.matched, []);
  assert.equal(json.unmatched.length, 1);
  assert.equal(json.unmatched[0].spec, 'Fig.compute');
  // `Fog.compute` shares the trailing segment; the rest share nothing and
  // follow it by name.
  assert.equal(json.unmatched[0].closest[0], 'Fog.compute');
  assert.ok(json.unmatched[0].closest.length <= 3);
});

test('a spec selecting only functions this recorder excludes says which', () => {
  const { json } = resolve(['legacy', 'Shape', 'orphan']);
  assert.deepEqual(json.matched, []);
  assert.deepEqual(json.unmatched, []);
  assert.deepEqual(json.excluded_only, [
    { spec: 'legacy', reasons: { ambient: 2 } },
    { spec: 'Shape', reasons: { abstract: 1 } },
    { spec: 'orphan', reasons: { 'overload-signature': 1 } },
  ]);
});

test('an overload signature never hides the implementation beside it', () => {
  const { json } = resolve(['pick']);
  assert.deepEqual(json.matched, [
    { rel: 'src/pick.ts', qualname: 'pick', line: 3, kind: 'function', deferred: false },
  ]);
  assert.deepEqual(json.excluded_only, []);
});

test('a .cjs, a node_modules file and a .sensorium file are not walked', () => {
  const { json } = resolve(['hiddenInCjs', 'hiddenInDep', 'hiddenInSensorium']);
  assert.deepEqual(json.matched, []);
  assert.deepEqual(json.unmatched.map((/** @type {any} */ u) => u.spec),
    ['hiddenInCjs', 'hiddenInDep', 'hiddenInSensorium']);
  // cache.ts, fog.ts, decl.ts, pick.ts, broken.ts -- and nothing else.
  assert.equal(json.files_scanned, 5);
});

test('a file that does not parse is counted and offers nothing', () => {
  const { json } = resolve(['broken']);
  assert.equal(json.files_unparsable, 1);
  assert.deepEqual(json.matched, []);
  assert.equal(json.unmatched.length, 1);
});

test('a root with no eligible function at all is offered nothing', () => {
  const { json } = resolve(['whatever'], {
    'package.json': '{"name": "empty", "type": "module"}\n',
    'src/types.ts': 'export type A = { a: number };\n',
  });
  assert.deepEqual(json.unmatched, [{ spec: 'whatever', closest: [] }]);
  assert.equal(json.files_scanned, 1);
});

test('an unspellable name is never suggested', () => {
  const { json } = resolve(['nope'], {
    'package.json': '{"name": "cb", "type": "module"}\n',
    'src/a.test.ts': [
      "import { describe, test } from 'node:test';",
      '',
      "describe('outer', () => {",
      "  test('inner', () => {});",
      '});',
      '',
      'export function named(): void {}',
      '',
    ].join('\n'),
  });
  // The callbacks are `<anonymous>` and `<anonymous>.<anonymous>`, which sort
  // first and which no caller can type: a suggestion is a name to retype.
  assert.deepEqual(json.unmatched, [{ spec: 'nope', closest: ['named'] }]);
});

test('a missing variable is one line on stderr and exit 2, with no JSON', () => {
  const { res, json } = resolve(['refresh'], FILES, { SENSORIUM_TS_ROOT: undefined });
  assert.equal(res.status, 2);
  assert.equal(json, null);
  assert.equal(res.stderr.trimEnd().split('\n').length, 1, res.stderr);
  assert.match(res.stderr, /SENSORIUM_TS_ROOT/);
});

test('an empty focus is refused rather than walking the tree for nothing', () => {
  const { res } = resolve([]);
  assert.equal(res.status, 2);
  assert.match(res.stderr, /SENSORIUM_FOCUS/);
});

test('a root that is not a directory is one line on stderr and exit 2', () => {
  const { res } = resolve(['refresh'], FILES,
    { SENSORIUM_TS_ROOT: path.join(PROBES, 'no-such-root') });
  assert.equal(res.status, 2);
  assert.equal(res.stderr.trimEnd().split('\n').length, 1, res.stderr);
  assert.match(res.stderr, /no-such-root/);
});

// --- what pass one tells the resolver about the functions it skipped --------

test('an excluded function-like is named, placed and reasoned (R26)', () => {
  const src = [
    'export function pick(a: number): number;',
    'export function pick(a: string): string;',
    'export function pick(a: unknown): unknown {',
    '  return a;',
    '}',
    '',
    'declare function ambient(): void;',
    '',
  ].join('\n');
  const out = sitesOf(src, '/w/src/a.ts', { root: '/w', ts });
  assert.ok(out);
  assert.deepEqual(out.sites, [{ qualname: 'pick', line: 3, kind: 'function', focused: false, deferred: false }]);
  assert.deepEqual(out.excluded, { 'overload-signature': 2, ambient: 1 });
  assert.deepEqual(out.excludedSites, [
    { qualname: 'pick', line: 1, reason: 'overload-signature' },
    { qualname: 'pick', line: 2, reason: 'overload-signature' },
    { qualname: 'ambient', line: 7, reason: 'ambient' },
  ]);
});

test('a file that does not parse has no excluded sites to name', () => {
  const out = sitesOf('export function f() {\n  g(\n}\n', '/w/src/a.ts', { root: '/w', ts });
  assert.ok(out);
  assert.deepEqual(out.excludedSites, []);
});

// --- what the resolver says about the seal, and what it survives -----------

test('every matched function says whether its exit is deferred', () => {
  // `deferred` rides the site (design §4.2, plan A3), so the answer a caller
  // gets before the run says which functions the seal will change. It is not
  // a focus question: an unfocused run's wrappers move for the same shape.
  const { res, json } = resolve(['seal.ts:plain', 'seal.ts:settle'], {
    'package.json': '{"name": "sealtmp", "type": "module"}\n',
    'src/seal.ts': [
      'export function plain(): number {',
      '  return 1;',
      '}',
      '',
      'export function settle(): number {',
      '  try {',
      '    return 1;',
      '  } finally {',
      '    cleanup();',
      '  }',
      '}',
      '',
    ].join('\n'),
  });

  assert.equal(res.status, 0, res.stderr);
  assert.deepEqual(json.matched, [
    { rel: 'src/seal.ts', qualname: 'plain', line: 1, kind: 'function', deferred: false },
    { rel: 'src/seal.ts', qualname: 'settle', line: 5, kind: 'function', deferred: true },
  ]);
});

test('a file the consumer’s TypeScript throws on is counted, named, and walked past', () => {
  // The minor CARRIED-DEBT named: `sitesOf` runs the consumer's own parser
  // over a file this recorder did not write, and a throw from it took the
  // whole resolution down — a focus nobody could resolve because ONE file in
  // the tree was unreadable. It is now what an unparsable file always was:
  // a file that offered no sites, counted so the numbers reconcile, and
  // named on stderr so it is not a silent subtraction.
  const root = writeRoot({
    'package.json': '{"name": "throwtmp", "type": "module"}\n',
    'src/good.ts': 'export function good(): number {\n  return 1;\n}\n',
    'src/bad.ts': 'export function bad(): number {\n  return 2;\n}\n',
  });
  /** @type {string[]} */
  const errs = [];
  const real = process.stderr.write.bind(process.stderr);
  process.stderr.write = /** @type {any} */ ((/** @type {unknown} */ chunk) => {
    errs.push(String(chunk));
    return true;
  });
  /** @type {ReturnType<typeof survey>} */
  let out;
  try {
    out = survey(root, ts, {
      sitesOf: (/** @type {string} */ code, /** @type {string} */ file,
        /** @type {any} */ opts) => {
        if (file.endsWith('bad.ts')) throw new Error('consumer typescript threw');
        return sitesOf(code, file, opts);
      },
    });
  } finally {
    process.stderr.write = real;
    fs.rmSync(root, { recursive: true, force: true });
  }

  assert.equal(out.unparsable, 1);
  assert.equal(out.scanned, 2);
  assert.deepEqual(out.eligible.map((site) => site.qualname), ['good']);
  assert.equal(errs.length, 1, errs.join(''));
  assert.match(errs[0], /src\/bad\.ts/);
  assert.match(errs[0], /consumer typescript threw/);
});
