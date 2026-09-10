// The `node --test` loader hook, end to end. The probe project runs a whole
// TypeScript file through it; what is pinned here is the branching a green
// probe run cannot show: a `.mjs` under the root is instrumented with nothing to
// strip, a file outside the root is not touched at all, and `register.mjs`
// refuses rather than installing a hook with no scope.
//
// The temporary root lives under `probes/`, because the hook resolves the
// consumer's own `typescript` from it and that is where a copy exists.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { VERSION } from '../src/index.mjs';

const PKG = fileURLToPath(new URL('../', import.meta.url));
const PROBES = path.join(PKG, 'probes');
const REGISTER = path.join(PKG, 'src', 'register.mjs');

/**
 * Write a root, run one module under the hook, and read the spool back.
 * @param {Record<string, string>} files path relative to the root -> source
 * @param {string} entry the module to import, relative to the root
 * @param {Record<string, string>} [env] variables to add or blank out
 * @param {{hook?: boolean}} [opts] `hook: false` runs the same program with no
 *   recorder at all -- the control every "as it fails plain" claim needs
 */
function run(files, entry, env = {}, { hook = true } = {}) {
  const root = fs.mkdtempSync(path.join(PROBES, 'hooktmp-'));
  const spool = path.join(root, 'spool');
  const manifests = path.join(root, 'manifests');
  try {
    for (const [rel, source] of Object.entries(files)) {
      fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
      fs.writeFileSync(path.join(root, rel), source);
    }
    const target = path.join(root, entry);
    const argv = hook ? ['--import', REGISTER, target] : [target];
    const res = spawnSync(process.execPath, argv, {
      encoding: 'utf8',
      timeout: 30_000,
      env: {
        ...process.env,
        SENSORIUM_TIER: 'call',
        SENSORIUM_SPOOL: spool,
        SENSORIUM_TS_ROOT: root,
        SENSORIUM_TS_PKG: PKG,
        SENSORIUM_MANIFEST_DIR: manifests,
        ...env,
      },
    });
    const spooled = fs.existsSync(spool) ? fs.readdirSync(spool) : [];
    const recs = spooled.flatMap((name) => fs.readFileSync(path.join(spool, name), 'utf8')
      .split('\n').filter((line) => line !== '').map((line) => JSON.parse(line)));
    return { res, recs, tally: readTally(manifests) };
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

/**
 * The one tally this child wrote, or null. Named `_tally-<pid>.json` by the
 * hook, because `node --test` runs one child process per test file and a
 * shared name would be several writers over one number.
 * @param {string} manifests
 * @returns {{files_transformed: number, excluded: Record<string, number>}|null}
 */
function readTally(manifests) {
  if (!fs.existsSync(manifests)) return null;
  const names = fs.readdirSync(manifests).filter((n) => n.startsWith('_tally'));
  if (names.length !== 1) return null;
  return JSON.parse(fs.readFileSync(path.join(manifests, names[0]), 'utf8'));
}

/** @param {any[]} recs @returns {string[]} the root-relative files it recorded */
const filesOf = (recs) => recs.filter((r) => r.e === 'FILE').map((r) => r.rel).sort();

/** @param {any[]} recs @returns {string[]} every called function's qualname */
function called(recs) {
  const byId = new Map(recs.filter((r) => r.e === 'FILE').map((r) => [r.id, r]));
  return recs.filter((r) => r.e === 'CALL').map((r) => byId.get(r.file).codes[r.c][0]).sort();
}

test('a `.mjs` under the root is instrumented, with no types to erase', () => {
  const out = run({
    'main.mjs': "import { helper } from './lib.mjs';\nconsole.log(helper(1));\n",
    'lib.mjs': 'export function helper(x) {\n  return x + 1;\n}\n',
  }, 'main.mjs');
  assert.equal(out.res.status, 0, out.res.stderr);
  assert.equal(out.res.stdout.trim(), '2');
  assert.deepEqual(filesOf(out.recs), ['lib.mjs', 'main.mjs']);
  assert.deepEqual(called(out.recs), ['helper']);
});

test('a `.ts` under the root is instrumented and type-stripped', () => {
  const out = run({
    'main.ts': "import { helper } from './lib.ts';\nconsole.log(helper(1));\n",
    'lib.ts': 'export function helper(x: number): number {\n  return x + 1;\n}\n',
  }, 'main.ts');
  assert.equal(out.res.status, 0, out.res.stderr);
  assert.equal(out.res.stdout.trim(), '2');
  assert.deepEqual(filesOf(out.recs), ['lib.ts', 'main.ts']);
  assert.deepEqual(called(out.recs), ['helper']);
  // Positions are the source's own: the transform ran before anything erased a
  // type, and no edit it made carried a newline.
  const lib = out.recs.find((r) => r.e === 'FILE' && r.rel === 'lib.ts');
  assert.deepEqual(lib.codes, [['helper', 1, 'function']]);
});

test('a module outside the root is loaded, and recorded by nobody', () => {
  // This package's own `index.mjs`: a real ES module, outside the root the hook
  // was given, so it loads untouched and declares no file.
  const outside = pathToFileURL(path.join(PKG, 'src', 'index.mjs')).href;
  const out = run({
    'main.mjs': `import { VERSION } from ${JSON.stringify(outside)};\nconsole.log(VERSION);\n`,
  }, 'main.mjs');
  assert.equal(out.res.status, 0, out.res.stderr);
  assert.equal(out.res.stdout.trim(), VERSION);
  assert.deepEqual(filesOf(out.recs), ['main.mjs']);
});

test('register.mjs refuses to install a hook with no scope', () => {
  for (const missing of ['SENSORIUM_TS_ROOT', 'SENSORIUM_TS_PKG']) {
    const out = run({ 'main.mjs': "console.log('ran');\n" }, 'main.mjs', { [missing]: '' });
    assert.notEqual(out.res.status, 0);
    assert.match(out.res.stderr, new RegExp(`${missing} is not set`));
    assert.equal(out.res.stdout.includes('ran'), false);
  }
});

test('R37: a CommonJS file under the root is loaded as Node loads it, and counted', () => {
  // The package has no `"type"` field, so `add.js` is whatever it parses as --
  // and it parses as CommonJS. Forcing the default load to `format: 'module'`
  // spliced an `import` header into a file full of `require` calls: a suite
  // that passes under plain `node --test` failed under the recorder with
  // `require is not defined in ES module scope`, while HONESTY section 7 said
  // such a file was "excluded and counted". Node decides the format now.
  const out = run({
    'package.json': '{"name": "untyped"}\n',
    'add.js': "const os = require('node:os');\n"
      + 'function add(a, b) { return a + b; }\n'
      + 'module.exports = { add, arch: typeof os.arch };\n',
    'main.mjs': "const cjs = await import('./add.js');\n"
      + 'console.log(cjs.default.add(1, 2), cjs.default.arch);\n',
  }, 'main.mjs');
  assert.equal(out.res.status, 0, out.res.stderr);
  assert.equal(out.res.stdout.trim(), '3 function');
  // Untouched: it declared no FILE record, because it was never instrumented.
  assert.deepEqual(filesOf(out.recs), ['main.mjs']);
  // And not silently absent either: excluded BY NAME, beside the one file that
  // was transformed.
  assert.deepEqual(out.tally, { files_transformed: 1, excluded: { commonjs: 1 } });
});

test('R37: a `.cjs` under the root is counted without being parsed at all', () => {
  // The other half of the CommonJS verdict: this one `classify` reaches from
  // the extension, before Node is asked anything. It was passed through
  // uncounted, so the run's coverage number said nothing about it.
  const out = run({
    'package.json': '{"name": "untyped"}\n',
    'helper.cjs': 'module.exports = { two: () => 2 };\n',
    'main.mjs': "const h = await import('./helper.cjs');\n"
      + 'console.log(h.default.two());\n',
  }, 'main.mjs');
  assert.equal(out.res.status, 0, out.res.stderr);
  assert.equal(out.res.stdout.trim(), '2');
  assert.deepEqual(filesOf(out.recs), ['main.mjs']);
  assert.deepEqual(out.tally, { files_transformed: 1, excluded: { commonjs: 1 } });
});

test('an ES module under the root still carries its own count', () => {
  // The count the plugin has always written, now written by this hook too:
  // before R37 a `node --test` trace carried no coverage number at all.
  const out = run({
    'main.mjs': "import { helper } from './lib.mjs';\nconsole.log(helper(1));\n",
    'lib.mjs': 'export function helper(x) {\n  return x + 1;\n}\n',
  }, 'main.mjs');
  assert.equal(out.res.status, 0, out.res.stderr);
  assert.deepEqual(out.tally, { files_transformed: 2, excluded: {} });
});

/** The first error code a run printed, or null: what two sides compare on. */
const codeOf = (/** @type {string} */ stderr) => (stderr.match(/ERR_[A-Z_]+/) ?? [null])[0];

test('a `.mts` under the root is instrumented and stripped by Node', () => {
  // The R46 residual, closed. `STRIP` held `.ts` and `.tsx`, so an eligible
  // `.mts` was instrumented, handed back with its types still in it, and Node
  // threw a SyntaxError on the first annotation it met. Node's OWN reported
  // format goes back now (`module-typescript`), and Node strips it with the
  // stripper plain `node --test` already uses.
  const out = run({
    'main.mts': "import { helper } from './lib.mts';\nconsole.log(helper(1));\n",
    'lib.mts': 'export function helper(x: number): number {\n  return x + 1;\n}\n',
  }, 'main.mts');
  assert.equal(out.res.status, 0, out.res.stderr);
  assert.equal(out.res.stdout.trim(), '2');
  assert.deepEqual(filesOf(out.recs), ['lib.mts', 'main.mts']);
  assert.deepEqual(called(out.recs), ['helper']);
});

test('the hook erases nothing: a construct strip-only mode rejects fails as it fails plain', () => {
  // H1's falsifier. An `enum` has runtime meaning, so Node's strip-only mode
  // refuses it by name; the old hook ran `transpileModule` over the file and
  // EMITTED one, so the recorder made a program load that plain `node` will
  // not load. A recorder that changes what loads is changing the program.
  const files = {
    'main.ts': "import { Colour } from './lib.ts';\nconsole.log(Colour.Red);\n",
    'lib.ts': 'export enum Colour {\n  Red = 1,\n}\n',
  };
  const out = run(files, 'main.ts');
  const plain = run(files, 'main.ts', {}, { hook: false });
  assert.equal(codeOf(plain.res.stderr), 'ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX');
  assert.notEqual(out.res.status, 0);
  assert.equal(codeOf(out.res.stderr), codeOf(plain.res.stderr));
});

test('a `.tsx` never reaches the hook', () => {
  // H2. Node's own loader throws `ERR_UNKNOWN_FILE_EXTENSION` from `nextLoad`
  // before any `load` hook runs, so under `node --test` a JSX file is outside
  // NODE's scope and not an exclusion of ours: the hook never sees it, and a
  // count of files it decided about cannot honestly include one it did not.
  const out = run({
    'main.mjs': "await import('./x.tsx');\nconsole.log('loaded');\n",
    'x.tsx': 'export const x = 1;\n',
  }, 'main.mjs');
  assert.notEqual(out.res.status, 0);
  assert.match(out.res.stderr, /ERR_UNKNOWN_FILE_EXTENSION/);
  assert.equal(out.res.stdout.includes('loaded'), false);
  assert.deepEqual(filesOf(out.recs), ['main.mjs']);
  assert.deepEqual(out.tally, { files_transformed: 1, excluded: {} });
});
