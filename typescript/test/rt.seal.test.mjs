// The seal, one test per row of design §4.3's table. `pend` stores the value
// a `return` chose and leaves the frame OPEN; the wrapper's own `finally`
// calls `seal`, which closes it and emits RETURN — so the program's `finally`
// runs on a live frame: its statements mint their rows, and a call it makes
// opens under the frame that made it (blind spot 38, closed 2026-09-12).
//
// Every body here is written the way `transform.mjs` splices it — generated
// from the real transform and pasted, header line apart — so a splice form
// that moves and a runtime that moves cannot pass each other in the night.
// Nothing is mocked: each test spawns a child, records, and reads the spool.
import assert from 'node:assert/strict';
import test from 'node:test';

import { of, ok, one, run } from './helpers/rt-child.mjs';

/** The header every body opens with: one file, one focused frame. */
const FILE = "const __sfile = __srt.file('t.ts', '/w/t.ts', [], 'sha');";

/**
 * @param {any[]} recs
 * @param {any} frame a CALL record
 * @returns {any[]} that frame's LINE rows, in order
 */
const linesOf = (recs, frame) => of(recs, 'LINE').filter((r) => r.f === frame.f);

/** @param {any[]} recs @param {any} rec @returns {number} */
const at = (recs, rec) => recs.indexOf(rec);

// --- row 1: `try { return 1 } finally { cleanup = 1 }` ----------------------

test('a statement of the finally mints its row, and the RETURN comes after it', () => {
  const out = run(`
    ${FILE}
    let cleanup = 0;
    function f() {const __sf=__srt.call(__sfile,0);try{
      try {
        return __srt.pend(__sf,(1));
      } finally {
        cleanup = 1;__srt.line(__sf,5,["cleanup",cleanup]);
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    console.log(JSON.stringify({ returned: f() }));
  `, { focus: 'f' });
  ok(out);

  const frame = one(out.recs, 'CALL');
  const returned = one(out.recs, 'RETURN');
  // The program is unchanged by the seal: `pend` hands back what it was given.
  assert.deepEqual(JSON.parse(out.res.stdout), { returned: 1 });
  // The row the finally wrote, and the value the return chose.
  assert.deepEqual(linesOf(out.recs, frame).map((r) => [r.l, r.d.cleanup.v]), [[5, '1']]);
  assert.deepEqual(returned.v, { k: 'dbg', v: '1', trunc: false });
  assert.equal(returned.f, frame.f);
  // The order is the whole point: the exit is recorded AFTER the finally ran.
  assert.ok(at(out.recs, returned) > at(out.recs, linesOf(out.recs, frame)[0]),
    'the RETURN follows the row of the statement the finally ran');
});

// --- row 2: `try { return 1 } finally { return 2 }` -------------------------

test('a finally that returns overwrites the pended value, and there is one exit', () => {
  const out = run(`
    ${FILE}
    function f() {const __sf=__srt.call(__sfile,0);try{
      try {
        return __srt.pend(__sf,(1));
      } catch(__sfe){__srt.mark(__sf,__sfe);throw __sfe}finally {__srt.handledFinally(__sf,4);
        return __srt.pend(__sf,(2));
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    console.log(JSON.stringify({ returned: f() }));
  `, { focus: 'f' });
  ok(out);

  // JavaScript returns 2, and the record says 2: the second `pend` overwrote
  // the first, and `seal` emits what the frame was holding when it closed.
  assert.deepEqual(JSON.parse(out.res.stdout), { returned: 2 });
  assert.deepEqual(one(out.recs, 'RETURN').v, { k: 'dbg', v: '2', trunc: false });
});

// --- row 3: `try { return 1 } finally { throw e }` --------------------------

test('a finally that throws unwinds the frame, and no RETURN is invented', () => {
  const out = run(`
    ${FILE}
    let cleanup = 0;
    function f() {const __sf=__srt.call(__sfile,0);try{
      try {
        return __srt.pend(__sf,(1));
      } finally {
        cleanup = 1;__srt.line(__sf,5,["cleanup",cleanup]);
        throw __srt.raise(__sf,(new Error('boom')),6);
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    try { f(); } catch {}
  `, { focus: 'f' });
  ok(out);

  const frame = one(out.recs, 'CALL');
  // The finally's rows are there — the frame was open while it ran — and the
  // exit is the UNWIND `thr` recorded in the wrapper's catch. `seal` then met
  // a frame `thr` had closed and left it exactly as `thr` left it.
  assert.deepEqual(linesOf(out.recs, frame).map((r) => [r.l, r.d.cleanup.v]), [[5, '1']]);
  assert.deepEqual(of(out.recs, 'RETURN'), [], 'a value that never left is not a return');
  assert.equal(one(out.recs, 'UNWIND').f, frame.f);
  assert.deepEqual(one(out.recs, 'UNWIND').x.msg, 'boom');
});

// --- row 4: `try { throw e } catch { return 1 } finally { … }` --------------

