// The focus tier's half of the wire, read back off real spools. `rt.test.mjs`
// holds the key tables that pin every record's shape -- LINE and the two
// optional keys are declared THERE -- and this file holds what the new records
// SAY: a completed statement's deltas, a focused CALL's arguments, the identity
// a captured object carries, and the two declaration shapes a BOOT can have.
// Nothing here is a mock; the child-process helper is `helpers/rt-child.mjs`.
import assert from 'node:assert/strict';
import test from 'node:test';

import { VERSION } from '../src/index.mjs';
import { of, ok, one, run } from './helpers/rt-child.mjs';

// --- LINE ------------------------------------------------------------------

test('a LINE record is one completed statement of a focused function', () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const [, activate] = __srt.task('t', () => {
      const f = __srt.call(fid, 0, ['n', 3]);
      __srt.line(f, 4, ['sum', 3]);
      __srt.line(f, 5, ['sum', 6, 'label', 'a'], []);
      __srt.line(f, 6, [], ['discount']);
      __srt.ret(f, 6);
    }, 1);
    activate();
  `);
  ok(out);
  const task = one(out.recs, 'TASK');
  const frame = one(out.recs, 'CALL');
  const lines = of(out.recs, 'LINE');
  assert.equal(lines.length, 3);
  // Every LINE names the frame whose statement it was and that frame's task.
  assert.deepEqual([...new Set(lines.map((r) => r.f))], [frame.f]);
  assert.deepEqual([...new Set(lines.map((r) => r.t))], [task.id]);
  assert.deepEqual(lines.map((r) => r.l), [4, 5, 6]);
  assert.ok(lines.every((r) => Number.isFinite(r.ts) && r.ts > 0), 'ts is monotonic nanoseconds');
  // `d` is the pair list read two at a time: a name, then the capture of what
  // it held when the statement completed.
  assert.deepEqual(lines[0].d, { sum: { k: 'dbg', v: '3', trunc: false } });
  assert.deepEqual(lines[1].d, {
    sum: { k: 'dbg', v: '6', trunc: false },
    label: { k: 'dbg', v: "'a'", trunc: false },
  });
  assert.deepEqual(lines[2].d, {}, 'a statement that changed nothing readable says so');
  // `u` appears only where there is a name to report as out of scope: an empty
  // unbound list is not a claim, so it is not written.
  assert.equal(Object.hasOwn(lines[0], 'u'), false);
  assert.equal(Object.hasOwn(lines[1], 'u'), false);
  assert.deepEqual(lines[2].u, ['discount']);
  // The statements are on the record in the order they completed, between the
  // CALL that opened the frame and the RETURN that closed it.
  const at = (/** @type {any} */ r) => out.recs.indexOf(r);
  assert.ok(at(frame) < at(lines[0]) && at(lines[2]) < at(one(out.recs, 'RETURN')));
});

test('a LINE outside a live frame is not written', () => {
  // Three ways there is no statement of a focused function to report: the
  // frame that would own it was never opened, it has already closed, and the
  // whole runtime is off. None of them may write a row, and none may throw.
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    __srt.line(null, 1, ['x', 1]);
    const f = __srt.call(fid, 0);
    __srt.ret(f, 'done');
    __srt.line(f, 2, ['x', 2]);
    const g = __srt.call(fid, 1);
    __srt.thr(g, new Error('unwound'));
    __srt.line(g, 3, ['x', 3]);
  `);
  ok(out);
  assert.deepEqual(of(out.recs, 'LINE'), [],
    'a frameless, a returned and an unwound frame each report no statement');

  const off = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const f = __srt.call(fid, 0, ['n', 1]);
    __srt.line(f, 1, ['x', 1], ['y']);
    console.log(JSON.stringify({ frame: f, quiet: __srt.line(null, 2, []) === undefined }));
  `, { tier: 'off' });
  ok(off);
  assert.deepEqual(off.files, [], 'the tier is read once at load and off creates nothing');
  assert.deepEqual(JSON.parse(off.res.stdout), { frame: null, quiet: true },
    'both still return, and the program is unchanged');
});

test('a LINE in a frame that parked and resumed carries that frame', () => {
  // A parked frame is off its task's stack, so the statement that runs after
  // the await must still be attributed to the frame it belongs to and not to
  // whatever else the task was doing meanwhile.
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const [, activate] = __srt.task('t', async () => {
      const f = __srt.call(fid, 0, ['n', 1]);
      __srt.line(f, 4, ['before', 1]);
      __srt.r(f, await __srt.y(f, Promise.resolve('v'), 0));
      const sibling = __srt.call(fid, 1);
      __srt.line(sibling, 9, ['own', 'x']);
      __srt.ret(sibling, null);
      __srt.line(f, 6, ['after', 2]);
      __srt.ret(f, null);
    }, 1);
    await activate();
  `);
  ok(out);
  const task = one(out.recs, 'TASK');
  const [outer, sibling] = of(out.recs, 'CALL');
  const lines = of(out.recs, 'LINE');
  assert.deepEqual(lines.map((r) => [r.l, r.f]), [[4, outer.f], [9, sibling.f], [6, outer.f]]);
  assert.deepEqual([...new Set(lines.map((r) => r.t))], [task.id]);
  // The last one really is after the resumption, not before the park.
  const at = (/** @type {any} */ r) => out.recs.indexOf(r);
  assert.ok(at(one(out.recs, 'RESUME')) < at(lines[2]));
  assert.deepEqual(lines[2].d, { after: { k: 'dbg', v: '2', trunc: false } });
});

