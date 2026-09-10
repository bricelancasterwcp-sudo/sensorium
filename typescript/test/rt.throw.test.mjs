// The runtime's throw flow, read back off its own spools: the rejection-handler
// wrapper (`catchCb`), the one-slot in-flight mark (`mark`, set by `raise` and
// cleared by `handled`) and the sink a completing `finally` writes
// (`handledFinally`). Its own file rather than `rt.test.mjs`'s because that file
// is at 682 lines and the repository ceiling is 800 (`tests/test_ceiling.py`):
// these seven tests would carry it over. The child-process helper is the one
// `rt.test.mjs` and `rt.spool.test.mjs` share, and what is asserted is the wire.
import assert from 'node:assert/strict';
import test from 'node:test';

import { of, one, ok, run } from './helpers/rt-child.mjs';

test('catchCb records the rejection its handler was given and changes nothing about it', () => {
  // The wrapper is what the program's promise chain continues with, so the
  // three things it must not touch are the reason, `this` and the return value.
  const out = run(`
    const target = { name: 'the receiver' };
    const seenThis = [];
    const seenReason = [];
    function original(reason) {
      seenThis.push(this === target);
      seenReason.push(reason);
      return 'from the original: ' + reason;
    }
    const wrapped = __srt.catchCb(null, 12, 'catch_callback', original);
    const returned = wrapped.call(target, 'why');
    console.log(JSON.stringify({ returned, seenThis, seenReason, samefn: wrapped === original }));
  `);
  ok(out);
  const got = JSON.parse(out.res.stdout);
  assert.equal(got.returned, 'from the original: why', "the wrapper returns the original's result");
  assert.deepEqual(got.seenThis, [true], 'the original still ran with its own `this`');
  assert.deepEqual(got.seenReason, ['why'], 'the original still got the reason');
  assert.equal(got.samefn, false, 'at tier `call` the handler is wrapped');
  const rec = one(out.recs, 'HANDLED');
  assert.deepEqual([rec.f, rec.t, rec.how, rec.l], [null, null, 'catch_callback', 12]);
  assert.deepEqual([rec.x.kind, rec.x.type, rec.x.msg], ['rejection', 'string', 'why']);
});

test('catchCb carries the how word it was given and the reason keeps its serial', () => {
  // The `how` is the transform's verdict about the handler's shape; the runtime
  // writes it down and does not second-guess it. The serial is what pairs the
  // HANDLED with the RAISE that threw the same object.
  const out = run(`
    const err = new Error('boom');
    __srt.raise(null, err, 3);
    __srt.catchCb(null, 14, 'catch_callback_opaque', (r) => r)(err);
    __srt.catchCb(null, 16, 'sink_empty_catch_callback', () => {})(err);
    __srt.catchCb(null, 18, 'catch_callback_escaped', (r) => { throw r; });
  `);
  ok(out);
  const serial = one(out.recs, 'RAISE').x.serial;
  const [opaque, sink] = of(out.recs, 'HANDLED');
  assert.equal(of(out.recs, 'HANDLED').length, 2, 'a wrapper that was never called records nothing');
  assert.deepEqual([opaque.how, opaque.l, opaque.x.serial, opaque.x.kind],
    ['catch_callback_opaque', 14, serial, 'rejection']);
  assert.deepEqual([sink.how, sink.l, sink.x.serial], ['sink_empty_catch_callback', 16, serial]);
});

test('catchCb hands back a non-function untouched rather than throwing', () => {
  // A shape the transform will not emit — `.catch(handler)` where `handler` is
  // not callable — is a program the recorder must not break. Nothing is
  // recorded, because nothing handled anything.
  const out = run(`
    const notAFunction = { nope: true };
    const back = __srt.catchCb(null, 20, 'catch_callback_opaque', notAFunction);
    console.log(JSON.stringify({ same: back === notAFunction }));
  `);
  ok(out);
  assert.deepEqual(JSON.parse(out.res.stdout), { same: true });
  assert.deepEqual(of(out.recs, 'HANDLED'), []);
});