test('a return from the catch pends, and the finally still mints its rows', () => {
  const out = run(`
    ${FILE}
    let cleanup = 0;
    function f() {const __sf=__srt.call(__sfile,0);try{
      try {
        throw __srt.raise(__sf,(new Error('boom')),3);
      } catch (e) {__srt.handled(__sf,e,4,"catch");__srt.line(__sf,4,["e",e]);
        return __srt.pend(__sf,(1));
      } finally {
        cleanup = 1;__srt.line(__sf,7,["cleanup",cleanup]);
      };__srt.line(__sf,2,[],["e"]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    console.log(JSON.stringify({ returned: f() }));
  `, { focus: 'f' });
  ok(out);

  const frame = one(out.recs, 'CALL');
  const returned = one(out.recs, 'RETURN');
  assert.deepEqual(JSON.parse(out.res.stdout), { returned: 1 });
  assert.equal(one(out.recs, 'HANDLED').how, 'catch');
  assert.deepEqual(linesOf(out.recs, frame).map((r) => r.l), [4, 7]);
  assert.deepEqual(returned.v, { k: 'dbg', v: '1', trunc: false });
  assert.ok(at(out.recs, returned) > at(out.recs, one(out.recs, 'HANDLED')));
  assert.ok(at(out.recs, returned) > at(out.recs, linesOf(out.recs, frame)[1]));
});

// --- row 5: `try { return await p } finally { … }` (async) ------------------

test('a coroutine parks and resumes with the frame open, and seals after the finally', () => {
  const out = run(`
    ${FILE}
    let cleanup = 0;
    async function f(p) {const __sf=__srt.call(__sfile,0);try{
      try {
        return __srt.pend(__sf,(__srt.r(__sf,await __srt.y(__sf,(p),0))));
      } finally {
        cleanup = 1;__srt.line(__sf,5,["cleanup",cleanup]);
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    f(Promise.resolve(7)).then((v) => console.log(JSON.stringify({ returned: v })));
  `, { focus: 'f' });
  ok(out);

  const frame = one(out.recs, 'CALL');
  const returned = one(out.recs, 'RETURN');
  assert.deepEqual(JSON.parse(out.res.stdout), { returned: 7 });
  // `y` and `r` both ask whether the frame is open, and it still is: the park
  // and the resume are recorded, and the finally's row after them.
  assert.equal(one(out.recs, 'YIELD').k, 'await');
  assert.equal(one(out.recs, 'RESUME').f, frame.f);
  assert.deepEqual(linesOf(out.recs, frame).map((r) => [r.l, r.d.cleanup.v]), [[5, '1']]);
  assert.deepEqual(returned.v, { k: 'dbg', v: '7', trunc: false });
  assert.ok(at(out.recs, returned) > at(out.recs, linesOf(out.recs, frame)[0]));
});

// --- row 6: a generator with the shape (§4.4) ------------------------------

test('a deferred generator has exactly one exit: seal’s, and gclose is the no-op', () => {
  const out = run(`
    ${FILE}
    let cleanup = 0;
    function* f() {const __sf=__srt.call(__sfile,0);try{
      try {
        __srt.r(__sf,yield __srt.y(__sf,(1),1));__srt.line(__sf,3,[]);
        return __srt.pend(__sf,(2));
      } finally {
        cleanup = 1;__srt.line(__sf,6,["cleanup",cleanup]);
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf);__srt.gclose(__sf)}}
    console.log(JSON.stringify({ yielded: [...f()] }));
  `, { focus: 'f' });
  ok(out);

  const frame = one(out.recs, 'CALL');
  assert.deepEqual(JSON.parse(out.res.stdout), { yielded: [1] });
  // ONE RETURN, and it is the seal's: the value the body returned, not the
  // `unread` `gclose` writes for a generator its consumer closed.
  const returned = one(out.recs, 'RETURN');
  assert.deepEqual(returned.v, { k: 'dbg', v: '2', trunc: false });
  assert.deepEqual(linesOf(out.recs, frame).map((r) => [r.l, r.d]), [[3, {}], [6, { cleanup: { k: 'dbg', v: '1', trunc: false } }]]);
  assert.ok(at(out.recs, returned) > at(out.recs, linesOf(out.recs, frame)[1]));
});

test('a deferred generator its consumer abandons reports its value unread', () => {
  // The one shape where no `pend` ran at all: a generator resumed with a
  // RETURN completion runs its `finally` and reaches the wrapper's, having
  // pended nothing. `seal` writes `gclose`'s word for it (amendment A12,
  // §4.4) — `.return(v)`'s value belongs to the CONSUMER and never reaches
  // the body, so the body produced none, and `undefined` there would be a
  // value this recorder invented. The row is the same one `gclose` would
  // have written; only the frame's lifetime moved.
  const out = run(`
    ${FILE}
    let cleanup = 0;
    function* f() {const __sf=__srt.call(__sfile,0);try{
      try {
        __srt.r(__sf,yield __srt.y(__sf,(1),1));__srt.line(__sf,3,[]);
        return __srt.pend(__sf,(2));
      } finally {
        cleanup = 1;__srt.line(__sf,6,["cleanup",cleanup]);
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf);__srt.gclose(__sf)}}
    for (const v of f()) { break; }
  `, { focus: 'f' });
  ok(out);

  const frame = one(out.recs, 'CALL');
  const returned = one(out.recs, 'RETURN');
  assert.deepEqual(returned.v, { k: 'unread' },
    'the consumer closed it; the body produced no value to report');
  // The finally still ran on a live frame, which is what the seal is for.
  assert.deepEqual(linesOf(out.recs, frame).map((r) => r.l), [6]);
});

