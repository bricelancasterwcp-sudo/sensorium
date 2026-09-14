// The manifest directory's modes. Everything this recorder writes is 0600 in
// a 0700 directory, AT CREATION — spec §5.5 — and this is the one writer on
// the TypeScript side that is not the runtime's spool.
//
// E16 part A measured it otherwise (H2): six of the ten offending paths were
// `manifests/` and the JSON inside it, at 0775/0664, because `mkdirSync` and
// `writeFileSync` here were called with no mode at all and took the umask.
// A manifest names every function in a file of somebody's project and the
// path it lives at; `_tally.json` names how much of their suite was
// instrumented. Neither is the world's business.
//
// A unit test and not the Python end-to-end one, because this module is
// reachable directly: `record` and `write` are what the Vite plugin and the
// loader hook call, and calling them here needs no harness, no Node version
// floor and no installed package.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import * as tally from '../src/tally.mjs';

/** @param {string} p @returns {number} */
const modeOf = (p) => fs.statSync(p).mode & 0o7777;

/** @param {string} name @returns {string} a fresh directory, removed by the caller */
const scratch = (name) => fs.mkdtempSync(path.join(os.tmpdir(), `sensorium-tally-${name}-`));

/**
 * @param {string} rel
 * @returns {import('../src/transform.mjs').Manifest}
 */
const manifest = (rel) => ({
  file: `/w/${rel}`,
  rel,
  sha256: 'a'.repeat(64),
  instrumented: [],
  focused: [],
  excluded: {},
});

test('the manifest directory and every manifest in it are created private', () => {
  const base = scratch('manifest');
  try {
    const dir = path.join(base, 'manifests');
    tally.record('/w/src/a.ts', { code: 'transformed', manifest: manifest('src/a.ts') }, dir);

    assert.equal(modeOf(dir), 0o700, 'the manifest directory');
    const written = fs.readdirSync(dir);
    assert.deepEqual(written, ['src__a.ts.json'], 'one manifest, named by its flattened path');
    assert.equal(modeOf(path.join(dir, written[0])), 0o600, written[0]);
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

test('the tally both harnesses write is created private too', () => {
  const base = scratch('write');
  try {
    const dir = path.join(base, 'manifests');
    tally.write(dir, tally.INVOCATION_TALLY);

    assert.equal(modeOf(dir), 0o700, 'the manifest directory');
    const file = path.join(dir, tally.INVOCATION_TALLY);
    assert.equal(modeOf(file), 0o600, tally.INVOCATION_TALLY);
    // `write` reports a failure to stderr and returns, so a file that never
    // arrived would otherwise read as a pass on the line above.
    assert.ok(JSON.parse(fs.readFileSync(file, 'utf8')).excluded, 'the counts are in it');
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

test('a directory that already exists keeps the permissions its owner chose', () => {
  // The mode is applied to what this recorder CREATES. A person who pointed
  // the driver at a directory of their own is not overruled, which is the
  // same position `perms.rs` and `paths.traces_dir()` take.
  const base = scratch('existing');
  try {
    const dir = path.join(base, 'manifests');
    fs.mkdirSync(dir, { mode: 0o750 });
    tally.write(dir, tally.containerTally());

    assert.equal(modeOf(dir), 0o750, 'untouched');
    assert.equal(modeOf(path.join(dir, tally.containerTally())), 0o600, 'the file is still ours');
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});
