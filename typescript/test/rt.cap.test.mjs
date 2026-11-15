// Per-run caps, read off the spool. The driver resolves sizes; the runtime
// reads the integers. 0 is unlimited.
import assert from 'node:assert/strict';
import test from 'node:test';

import { of, ok, one, run } from './helpers/rt-child.mjs';

const CAP3 = {
  SENSORIUM_MAX_CALLS: '3',
  SENSORIUM_MAX_EVENTS: '0',
  SENSORIUM_MAX_BYTES: '0',
};

test('20 calls with a cap of 3 keep 3 and elide 17', () => {
  const out = run(`
    const fid = __srt.file('src/a.ts', '/w/src/a.ts', [['leaf', 1, 'function']], 'sha');
    for (let i = 0; i < 20; i++) {
      const f = __srt.call(fid, 0, ['i', i]);
      __srt.ret(f, 'zz-kept-' + i);
    }
  `, { env: CAP3 });
  ok(out);
  const calls = of(out.recs, 'CALL');
  assert.equal(calls.length, 3);
  assert.equal(of(out.recs, 'RETURN').length, 3);
  assert.deepEqual(calls.map((rec) => rec.a.i), [
    { k: 'dbg', v: '0', trunc: false },
    { k: 'dbg', v: '1', trunc: false },
    { k: 'dbg', v: '2', trunc: false },
  ]);
  const elision = one(out.recs, 'ELISION');
  assert.equal(elision.callsElided, 17);
  assert.deepEqual(elision.hit, ['max_calls']);
  assert.equal(elision.maxCalls, 3);
  assert.equal(elision.elisions.length, 1);
  assert.equal(elision.elisions[0].elided, 17);
  assert.equal(elision.elisions[0].kept, 3);
  assert.equal(elision.elisions[0].c, 0);
  assert.equal(elision.elisions[0].file, calls[0].file);
  assert.equal(out.recs.at(-1).e, 'EXIT');
  assert.equal(out.recs.at(-2).e, 'ELISION');
  assert.ok(out.text.includes('zz-kept-0'));
  assert.ok(out.text.includes('zz-kept-2'));
  assert.ok(!out.text.includes('zz-kept-3'), 'an elided return is not stored');
});

test('an elided call does not read arguments or lines', () => {
  // An odd pairs list throws. It is passed only once the cap has been hit,
  // so a capture of an elided call would fail the child.
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [['leaf', 1, 'function']], 'sha');
    for (let i = 0; i < 5; i++) {
      const pairs = i < 2 ? ['n', i] : ['n', i, 'odd'];
      const f = __srt.call(fid, 0, pairs);
      __srt.line(f, 2, pairs);
      __srt.ret(f, i);
    }
  `, { env: { SENSORIUM_MAX_CALLS: '2', SENSORIUM_MAX_EVENTS: '0', SENSORIUM_MAX_BYTES: '0' } });
  ok(out);
  assert.equal(of(out.recs, 'CALL').length, 2);
  assert.equal(of(out.recs, 'LINE').length, 2);
  assert.equal(one(out.recs, 'ELISION').callsElided, 3);
});

test('a throw on the last call is still recorded', () => {
  const out = run(`
    const fid = __srt.file('src/a.ts', '/w/src/a.ts', [['leaf', 4, 'function']], 'sha');
    for (let i = 0; i < 20; i++) {
      const f = __srt.call(fid, 0, ['i', i]);
      if (i === 19) {
        __srt.raise(f, new Error('boom'), 5);
        __srt.thr(f, new Error('boom'));
      } else {
        __srt.ret(f, i);
      }
    }
  `, { env: CAP3 });
  ok(out);
  const calls = of(out.recs, 'CALL');
  assert.equal(calls.length, 4, 'three stored calls plus the throwing frame');
  const raised = one(out.recs, 'RAISE');
  assert.equal(raised.f, calls[3].f);
  assert.equal(raised.x.type, 'Error');
  assert.equal(raised.x.msg, 'boom');
  assert.equal(calls[3].a, undefined, 'the skeleton call omits arguments');
  const elision = one(out.recs, 'ELISION');
  assert.equal(elision.callsElided, 16);
  assert.equal(elision.failuresKept, 1);
  assert.equal(elision.elisions[0].kept, 4);
  assert.equal(elision.elisions[0].elided, 16);
  const unwind = one(out.recs, 'UNWIND');
  assert.equal(unwind.f, calls[3].f);
  assert.ok(out.recs.indexOf(calls[3]) < out.recs.indexOf(raised));
});

test('an elided parent is popped, and its child is not stored under it', () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [['leaf', 1, 'function'], ['other', 8, 'function']], 'sha');
    const leaf = __srt.call(fid, 0, []);
    __srt.ret(leaf, 1);
    const again = __srt.call(fid, 0, []);
    const inner = __srt.call(fid, 1, ['n', 1]);
    __srt.ret(inner, 1);
    __srt.ret(again, 2);
    const other = __srt.call(fid, 1, ['n', 2]);
    __srt.ret(other, 3);
  `, { env: { SENSORIUM_MAX_CALLS: '1', SENSORIUM_MAX_EVENTS: '0', SENSORIUM_MAX_BYTES: '0' } });
  ok(out);
  const calls = of(out.recs, 'CALL');
  // leaf kept, again elided, inner elided with it, other kept after the pop.
  assert.equal(calls.length, 2);
  assert.equal(calls[1].c, 1);
  assert.equal(calls[1].p, null);
  const elision = one(out.recs, 'ELISION');
  const rows = /** @type {{c: number, elided: number}[]} */ (elision.elisions);
  const byC = Object.fromEntries(rows.map((row) => [row.c, row.elided]));
  assert.equal(byC[0], 1);
  assert.equal(byC[1], 1);
});

test('a throw under an elided parent materializes the chain outermost first', () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [['outer', 1, 'function'], ['inner', 5, 'function']], 'sha');
    for (let i = 0; i < 3; i++) {
      const outer = __srt.call(fid, 0, ['i', i]);
      const inner = __srt.call(fid, 1, ['i', i]);
      if (i === 2) {
        __srt.raise(inner, new Error('boom'), 6);
        __srt.thr(inner, new Error('boom'));
        __srt.thr(outer, new Error('boom'));
      } else {
        __srt.ret(inner, i);
        __srt.ret(outer, i);
      }
    }
  `, { env: { SENSORIUM_MAX_CALLS: '1', SENSORIUM_MAX_EVENTS: '0', SENSORIUM_MAX_BYTES: '0' } });
  ok(out);
  const calls = of(out.recs, 'CALL');
  assert.equal(calls.length, 4);
  const skeletons = calls.slice(2);
  assert.equal(skeletons[0].c, 0, 'the outer frame is written first');
  assert.equal(skeletons[1].c, 1);
  assert.equal(skeletons[1].p, skeletons[0].f);
  assert.equal(skeletons[0].a, undefined);
  assert.equal(skeletons[1].a, undefined);
  const raised = one(out.recs, 'RAISE');
  assert.equal(raised.f, skeletons[1].f);
  assert.ok(out.recs.indexOf(skeletons[0]) < out.recs.indexOf(skeletons[1]));
  assert.ok(out.recs.indexOf(skeletons[1]) < out.recs.indexOf(raised));
  const elision = one(out.recs, 'ELISION');
  assert.equal(elision.failuresKept, 2);
  assert.equal(elision.callsElided, 2);
});
