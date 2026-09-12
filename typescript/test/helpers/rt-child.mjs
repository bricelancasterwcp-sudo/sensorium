// The child-process helper the two runtime test files share. The tier is read
// once at module load, so the runtime is never imported into a test process:
// every test spawns a child with `SENSORIUM_TIER` and `SENSORIUM_SPOOL` set,
// lets it record, and then parses the JSONL it left behind. Nothing here is a
// mock — what is asserted is the wire, which is the only thing the converter
// reads.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const RT = new URL('../../src/rt.mjs', import.meta.url).href;

/**
 * Run a script against the runtime in a child process and read its spool.
 *
 * The child's environment is this process's with every variable the recorder
 * reads decided HERE, never inherited: a shell that exported `SENSORIUM_FOCUS`
 * — which is exactly what recording a focused run does — would otherwise change
 * what these tests are testing, and the declaration a BOOT writes with it.
 * `SENSORIUM_MANIFEST_DIR` goes the same way; no test here wants a manifest.
 * @param {string} body module source, appended after the runtime import
 * @param {{tier?: string, spool?: boolean, raw?: boolean, focus?: string}}
 *   [opts] `raw` runs the body as the whole module, header and all; `focus`
 *   gives the child a `SENSORIUM_FOCUS`, which it otherwise does not have
 * @returns {{res: import('node:child_process').SpawnSyncReturns<string>,
 *            env: Record<string, string>, files: string[], recs: any[]}}
 */
export function run(body, opts = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sensorium-rt-'));
  // A copy, so nothing here touches this process's own environment.
  const inherited = { ...process.env };
  delete inherited.SENSORIUM_MANIFEST_DIR;
  delete inherited.SENSORIUM_FOCUS;
  if (opts.focus) inherited.SENSORIUM_FOCUS = opts.focus;
  const env = {
    ...inherited,
    SENSORIUM_TIER: opts.tier ?? 'call',
    SENSORIUM_SPOOL: opts.spool === false ? '' : dir,
    SENSORIUM_INVOCATION: 'inv-1',
  };
  const script = opts.raw ? body : `import * as __srt from ${JSON.stringify(RT)};\n${body}\n`;
  try {
    const res = spawnSync(process.execPath, ['--input-type=module', '-e', script], {
      encoding: 'utf8',
      env,
      timeout: 30_000,
    });
    const files = fs.readdirSync(dir);
    return { res, env, files, recs: files.length === 1 ? read(path.join(dir, files[0])) : [] };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

/**
 * @param {string} file
 * @returns {any[]}
 */
export function read(file) {
  const text = fs.readFileSync(file, 'utf8');
  assert.ok(text.endsWith('\n'), 'every record line is newline-terminated');
  return text.slice(0, -1).split('\n').map((line) => JSON.parse(line));
}

/**
 * @param {{res: import('node:child_process').SpawnSyncReturns<string>}} out
 * @param {number|null} [status]
 */
export function ok(out, status = 0) {
  assert.equal(out.res.status, status, `child stderr: ${out.res.stderr}`);
}

/** @param {any[]} recs @param {string} kind @returns {any[]} */
export const of = (recs, kind) => recs.filter((r) => r.e === kind);

/** @param {any[]} recs @param {string} kind @returns {any} */
export const one = (recs, kind) => {
  const found = of(recs, kind);
  assert.equal(found.length, 1, `expected one ${kind}, saw ${found.length}`);
  return found[0];
};