// --- the focused CALL's arguments -------------------------------------------

test("a focused CALL carries its arguments and an unfocused one says nothing", () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const focused = __srt.call(fid, 0, ['a', 1]);
    const many = __srt.call(fid, 1, ['key', 'rate', 'rows', [1, 2]]);
    const none = __srt.call(fid, 2, []);
    const unfocused = __srt.call(fid, 3);
    for (const f of [focused, many, none, unfocused]) __srt.ret(f, null);
  `);
  ok(out);
  const [focused, many, none, unfocused] = of(out.recs, 'CALL');
  assert.deepEqual(focused.a, { a: { k: 'dbg', v: '1', trunc: false } });
  assert.deepEqual(many.a, {
    key: { k: 'dbg', v: "'rate'", trunc: false },
    rows: { k: 'dbg', v: '[ 1, 2 ]', trunc: false, oid: 1, type: 'Array' },
  });
  // A focused function that takes no arguments says so with an empty map; an
  // unfocused one has no key at all, which is what tells a reader its
  // arguments were not read rather than that there were none.
  assert.deepEqual(none.a, {});
  assert.equal(Object.hasOwn(unfocused, 'a'), false);
});

// --- identity ---------------------------------------------------------------

test('a captured object carries an identity, and a primitive carries none', () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const capture = (v) => { const f = __srt.call(fid, 0); __srt.ret(f, v); };
    class Settings {}
    const shared = { retries: 3 };
    const twin = { retries: 3 };
    capture(shared);
    capture(twin);
    capture(shared);
    capture(7);
    capture('shared');
    capture(null);
    capture(undefined);
    capture(new Settings());
    capture(() => {});
    capture({ get constructor() { throw new Error('nope'); } });
    // The frame's own argument list and a statement's delta read the SAME
    // object through the same map: identity is the value's, not the record's.
    const f = __srt.call(fid, 1, ['settings', shared]);
    __srt.line(f, 3, ['alias', shared]);
    __srt.ret(f, null);
  `);
  ok(out);
  const [first, twin, again, num, str, nul, undef, instance, fn, hostile] =
    of(out.recs, 'RETURN').map((r) => r.v);
  // One object, two captures, one identity -- and a second object that renders
  // identically is a different one, which is the whole point of the serial.
  assert.equal(first.oid, again.oid);
  assert.equal(first.v, twin.v, 'the two render identically');
  assert.notEqual(first.oid, twin.oid, 'and are still not the same object');
  assert.deepEqual([first.type, twin.type], ['Object', 'Object']);
  // A primitive has no identity to carry, and this recorder does not invent
  // one: `null` is `typeof "object"` and is a primitive all the same.
  for (const [what, capture] of [['number', num], ['string', str], ['null', nul],
    ['undefined', undef]]) {
    assert.equal(Object.hasOwn(capture, 'oid'), false, `${what} has no oid`);
    assert.equal(Object.hasOwn(capture, 'type'), false, `${what} has no type`);
  }
  // `type` is the constructor's own name, `Function` for a function, and
  // `unread` for an object that lies about its constructor -- the same word
  // `exc.type` uses, from the same reader.
  assert.equal(instance.type, 'Settings');
  assert.equal(fn.type, 'Function');
  assert.equal(hostile.type, 'unread');
  assert.ok(hostile.oid > 0, 'a value whose type cannot be read still has an identity');
  // Every object seen here got its own serial, and no two share one.
  const oids = [first, twin, instance, fn, hostile].map((c) => c.oid);
  assert.equal(new Set(oids).size, oids.length);
  // The same object, through three different records.
  const call = of(out.recs, 'CALL').at(-1);
  assert.equal(call.a.settings.oid, first.oid);
  assert.equal(one(out.recs, 'LINE').d.alias.oid, first.oid);
});

