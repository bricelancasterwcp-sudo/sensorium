// The Vite plugin, on its branches. The probe project exercises the happy path
// end to end; what is pinned here is everything a green probe run cannot show:
// a file that is ours and uncountable (R7a), a file that is ours and unparsable
// (R10), a refusal that must reach the consumer (R10a), the two resolutions the
// plugin is forbidden to make from its own location, and the tally the converter
// reads.
//
// Every test runs in a CHILD process. The tally is per process by design and is
// written from an `exit` handler, so a test that shared this process with
// another would be reading another test's count.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const VITE = new URL('../src/vite.mjs', import.meta.url).href;
const PKG = fileURLToPath(new URL('../', import.meta.url));
// The probe project is a real root with its own `typescript`; no file under it
// is read, because `transform(code, id)` is given its source.
const ROOT = fileURLToPath(new URL('../probes/', import.meta.url));

/**
 * Run a plugin script in a child and read what it left behind.
 *
 * Every variable the recorder reads is decided HERE and never inherited: a
 * shell that exported `SENSORIUM_FOCUS` -- which is exactly what recording a
 * focused run does -- would change what this plugin splices, and these tests
 * would be reading that shell instead of their own fixture.
 * @param {string} body module source, run after `sensorium` is in scope
 * @param {{manifests?: boolean, focus?: string}} [opts]
 * @returns {{res: import('node:child_process').SpawnSyncReturns<string>, dir: string,
 *   out: any, tally: any, manifests: string[]}}
 */
