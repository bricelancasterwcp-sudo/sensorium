// The two files this recorder must NOT make loadable, and the proof that it
// does not. Each is run twice -- plain `node <file>`, and `node --import
// ../src/register.mjs <file>` -- and the error code Node printed has to be the
// same string both times. A mismatch is a refusal: the recorder changed what
// loads, which is the one thing it promises not to do (H1, H2).
//
// They live outside `nodetest/`'s test-file names on purpose. `node --test`
// would try to RUN them, and what is measured here is what happens when they
// are LOADED at all.
//
//   node nodetest/controls.mjs
//
// One JSON line per control on stdout, `{control, plain, hooked, same}`; exit
// 0 when both sides matched on both controls, 1 otherwise. A side that exited
// 0 is a refusal too: a control that stopped failing has stopped being one.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROBES = path.dirname(HERE);
const PKG = path.dirname(PROBES);
const REGISTER = path.join(PKG, 'src', 'register.mjs');

/** The controls, in the order their lines are printed. */
const CONTROLS = ['controls/enum.ts', 'controls/jsx.tsx'];

/** The first error code in a stream, or null: what the two sides compare on. */
const codeOf = (/** @type {string} */ text) => (text.match(/ERR_[A-Z_]+/) ?? [null])[0];

/**
 * One control, one side.
 * @param {string} rel the control, relative to this directory
 * @param {boolean} hooked whether `register.mjs` is installed in front of it
 * @param {string} spool a scratch spool directory for the hooked side
 * @returns {{code: string|null, status: number|null}}
 */
function run(rel, hooked, spool) {
  const file = path.join(HERE, rel);
  // `register.mjs` refuses without a root and a package, so the hooked side
  // sets all five: a refusal from the registrar is not a verdict on the file.
  // The spool and the manifest directory are this script's OWN scratch, never
  // the run's -- measured: with `SENSORIUM_MANIFEST_DIR` inherited, the enum
  // control's child (the transform succeeds; NODE rejects the file) wrote a
  // `_tally-<pid>.json` into the probe run's manifest directory, where it
  // reads as a second spool-less child and breaks `ext:cjs:tally`.
  const env = hooked
    ? {
      ...process.env,
      SENSORIUM_TIER: 'call',
      SENSORIUM_SPOOL: spool,
      SENSORIUM_MANIFEST_DIR: path.join(spool, 'manifests'),
      SENSORIUM_TS_ROOT: PROBES,
      SENSORIUM_TS_PKG: PKG,
    }
    : process.env;
  const res = spawnSync(process.execPath, hooked ? ['--import', REGISTER, file] : [file], {
    cwd: PROBES, encoding: 'utf8', timeout: 30_000, env,
  });
  return { code: codeOf(String(res.stderr)), status: res.status };
}

/**
 * Whether one side failed the way a control must, saying so when it did not.
 * @param {string} control
 * @param {string} side
 * @param {number|null} status
 * @returns {boolean}
 */
function failed(control, side, status) {
  if (status !== 0) return true;
  process.stderr.write(`controls.mjs: ${control} exited 0 on the ${side} side: `
    + 'a control that stopped failing has stopped being a control\n');
  return false;
}

function main() {
  const spool = fs.mkdtempSync(path.join(os.tmpdir(), 'sensorium-controls-'));
  let ok = true;
  try {
    for (const control of CONTROLS) {
      const plain = run(control, false, spool);
      const hooked = run(control, true, spool);
      const same = plain.code === hooked.code && plain.code !== null;
      const p = failed(control, 'plain', plain.status);
      const h = failed(control, 'hooked', hooked.status);
      ok = ok && same && p && h;
      process.stdout.write(`${JSON.stringify({
        control, plain: plain.code, hooked: hooked.code, same,
      })}\n`);
    }
  } finally {
    fs.rmSync(spool, { recursive: true, force: true });
  }
  process.exitCode = ok ? 0 : 1;
}

main();