test('a marked frame whose finally completes writes one sink, then holds nothing', () => {
  // `mark` is the synthetic catch clause's call (the transform's, Task 2): the
  // throw is in flight through THIS frame, and the value is in hand, so the
  // whole `exc` is kept — the sink's record reads `TypeError('in flight')` and
  // not a serial with the identity unread.
  const out = run(`
    const fid = __srt.file('src/a.ts', '/w/src/a.ts', [['a', 1, 'function']], 'sha');
    const f = __srt.call(fid, 0);
    const err = new TypeError('in flight');
    __srt.mark(f, err);
    __srt.handledFinally(f, 21);
    __srt.handledFinally(f, 21);
    __srt.handled(null, err, 30, 'catch');
    __srt.ret(f, undefined);
  `);
  ok(out);
  const [sink, later] = of(out.recs, 'HANDLED');
  assert.equal(of(out.recs, 'HANDLED').length, 2, 'the mark is cleared by the sink that read it');
  assert.deepEqual([sink.f, sink.how, sink.l], [one(out.recs, 'CALL').f, 'sink_finally_return', 21]);
  assert.deepEqual([sink.x.kind, sink.x.type, sink.x.msg], ['throw', 'TypeError', 'in flight']);
  assert.equal(sink.x.serial, later.x.serial, 'the sink names the very value that was thrown');
});

test('a finally that completes with no throw in flight records nothing', () => {
  const out = run(`
    const fid = __srt.file('src/a.ts', '/w/src/a.ts', [['a', 1, 'function']], 'sha');
    const f = __srt.call(fid, 0);
    __srt.handledFinally(f, 9);
    __srt.handledFinally(null, 9);
    __srt.ret(f, 'done');
  `);
  ok(out);
  assert.deepEqual(of(out.recs, 'HANDLED'), []);
  assert.equal(one(out.recs, 'RETURN').v.v, "'done'", 'the frame closed normally all the same');
});

test('raise marks the frame the throw is in flight through', () => {
  const out = run(`
    const fid = __srt.file('src/a.ts', '/w/src/a.ts', [['a', 1, 'function']], 'sha');
    const f = __srt.call(fid, 0);
    __srt.raise(f, new Error('thrown here'), 5);
    __srt.handledFinally(f, 7);
    __srt.ret(f, undefined);
  `);
  ok(out);
  const sink = one(out.recs, 'HANDLED');
  assert.deepEqual([sink.how, sink.l, sink.x.msg], ['sink_finally_return', 7, 'thrown here']);
  assert.equal(sink.x.serial, one(out.recs, 'RAISE').x.serial);
});

test('a finally after a caught throw records nothing: handled clears the mark', () => {
  // The mark says "a throw is travelling through this frame RIGHT NOW". A
  // `catch` in the same frame ends that flight, so the `finally` beneath it
  // discards nothing and must claim nothing. Without the clear in `handled`
  // every caught throw with a completing `finally` would read as a swallow.
  const out = run(`
    const fid = __srt.file('src/a.ts', '/w/src/a.ts', [['a', 1, 'function']], 'sha');
    const f = __srt.call(fid, 0);
    const err = new Error('caught');
    __srt.raise(f, err, 5);
    __srt.handled(f, err, 6, 'catch');
    __srt.handledFinally(f, 8);
    __srt.ret(f, undefined);
  `);
  ok(out);
  const rec = one(out.recs, 'HANDLED');
  assert.deepEqual([rec.how, rec.l], ['catch', 6]);
  assert.deepEqual(of(out.recs, 'HANDLED').map((r) => r.how), ['catch'],
    'no sink_finally_return follows a throw that was caught');
});

test('a throw a callee unwound with sets no mark in the caller', () => {
  // P1's declared blind spot, pinned so it cannot close silently: a `Frame`
  // holds no parent reference, so `thr` has nobody to mark. What sees a
  // library's throw or an awaited rejection is the synthetic clause's `mark`.
  const out = run(`
    const fid = __srt.file('src/a.ts', '/w/src/a.ts', [['a', 1, 'function']], 'sha');
    const caller = __srt.call(fid, 0);
    const callee = __srt.call(fid, 0);
    __srt.thr(callee, new Error('unwound'));
    __srt.handledFinally(caller, 11);
    __srt.ret(caller, undefined);
  `);
  ok(out);
  assert.equal(one(out.recs, 'UNWIND').x.msg, 'unwound');
  assert.deepEqual(of(out.recs, 'HANDLED'), []);
});