function run(body, opts = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sensorium-vite-'));
  const env = { ...process.env };
  delete env.SENSORIUM_FOCUS;
  if (opts.focus) env.SENSORIUM_FOCUS = opts.focus;
  if (opts.manifests === false) delete env.SENSORIUM_MANIFEST_DIR;
  else env.SENSORIUM_MANIFEST_DIR = dir;
  const script = `import { sensorium } from ${JSON.stringify(VITE)};\n` +
    `import { createRequire } from 'node:module';\n` +
    `const ROOT = ${JSON.stringify(ROOT)};\nconst PKG = ${JSON.stringify(PKG)};\n${body}\n`;
  const res = spawnSync(process.execPath, ['--input-type=module', '-e', script], {
    encoding: 'utf8', env, timeout: 30_000,
  });
  const names = fs.existsSync(dir) ? fs.readdirSync(dir).sort() : [];
  const tallyPath = path.join(dir, '_tally.json');
  const tally = fs.existsSync(tallyPath) ? JSON.parse(fs.readFileSync(tallyPath, 'utf8')) : null;
  const out = res.stdout.trim() === '' ? null : JSON.parse(res.stdout);
  try {
    return { res, dir, out, tally, manifests: names.filter((n) => n !== '_tally.json') };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

/** @param {any} out @param {number} [status] */
function ok(out, status = 0) {
  assert.equal(out.res.status, status, `child stderr: ${out.res.stderr}`);
}

const PLUGIN = "const p = sensorium({ root: ROOT, pkgDir: PKG, rtPath: 'RT' });";

test('a good file is edited, counted once, and its manifest is named by its path', () => {
  const out = run(`${PLUGIN}
    const id = ROOT + 'src/deep/mod.ts';
    const first = p.transform('export function f(){ return 1 }', id);
    // The same file asked for twice — Vite keeps one module graph per transform
    // mode — is ONE file, or the converter would publish the inflation.
    const again = p.transform('export function f(){ return 1 }', id + '?v=2');
    console.log(JSON.stringify({
      edited: first.code.includes('__srt.call('),
      imported: first.code.includes('from "RT"'),
      lines: [first.code.split('\\n').length, 1],
      hires: first.map.mappings.length > 0 && first.map.sources.length === 1,
      againEdited: again.code === first.code,
    }));
  `);
  ok(out);
  assert.equal(out.out.edited, true);
  assert.equal(out.out.imported, true);
  assert.equal(out.out.hires, true);
  assert.equal(out.out.againEdited, true);
  assert.deepEqual(out.manifests, ['src__deep__mod.ts.json']);
  assert.deepEqual(out.tally, { files_transformed: 1, functions_focused: 0, excluded: {} });
});

test('R7a: CommonJS is ours, cannot be transformed, and is counted by name', () => {
  const out = run(`${PLUGIN}
    console.log(JSON.stringify({
      cjs: p.transform('module.exports = 1', ROOT + 'src/legacy.cjs'),
      cts: p.transform('export = 1', ROOT + 'src/legacy.cts'),
    }));
  `);
  ok(out);
  assert.deepEqual(out.out, { cjs: null, cts: null });
  assert.deepEqual(out.manifests, []);
  assert.deepEqual(out.tally, { files_transformed: 0, functions_focused: 0, excluded: { commonjs: 2 } });
});

test('R10: a file that does not parse is ours, untouched, counted — and returns null', () => {
  const out = run(`${PLUGIN}
    console.log(JSON.stringify({ back: p.transform('function (', ROOT + 'src/broken.ts') }));
  `);
  ok(out);
  assert.equal(out.out.back, null);
  assert.deepEqual(out.manifests, ['src__broken.ts.json']);
  assert.deepEqual(out.tally, { files_transformed: 0, functions_focused: 0, excluded: { 'parse-error': 1 } });
});

test('R10a: a refusal to splice blind fails the run by name', () => {
  const out = run(`
    // A TypeScript build whose parser reports nothing. The plugin resolves the
    // consumer's copy through the SAME require cache, so replacing the cached
    // exports here is what it will pick up — the closest this can get to the
    // build the rule was written for without shipping one.
    const require = createRequire(ROOT + 'package.json');
    const id = require.resolve('typescript');
    const real = require(id);
    require.cache[id].exports = new Proxy(real, {
      get: (target, key) => (key === 'createSourceFile'
        ? (...args) => {
          const sf = target.createSourceFile(...args);
          sf.parseDiagnostics = undefined;
          return sf;
        }
        : target[key]),
    });
    ${PLUGIN}
    p.transform('export const x = 1', ROOT + 'src/blind.ts');
    console.log('the refusal did not propagate');
  `, { manifests: false });
  assert.notEqual(out.res.status, 0);
  assert.match(out.res.stderr, /exposes no parseDiagnostics; refusing to transform blind/);
  assert.equal(out.res.stdout.includes('did not propagate'), false);
});

test('a path that is not ours is left alone, manifest and tally included', () => {
  const out = run(`${PLUGIN}
    console.log(JSON.stringify({
      virtual: p.transform('x', '\\0virtual:thing'),
      outside: p.transform('x', '/elsewhere/mod.ts'),
      deps: p.transform('x', ROOT + 'node_modules/dep/mod.ts'),
      declaration: p.transform('x', ROOT + 'src/mod.d.ts'),
      json: p.transform('{}', ROOT + 'src/data.json'),
    }));
  `);
  ok(out);
  assert.deepEqual(out.out,
    { virtual: null, outside: null, deps: null, declaration: null, json: null });
  assert.deepEqual(out.manifests, []);
  assert.deepEqual(out.tally, { files_transformed: 0, functions_focused: 0, excluded: {} });
});

test('with no manifest directory the plugin writes nothing and still transforms', () => {
  const out = run(`${PLUGIN}
    const back = p.transform('export function f(){ return 1 }', ROOT + 'src/mod.ts');
    console.log(JSON.stringify({ edited: back.code.includes('__srt.call(') }));
  `, { manifests: false });
  ok(out);
  assert.equal(out.out.edited, true);
  assert.equal(out.tally, null);
  assert.deepEqual(out.manifests, []);
});

test('the two resolutions are the root\'s TypeScript and the package\'s magic-string', () => {
  // Neither may come from this file's own location: a `pkgDir` with no
  // `magic-string` and a `root` with no `typescript` must each refuse, here,
  // rather than fail inside a transform half a suite later.
  const noPkg = run("sensorium({ root: ROOT, pkgDir: '/nowhere/', rtPath: 'RT' });");
  assert.notEqual(noPkg.res.status, 0);
  assert.match(noPkg.res.stderr, /magic-string/);
  const noRoot = run("sensorium({ root: '/nowhere/', pkgDir: PKG, rtPath: 'RT' });");
  assert.notEqual(noRoot.res.status, 0);
  assert.match(noRoot.res.stderr, /typescript/);
});

test('the plugin reads SENSORIUM_FOCUS where it is BUILT, and counts what it selected', () => {
  // A config's `import` of the plugin is hoisted above the config's own body,
  // so a project that sets the variable in its config -- the probe project,
  // which has no driver -- sets it AFTER this module loads and before the
  // plugin is built. Reading it at build time is what makes that work.
  const out = run(`${PLUGIN}
    const back = p.transform(
      'export function watched(a){ const b = a + 1; return b }\\n'
      + 'export function ignored(a){ const b = a + 1; return b }\\n',
      ROOT + 'src/mod.ts');
    console.log(JSON.stringify({
      focused: back.code.includes('__srt.call(__sfile,0,["a",a]);'),
      rows: (back.code.match(/__srt\\.line\\(/g) || []).length,
      sibling: back.code.includes('export function ignored(a){const __sf=__srt.call(__sfile,1);'),
    }));
  `, { focus: 'mod.ts:watched' });
  ok(out);
  assert.equal(out.out.focused, true);
  assert.equal(out.out.rows, 1, 'one statement of the one focused function');
  assert.equal(out.out.sibling, true, 'and the sibling is spliced as it always was');
  assert.deepEqual(out.tally, { files_transformed: 1, functions_focused: 1, excluded: {} });
});

test('with no SENSORIUM_FOCUS the plugin focuses nothing and counts none', () => {
  const out = run(`${PLUGIN}
    const back = p.transform('export function watched(a){ return a }', ROOT + 'src/mod.ts');
    console.log(JSON.stringify({ rows: back.code.includes('__srt.line(') }));
  `);
  ok(out);
  assert.equal(out.out.rows, false);
  assert.deepEqual(out.tally, { files_transformed: 1, functions_focused: 0, excluded: {} });
});