test('a deferred function that falls off its end reports RETURN undefined', () => {
  // The other side of `seal`'s `??`, and what keeps A12 narrow: a body with
  // no `return` at all still PENDS — the wrapper's fallthrough close is
  // `;__srt.pend(__sf,undefined)`, which stores the capture of `undefined`,
  // an object. So `f.pending` is set, `unread` is not reached, and the row
  // says what JavaScript returned. Only the abandoned generator, whose body
  // never reaches that close, has nothing pended.
  const out = run(`
    ${FILE}
    let cleanup = 0;
    function f() {const __sf=__srt.call(__sfile,0);try{
      try {
        cleanup = 1;__srt.line(__sf,3,["cleanup",cleanup]);
      } finally {
        cleanup = 2;__srt.line(__sf,5,["cleanup",cleanup]);
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    console.log(JSON.stringify({ undefined_: f() === undefined }));
  `, { focus: 'f' });
  ok(out);

  assert.deepEqual(JSON.parse(out.res.stdout), { undefined_: true });
  assert.deepEqual(one(out.recs, 'RETURN').v, { k: 'dbg', v: 'undefined', trunc: false });
});

// --- row 7: the call the finally makes -------------------------------------

test('a call the finally makes is the frame’s child, not its sibling', () => {
  const out = run(`
    ${FILE}
    function note(n) {const __sf=__srt.call(__sfile,1);try{
      return __srt.ret(__sf,(n));
    ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
    function f() {const __sf=__srt.call(__sfile,0);try{
      try {
        return __srt.pend(__sf,(1));
      } finally {
        note(1);__srt.line(__sf,5,[]);
      };__srt.line(__sf,2,[]);
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    f();
    note(2);
  `, { focus: 'f' });
  ok(out);

  const [outer, inner, after] = of(out.recs, 'CALL');
  // The frame is open through the finally, so `note` opens beneath it. Under
  // 0.3.0 `ret` had already dropped `f` from the stack and `note` opened under
  // whatever was on top — attributed outside its own caller.
  assert.equal(inner.p, outer.f, 'the call the finally made is the frame’s child');
  // And `seal` takes the frame OFF its stack as it closes it: the call that
  // comes after `f` has returned is nobody's child. A seal that closed the
  // frame without dropping it would make every later call a descendant of a
  // function that had already returned.
  assert.equal(after.p, null, 'the call after the seal is not the sealed frame’s child');
  // The parent's exit is last: the child closed, then the frame sealed.
  const exits = of(out.recs, 'RETURN');
  assert.deepEqual(exits.map((r) => r.f), [inner.f, outer.f, after.f]);
});

// --- the frame `seal` must not touch ---------------------------------------

test('seal on a closed frame writes nothing, and seal outside a frame is quiet', () => {
  // `seal` runs in a `finally`, so it runs on every path — including the two
  // where the frame is already gone. Neither may write a second exit.
  const out = run(`
    ${FILE}
    const f = __srt.call(__sfile, 0);
    __srt.ret(f, 'done');
    __srt.seal(f);
    const g = __srt.call(__sfile, 1);
    __srt.thr(g, new Error('unwound'));
    __srt.seal(g);
    __srt.seal(null);
    console.log(JSON.stringify({ quiet: __srt.seal(null) === undefined }));
  `, { focus: 'f' });
  ok(out);

  assert.deepEqual(JSON.parse(out.res.stdout), { quiet: true });
  assert.deepEqual(of(out.recs, 'RETURN').map((r) => r.v.v), ["'done'"]);
  assert.equal(of(out.recs, 'UNWIND').length, 1);
});

test('pend hands the value back untouched and writes no record of its own', () => {
  const out = run(`
    ${FILE}
    const f = __srt.call(__sfile, 0);
    const obj = { a: 1 };
    console.log(JSON.stringify({
      same: __srt.pend(f, obj) === obj,
      frameless: __srt.pend(null, 7),
      closed: (__srt.ret(f, 'done'), __srt.pend(f, 9)),
    }));
  `, { focus: 'f' });
  ok(out);

  // `pend` is a pass-through: the program returns exactly what it wrote, and
  // the wire carries nothing until the frame is sealed.
  assert.deepEqual(JSON.parse(out.res.stdout), { same: true, frameless: 7, closed: 9 });
  assert.deepEqual(of(out.recs, 'RETURN').map((r) => r.v.v), ["'done'"]);
});
