// One rule of the runtime's naming, pinned where Task 4 found it: a harness that
// gives every activation of ONE registration a name of its own — `test.each`
// expanding a template into a row's values — has already told those activations
// apart, and `#k` must not be added on top. `probes/src/each.probe.test.ts`
// catches this end to end under vitest; this catches it in a second.
//
// `rt.test.mjs` holds the rest of the wire and is left exactly as Task 3 wrote
// it; the small runner below is this file's own so that stays true.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

const RT = new URL('../src/rt.mjs', import.meta.url).href;

/**
 * Record a script against the runtime in a child process and read its spool.
 *
 * `SENSORIUM_FOCUS` is scrubbed rather than inherited: it changes what the
 * runtime declares, and a shell that exported one would be running these
 * assertions against a different recorder.
 * @param {string} body module source, appended after the runtime import
 * @returns {any[]} the records the child wrote
 */
function record(body) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sensorium-naming-'));
  const inherited = { ...process.env };
  delete inherited.SENSORIUM_FOCUS;
  try {
    const res = spawnSync(process.execPath, ['--input-type=module', '-e',
      `import * as __srt from ${JSON.stringify(RT)};\n${body}\n`], {
      encoding: 'utf8',
      env: { ...inherited, SENSORIUM_TIER: 'call', SENSORIUM_SPOOL: dir },
      timeout: 30_000,
    });
    assert.equal(res.status, 0, `child stderr: ${res.stderr}`);
    const files = fs.readdirSync(dir);
    assert.equal(files.length, 1, `expected one spool, saw ${files.length}`);
    return fs.readFileSync(path.join(dir, files[0]), 'utf8')
      .split('\n').filter((line) => line !== '').map((line) => JSON.parse(line));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

test('a harness that renames each activation is not numbered on top of', () => {
  const recs = record(`
    const rows = ['adds 1 + 2 = 3', 'adds 2 + 3 = 5', 'adds 1 + 2 = 3', 'adds 1 + 2 = 3'];
    let i = 0;
    __srt.nameProvider(() => rows[i]);
    const [, activate] = __srt.task('adds $a + $b = $expected', () => {}, 3);
    for (; i < rows.length; i += 1) activate();
  `);
  const tasks = recs.filter((r) => r.e === 'TASK');
  // Three distinct names, and the ordinal only where a name actually repeated.
  assert.deepEqual(tasks.map((t) => t.name), [
    'adds 1 + 2 = 3',
    'adds 2 + 3 = 5',
    'adds 1 + 2 = 3#2',
    'adds 1 + 2 = 3#3',
  ]);
  assert.deepEqual([...new Set(tasks.map((t) => t.basis))], ['vitest']);
  assert.deepEqual([...new Set(tasks.map((t) => t.conflict))], [false]);
});

test('two registrations that share a name are numbered as one sequence', () => {
  // R39: `#k` is per CONTAINER per capped name, which is what HONESTY section 2
  // and the spec's R17 row already claim. Held in the closure it shipped in,
  // the counter was per REGISTRATION and these two both printed `same`.
  const recs = record(`
    const [, first] = __srt.task('same', () => {}, 1);
    const [, second] = __srt.task('same', () => {}, 1);
    first();
    second();
  `);
  assert.deepEqual(recs.filter((r) => r.e === 'TASK').map((t) => t.name),
    ['same', 'same#2']);
});

test('one registration activated twice is numbered the same way', () => {
  // The case `#k` was built for -- a retry, a `repeats` -- and the one the
  // per-registration counter did get right. It must survive the move.
  const recs = record(`
    const [, activate] = __srt.task('twice', () => {}, 1);
    activate();
    activate();
  `);
  assert.deepEqual(recs.filter((r) => r.e === 'TASK').map((t) => t.name),
    ['twice', 'twice#2']);
});