test('a value that cannot be read carries neither identity nor type', () => {
  const out = run(`
    import util from 'node:util';
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const hostile = () => ({ [util.inspect.custom]() { throw new Error('no'); } });
    const f = __srt.call(fid, 0, ['x', hostile()]);
    __srt.line(f, 2, ['y', hostile()]);
    __srt.ret(f, hostile());
  `);
  ok(out);
  // `unread` is the whole record: an oid on it would say this recorder knows
  // which object it failed to read, and the only honest report is the failure.
  assert.deepEqual(one(out.recs, 'CALL').a.x, { k: 'unread' });
  assert.deepEqual(one(out.recs, 'LINE').d.y, { k: 'unread' });
  assert.deepEqual(one(out.recs, 'RETURN').v, { k: 'unread' });
});

// --- what a `finally` after a `return` cannot mint (blind spot 38) ----------

test('a statement in a finally after the return mints no row', () => {
  // Pinned as an ABSENCE: `return x` is spliced to `return __srt.ret(__sf,(x))`
  // and `ret` closes the frame BEFORE the program's own `finally` runs, so
  // `line` drops every row arriving from it. Blind spot 38 in
  // `HONESTY-BLIND-SPOTS.md`; a runtime that sealed the frame after the finally
  // would have to change this assertion on purpose. `g` is the asymmetry: after
  // a THROW the same finally's rows ARE recorded, because `thr` has not run yet.
  // Both bodies are written the way the transform splices a focused function.
  const out = run(`
    const __sfile = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    let cleanup = 0;
    function f() {const __sf=__srt.call(__sfile,0);try{
      try { return __srt.ret(__sf,(1)); } finally { cleanup = 1;__srt.line(__sf,3,['cleanup',cleanup]); }
    ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
    function g() {const __sf=__srt.call(__sfile,1);try{
      try { throw new Error('boom'); } finally { cleanup = 2;__srt.line(__sf,7,['cleanup',cleanup]); }
    ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
    f();
    try { g(); } catch {}
  `, { focus: 'f' });
  ok(out);
  const [returned, threw] = of(out.recs, 'CALL');
  const linesOf = (/** @type {any} */ frame) =>
    of(out.recs, 'LINE').filter((r) => r.f === frame.f);
  // The RETURN is on the record; the write the finally made is nowhere.
  assert.equal(one(out.recs, 'RETURN').f, returned.f);
  assert.deepEqual(linesOf(returned), [],
    'the finally ran after `ret` closed the frame, so its row was dropped');
  // The same finally, reached by a throw, IS recorded: `thr` runs after it.
  assert.deepEqual(linesOf(threw).map((r) => [r.l, r.d.cleanup.v]), [[7, '2']]);
});

// --- what a 0.3.0 recorder declares -----------------------------------------

test('the declaration says object identity always and line only under a focus', () => {
  // The child's `SENSORIUM_FOCUS` is the helper's to decide, never the shell's:
  // no `focus` option means the variable is not there, whatever this test run
  // was started with. The runtime reads it ONCE, as it reads the tier.
  const plain = run(`__srt.seen('a test');`);
  ok(plain);
  assert.deepEqual(plain.recs[0].capabilities, { err_flow: true, object_identity: true });

  const focused = run(`__srt.seen('a test');`, { focus: 'x' });
  ok(focused);
  assert.deepEqual(focused.recs[0].capabilities,
    { err_flow: true, object_identity: true, line: true, locals: true });
});

test("the recorder's version is 0.3.0", () => {
  // The number the focus tier ships under. `rt.test.mjs` holds the other two
  // ends of the chain: BOOT's `version`, and the package's own.
  assert.equal(VERSION, '0.3.0');
});
