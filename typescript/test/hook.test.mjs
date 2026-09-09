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
 */
function run(files, entry, env = {}) {
  const root = fs.mkdtempSync(path.join(PROBES, 'hooktmp-'));
  const spool = path.join(root, 'spool');
  try {
    for (const [rel, source] of Object.entries(files)) {
      fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
      fs.writeFileSync(path.join(root, rel), source);
    }
    const res = spawnSync(process.execPath, ['--import', REGISTER, path.join(root, entry)], {
      encoding: 'utf8',
      timeout: 30_000,
      env: {
        ...process.env,
        SENSORIUM_TIER: 'call',
        SENSORIUM_SPOOL: spool,
        SENSORIUM_TS_ROOT: root,
        SENSORIUM_TS_PKG: PKG,
        ...env,
      },
    });
    const spooled = fs.existsSync(spool) ? fs.readdirSync(spool) : [];
    const recs = spooled.flatMap((name) => fs.readFileSync(path.join(spool, name), 'utf8')
      .split('\n').filter((line) => line !== '').map((line) => JSON.parse(line)));
    return { res, recs };
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
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
