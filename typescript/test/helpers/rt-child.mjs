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
 * The four variables rule v1 reads go the same way too, and for the same
 * reason: a shell carrying `SENSORIUM_REDACT_KEY` or `SENSORIUM_NO_REDACT`
 * would change what every capture in every child here says, so what the rule
 * was given is `opts.env`'s to state and nothing else's.
 * @param {string} body module source, appended after the runtime import
 * @param {{tier?: string, spool?: boolean, raw?: boolean, focus?: string,
 *          env?: Record<string, string>}}
 *   [opts] `raw` runs the body as the whole module, header and all; `focus`
 *   gives the child a `SENSORIUM_FOCUS`, which it otherwise does not have;
 *   `env` is merged last, so a test says what the child was started with
 * @returns {{res: import('node:child_process').SpawnSyncReturns<string>,
 *            env: Record<string, string>, files: string[], recs: any[],
 *            text: string}} `text` is the spool's own bytes, unparsed
 */
export function run(body, opts = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sensorium-rt-'));
  // A copy, so nothing here touches this process's own environment.
  const inherited = { ...process.env };
  delete inherited.SENSORIUM_MANIFEST_DIR;
  delete inherited.SENSORIUM_FOCUS;
  for (const name of ['SENSORIUM_REDACT_KEY', 'SENSORIUM_NO_REDACT',
    'SENSORIUM_REDACT_NAMES', 'SENSORIUM_REDACT_ALLOW']) {
    delete inherited[name];
  }
  if (opts.focus) inherited.SENSORIUM_FOCUS = opts.focus;
  const env = {
    ...inherited,
    SENSORIUM_TIER: opts.tier ?? 'call',
    SENSORIUM_SPOOL: opts.spool === false ? '' : dir,
    SENSORIUM_INVOCATION: 'inv-1',
    ...(opts.env ?? {}),
  };
  const script = opts.raw ? body : `import * as __srt from ${JSON.stringify(RT)};\n${body}\n`;
  try {
    const res = spawnSync(process.execPath, ['--input-type=module', '-e', script], {
      encoding: 'utf8',
      env,
      timeout: 30_000,
    });
    const files = fs.readdirSync(dir);
    const one_ = files.length === 1 ? path.join(dir, files[0]) : null;
    return {
      res,
      env,
      files,
      recs: one_ === null ? [] : read(one_),
      // The bytes, for a test that asks what the disk holds rather than what
      // the records say: a secret the rule missed is a secret ON DISK.
      text: one_ === null ? '' : fs.readFileSync(one_, 'utf8'),
    };
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
