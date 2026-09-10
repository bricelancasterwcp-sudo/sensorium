// The runtime's spool: what reaches the disk, when it gets there, and when
// nothing does. Split out of `rt.test.mjs` verbatim — no test here is reworded
// — so that neither file crosses the 800-line ceiling; both share the
// child-process helper in `helpers/rt-child.mjs`.
import assert from 'node:assert/strict';
import test from 'node:test';

import { ok, of, one, run } from './helpers/rt-child.mjs';

// ---------------------------------------------------------------------------

test('flush on exit', () => {
  // Nothing in the child flushes: the records survive because the runtime
  // flushes on exit, and EXIT is the spool's last line.
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const f = __srt.call(fid, 0);
    __srt.ret(f, 'v');
    process.exitCode = 3;
  `);
  ok(out, 3);
  const kinds = out.recs.map((r) => r.e);
  assert.deepEqual(kinds, ['BOOT', 'FILE', 'CALL', 'RETURN', 'EXIT']);
  const exit = out.recs[out.recs.length - 1];
  assert.equal(exit.code, 3, 'the code the process is leaving with');
  assert.ok(exit.endTs > 1_700_000_000, 'endTs is epoch seconds');
});

test('a task is flushed however it settles', () => {
  // SIGKILL runs no handler at all: what is on the disk got there when each
  // task settled, which is what vitest's teardown timeout leaves behind.
  const out = run(`
    setTimeout(() => {}, 60000);
    const [, thrower] = __srt.task('throws', () => { throw new Error('boom'); }, 1);
    try { thrower(); } catch (err) { /* the harness would report this */ }
    const [, resolver] = __srt.task('resolves', async () => {}, 1);
    await resolver();
    process.kill(process.pid, 'SIGKILL');
  `);
  assert.equal(out.res.signal, 'SIGKILL');
  assert.deepEqual(out.recs.map((r) => r.e), ['BOOT', 'TASK', 'TASK']);
  assert.deepEqual(of(out.recs, 'TASK').map((r) => r.name), ['throws', 'resolves']);
});

test('flush on a terminal signal', () => {
  // The child signals itself in the same turn it records, so the 100 ms timer
  // cannot be what saved the records; the ref'd timeout keeps the loop alive so
  // that only the signal can end the process.
  const out = run(`
    setTimeout(() => {}, 60000);
    __srt.file('t.ts', '/w/t.ts', [], 'sha');
    __srt.seen('a test');
    process.kill(process.pid, 'SIGTERM');
  `);
  assert.equal(out.res.signal, 'SIGTERM', 'the default disposition is restored and re-raised');
  assert.equal(out.res.status, null);
  assert.deepEqual(out.recs.map((r) => r.e), ['BOOT', 'FILE', 'SEEN', 'EXIT'],
    'the buffer reached the disk before the process died');
  // R13: a signalled container still says how it ended.
  const exit = out.recs[out.recs.length - 1];
  assert.equal(exit.code, null, 'no exit code was chosen');
  assert.equal(exit.signal, 'SIGTERM', 'what ended it is named');
  assert.ok(exit.endTs > 1_700_000_000);
});

test('an unhandled rejection is recorded and flushed', () => {
  const out = run(`
    __srt.file('t.ts', '/w/t.ts', [], 'sha');
    Promise.reject(new TypeError('nobody'));
    await new Promise((res) => setTimeout(res, 20));
  `);
  ok(out);
  const rec = one(out.recs, 'UNHANDLED');
  assert.deepEqual([rec.x.kind, rec.x.type, rec.x.msg], ['rejection', 'TypeError', 'nobody']);
  assert.ok(Number.isFinite(rec.x.serial));
});

test('boot is the earliest record on the wire', () => {
  // The first record is a ts-bearing one, so it is the record whose emission
  // boots the spool: its clock reading must not predate BOOT's.
  const out = run(`
    const f = __srt.call(1, 0);
    __srt.ret(f, 'v');
  `);
  ok(out);
  const boot = out.recs[0];
  assert.equal(boot.e, 'BOOT');
  const stamped = out.recs.slice(1).filter((r) => typeof r.ts === 'number');
  assert.ok(stamped.length >= 3, 'there are later stamped records to compare');
  for (const rec of stamped) {
    assert.ok(rec.ts >= boot.ts, `${rec.e} ts ${rec.ts} predates BOOT ts ${boot.ts}`);
  }
});

test('off writes no file at all', () => {
  const out = run(`
    const fn = () => 'called';
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const wrapped = __srt.task('t', fn, 1);
    const suite = __srt.suite('s', fn);
    const frame = __srt.call(fid, 0);
    __srt.nameProvider(() => 'ignored');
    __srt.fileStart('t.ts', 'jsdom');
    __srt.seen('a test');
    __srt.handled(null, new Error('x'), 1, 'catch');
    __srt.flush();
    console.log(JSON.stringify({
      task: [wrapped.length, wrapped[1] === fn],
      suite: [suite.length, suite[1] === fn],
      frame,
      ret: __srt.ret(null, 42),
      y: __srt.y(null, 7, 0),
      r: __srt.r(null, 8),
      raise: __srt.raise(null, 'e', 1),
      emptyCatch: __srt.emptyCatch(null, 1, fn) === fn,
      called: wrapped[1](),
    }));
  `, { tier: 'off' });
  ok(out);
  assert.deepEqual(out.files, [], 'the tier is read once at load and off creates nothing');
  assert.deepEqual(JSON.parse(out.res.stdout), {
    task: [2, true],
    suite: [2, true],
    frame: null,
    ret: 42,
    y: 7,
    r: 8,
    raise: 'e',
    emptyCatch: true,
    called: 'called',
  });
});

test('a spool directory that was never given is not guessed at', () => {
  // The frame is asked for FIRST: nothing has tried to boot yet, so a runtime
  // that read the tier alone would hand back a live frame here.
  const out = run(`
    console.log(JSON.stringify({ frame: __srt.call(1, 0) }));
    __srt.file('t.ts', '/w/t.ts', [], 'sha');
  `, { spool: false });
  ok(out);
  assert.deepEqual(out.files, []);
  assert.equal(JSON.parse(out.res.stdout).frame, null);
});
