// The runtime, read back off its own spools. Nothing here is a mock — what is
// asserted is the wire, which is the only thing the converter (Task 5) reads.
// The child-process helper every test uses is `helpers/rt-child.mjs`; the
// spool's own tests — flush, signals, exit, the off tier — are in
// `rt.spool.test.mjs`, moved there verbatim to keep both files under 800 lines.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';

import { VERSION } from '../src/index.mjs';
import { transformSource } from '../src/transform.mjs';
import { RT, of, ok, one, run } from './helpers/rt-child.mjs';

/**
 * Every record kind's keys, verbatim from the design's wire table.
 * @type {Record<string, string[]>}
 */
const KEYS = {
  BOOT: ['e', 'wire', 'pid', 'ppid', 'threadId', 'isMainThread', 'argv', 'cwd', 'env',
    'envHash', 'node', 'version', 'tier', 'invocation', 'startTs', 'ts'],
  FILE: ['e', 'id', 'rel', 'abs', 'codes', 'sha'],
  TASK: ['e', 'id', 'name', 'basis', 'conflict'],
  CALL: ['e', 'f', 'p', 'file', 'c', 't', 'ts'],
  RETURN: ['e', 'f', 't', 'v', 'ts'],
  UNWIND: ['e', 'f', 't', 'x', 'ts'],
  YIELD: ['e', 'f', 't', 'k', 'ts'],
  RESUME: ['e', 'f', 't', 'ts'],
  RAISE: ['e', 'f', 't', 'x', 'l', 'how', 'ts'],
  HANDLED: ['e', 'f', 't', 'x', 'l', 'how', 'ts'],
  UNHANDLED: ['e', 'x', 'ts'],
  FILE_START: ['e', 'path', 'environment'],
  SEEN: ['e', 'name'],
  EXIT: ['e', 'code', 'endTs', 'ts'],
};

/**
 * Keys a record carries only when it has something to say: `signal` on the EXIT
 * of a signalled container (R13), `name_trunc` on a TASK whose name was cut
 * (R14). Each test that can produce one asserts it appears exactly then.
 * @type {Record<string, string[]>}
 */
const OPTIONAL = { EXIT: ['signal'], TASK: ['name_trunc'], SEEN: ['name_trunc'] };

/**
 * The `x` an exception record carries, and the two flags that appear only when
 * the cap cut something (R14a, TRACE-FORMAT §5).
 */
const EXC = { required: ['kind', 'type', 'msg', 'serial'], optional: ['trunc', 'type_trunc'] };

// ---------------------------------------------------------------------------

test('boot names the writer, the invocation and the environment', () => {
  const out = run(`__srt.seen('a test');`);
  ok(out);
  const boot = out.recs[0];
  assert.equal(boot.e, 'BOOT');
  assert.equal(boot.wire, 1);
  assert.equal(boot.tier, 'call');
  assert.equal(boot.invocation, 'inv-1');
  assert.equal(boot.node, process.version);
  assert.equal(boot.version, '0.1.1');
  assert.equal(boot.isMainThread, true);
  assert.equal(boot.threadId, 0);
  assert.equal(boot.ppid, process.pid);
  assert.deepEqual(boot.env, out.env);
  assert.ok(boot.startTs > 1_700_000_000 && boot.startTs < 4_000_000_000, 'startTs is epoch seconds');
  assert.ok(Number.isFinite(boot.ts) && boot.ts > 0, 'ts is monotonic nanoseconds');
  // The recipe, recomputed from the record's own env: sorted `k=v` lines,
  // sha256, first 16 hex.
  const lines = Object.keys(boot.env).sort().map((k) => `${k}=${boot.env[k]}`).join('\n');
  assert.equal(boot.envHash, crypto.createHash('sha256').update(lines).digest('hex').slice(0, 16));
  // One spool per (pid, threadId).
  assert.deepEqual(out.files, [`${boot.pid}-0.jsonl`]);
});

test('every record carries exactly its wire keys', () => {
  const out = run(`
    const fid = __srt.file('src/a.test.ts', '/w/src/a.test.ts', [['a', 1, 'function']], 'sha');
    __srt.fileStart('src/a.test.ts', 'jsdom');
    __srt.seen('a > b');
    const [, long] = __srt.task('L'.repeat(300), () => {}, 1);
    long();
    const [, activate] = __srt.task('b', async () => {
      const f = __srt.call(fid, 0);
      __srt.r(f, await __srt.y(f, Promise.resolve(1), 0));
      __srt.raise(f, new Error('raised'), 7);
      __srt.handled(f, new Error('handled'), 8, 'catch');
      const g = __srt.call(fid, 0);
      __srt.thr(g, new Error('unwound'));
      __srt.ret(f, 'done');
    }, 1);
    await activate();
    Promise.reject(new Error('nobody catches this'));
    await new Promise((res) => setTimeout(res, 20));
  `);
  ok(out);
  const seen = new Set();
  for (const rec of out.recs) {
    const required = KEYS[rec.e];
    assert.ok(required, `unknown record kind ${rec.e}`);
    const keys = Object.keys(rec);
    const allowed = [...required, ...(OPTIONAL[rec.e] ?? [])];
    assert.deepEqual(keys.filter((k) => !allowed.includes(k)), [], `extra keys on ${rec.e}`);
    assert.deepEqual(required.filter((k) => !keys.includes(k)), [], `missing keys on ${rec.e}`);
    if (rec.x !== undefined) {
      const inner = Object.keys(rec.x);
      const ok_ = [...EXC.required, ...EXC.optional];
      assert.deepEqual(inner.filter((k) => !ok_.includes(k)), [], `extra keys on ${rec.e}.x`);
      assert.deepEqual(EXC.required.filter((k) => !inner.includes(k)), [],
        `missing keys on ${rec.e}.x`);
    }
    seen.add(rec.e);
  }
  // The optional keys appear exactly where they are earned: one cut name, and
  // no `signal` at all on a container that chose its own exit.
  const cut = out.recs.filter((r) => r.name_trunc !== undefined);
  assert.equal(cut.length, 1, 'exactly the task whose name was cut says so');
  assert.deepEqual([cut[0].e, cut[0].name_trunc], ['TASK', true]);
  assert.deepEqual(out.recs.filter((r) => r.signal !== undefined), []);
  // Nothing in this child was long enough to cut, so no record claims one.
  assert.deepEqual(out.recs.filter((r) => r.e === 'SEEN' && r.name_trunc !== undefined), []);
  assert.deepEqual(out.recs.filter((r) => r.x && (r.x.trunc || r.x.type_trunc)), []);
  assert.deepEqual([...seen].sort(), Object.keys(KEYS).sort(), 'every record kind exercised');
  assert.equal(out.recs[0].e, 'BOOT');
  assert.equal(out.recs[out.recs.length - 1].e, 'EXIT');
});

test('task isolation', () => {
  // Two tasks whose awaits interleave: the second resumes while the first is
  // still parked. Attribution is by async context, so no row of one carries the
  // other's id, and a frame opened after both is in no task at all.
  const out = run(`
    const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const body = (c, ms) => async () => {
      const f = __srt.call(fid, c);
      __srt.r(f, await __srt.y(f, sleep(ms), 0));
      __srt.ret(f, c);
    };
    const [, slow] = __srt.task('one', body(0, 40), 1);
    const [, fast] = __srt.task('two', body(1, 1), 1);
    await Promise.all([slow(), fast()]);
    const after = __srt.call(fid, 2);
    __srt.ret(after, null);
  `);
  ok(out);
  const [first, second] = of(out.recs, 'TASK');
  assert.deepEqual([first.name, second.name], ['one', 'two']);
  /** @type {Map<number, number>} */
  const code = new Map(of(out.recs, 'CALL').map((r) => [r.f, r.c]));
  const want = [first.id, second.id, null];
  for (const rec of out.recs) {
    if (rec.f == null) continue;
    const c = code.get(rec.f);
    assert.notEqual(c, undefined, `frame ${rec.f} was opened by a CALL`);
    assert.equal(rec.t, want[Number(c)], `${rec.e} of frame ${rec.f}`);
  }
  const leaked = out.recs.filter((r) => r.t === first.id && code.get(r.f) === 1);
  assert.equal(leaked.length, 0, 'zero rows of the second task carry the first task id');
  // The interleaving is real: the fast task resumed before the slow one did.
  const resumes = out.recs.map((r, i) => [r, i]).filter(([r]) => r.e === 'RESUME');
  assert.equal(resumes.length, 2);
  assert.equal(resumes[0][0].t, second.id, 'the second task resumed first');
});

test('stack pops at yield', () => {
  // While a frame is parked it is off its task's stack, so a call made in the
  // meantime is parentless; after RESUME the frame is the parent again.
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const [, activate] = __srt.task('t', async () => {
      const f = __srt.call(fid, 0);
      const parked = __srt.y(f, Promise.resolve('v'), 0);
      const sibling = __srt.call(fid, 1);
      __srt.ret(sibling, 1);
      __srt.r(f, await parked);
      const child = __srt.call(fid, 2);
      __srt.ret(child, 2);
      __srt.ret(f, 3);
    }, 1);
    await activate();
  `);
  ok(out);
  const calls = of(out.recs, 'CALL');
  const [parent, sibling, child] = calls;
  assert.equal(parent.p, null, 'the first frame of a task has no parent');
  assert.equal(sibling.p, null, 'a call made while the frame is parked is parentless');
  assert.equal(child.p, parent.f, 'after RESUME the parked frame is the parent again');
  const yielded = one(out.recs, 'YIELD');
  assert.equal(yielded.k, 'await');
  assert.equal(yielded.f, parent.f);
  assert.ok(out.recs.indexOf(yielded) < out.recs.indexOf(one(out.recs, 'RESUME')));
});

test('yield kind names the suspension', () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const f = __srt.call(fid, 0);
    __srt.r(f, __srt.y(f, 'a', 0));
    __srt.r(f, __srt.y(f, 'b', 1));
    __srt.ret(f, null);
  `);
  ok(out);
  assert.deepEqual(of(out.recs, 'YIELD').map((r) => r.k), ['await', 'yield']);
});

test('serial survives rethrow', () => {
  const out = run(`
    const err = new Error('boom');
    __srt.raise(null, err, 1);
    __srt.raise(null, err, 2);
    __srt.raise(null, 'oops', 3);
    __srt.raise(null, 'oops', 4);
  `);
  ok(out);
  const [a, b, c, d] = of(out.recs, 'RAISE');
  assert.equal(a.x.serial, b.x.serial, 'a rethrown object keeps its serial');
  assert.notEqual(c.x.serial, d.x.serial, 'a rethrown string cannot be followed');
  assert.deepEqual([a.x.kind, a.x.type, a.x.msg], ['throw', 'Error', 'boom']);
  assert.deepEqual([c.x.kind, c.x.type, c.x.msg], ['throw', 'string', 'oops']);
  assert.deepEqual([a.l, b.l, c.l, d.l], [1, 2, 3, 4]);
});

test('dbg caps', () => {
  const out = run(`
    import util from 'node:util';
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const capture = (v) => { const f = __srt.call(fid, 0); __srt.ret(f, v); };
    capture('a'.repeat(10000));
    const wide = {};
    for (let i = 0; i < 60; i += 1) wide['key' + i] = i;
    capture(wide);
    capture('\\u2603'.repeat(200));
    capture(undefined);
    capture({ [util.inspect.custom]() { throw new Error('hostile'); } });
  `);
  ok(out);
  const [long, wide, snow, nothing, hostile] = of(out.recs, 'RETURN').map((r) => r.v);
  // A 10 kB string is cut by `maxStringLength: 100` before the byte cap is
  // reached, so it lands well under 200 bytes and is not marked truncated:
  // the note the trace carries is the inspector's, not the cap's.
  assert.ok(long.v.startsWith("'aaaa"));
  assert.ok(long.v.endsWith('9900 more characters'));
  assert.equal(long.trunc, false);
  assert.ok(Buffer.byteLength(long.v) < 200);
  // A value whose inspection is genuinely long is cut to 200 bytes.
  assert.equal(Buffer.byteLength(wide.v), 200);
  assert.equal(wide.trunc, true);
  // The cut is on a character boundary, never through one.
  assert.equal(snow.trunc, true);
  assert.ok(Buffer.byteLength(snow.v) <= 200 && Buffer.byteLength(snow.v) > 190);
  assert.ok(!snow.v.includes('�'), 'no character was cut in half');
  assert.deepEqual(nothing, { k: 'dbg', v: 'undefined', trunc: false });
  assert.deepEqual(hostile, { k: 'unread' }, 'an inspector that throws reads unread');
});

test('task names come from the provider, cross-checked against the literal title', () => {
  const out = run(`
    let name = 'math > adds';
    __srt.nameProvider(() => name);
    const [, agrees] = __srt.task('adds', () => {}, 1);
    agrees();
    name = 'a different test entirely';
    const [, conflicts] = __srt.task('adds', () => {}, 1);
    conflicts();
    const [, each] = __srt.task('doubles %i', () => {}, 3);
    each();
    const [, computed] = __srt.task('adds', () => {}, 0);
    computed();
  `);
  ok(out);
  const tasks = of(out.recs, 'TASK');
  assert.deepEqual(tasks.map((t) => [t.name, t.basis, t.conflict]), [
    ['math > adds', 'vitest', false],
    // The provider named a test that is not this one: the lexical name wins and
    // the disagreement is on the record.
    ['adds', 'title', true],
    // A `.each` row's title is a template the provider expands; uncheckable.
    ['a different test entirely', 'vitest', false],
    // A title the transform could not read as a literal is uncheckable too --
    // and this stub provider handed the same full name to two registrations,
    // so the container's second run of that NAME is `#2` (R39). Real vitest
    // full titles are unique, which is why this is only reachable here.
    ['a different test entirely#2', 'vitest', false],
  ]);
  assert.deepEqual(tasks.map((t) => t.id), [1, 2, 3, 4]);
});

test('task names fall back to the lexical describe chain', () => {
  const out = run(`
    const [, outer] = __srt.suite('math', () => {
      const [, inner] = __srt.suite('addition', () => {
        const [, activate] = __srt.task('adds', () => {}, 1);
        activate();
        activate();
      });
      inner();
      const [, sibling] = __srt.task('subtracts', () => {}, 1);
      sibling();
    });
    outer();
    const [, top] = __srt.task('at the top', () => {}, 1);
    top();
    const [, unnamed] = __srt.task({ not: 'a string' }, () => {}, 0);
    unnamed();
    __srt.nameProvider(() => { throw new Error('no state here'); });
    const [, hostile] = __srt.task('provider throws', () => {}, 1);
    hostile();
  `);
  ok(out);
  const tasks = of(out.recs, 'TASK');
  assert.deepEqual(tasks.map((t) => t.name), [
    'math > addition > adds',
    // The second activation of ONE registration.
    'math > addition > adds#2',
    'math > subtracts',
    'at the top',
    '<unnamed: title not a string>',
    'provider throws',
  ]);
  assert.deepEqual([...new Set(tasks.map((t) => t.basis))], ['title']);
  assert.deepEqual([...new Set(tasks.map((t) => t.conflict))], [false]);
});

test('a callback that is not a function is passed through in place', () => {
  const out = run(`
    const notATask = __srt.task('title', 'not a function', 1);
    const notASuite = __srt.suite('title', 42);
    const opts = { timeout: 100 };
    const fn = () => {};
    const withOptions = __srt.task('title', opts, fn, 1);
    const suiteWithOptions = __srt.suite('title', opts, fn);
    console.log(JSON.stringify({
      notATask,
      notASuite,
      withOptions: [withOptions.length, withOptions[1] === opts, withOptions[2] === fn],
      suiteWithOptions: [suiteWithOptions.length, suiteWithOptions[1] === opts,
        suiteWithOptions[2] === fn],
    }));
  `);
  ok(out);
  const got = JSON.parse(out.res.stdout);
  assert.deepEqual(got.notATask, ['title', 'not a function'], 'the flags are consumed, the rest kept');
  assert.deepEqual(got.notASuite, ['title', 42]);
  assert.deepEqual(got.withOptions, [3, true, false], 'the options stay between title and wrapper');
  assert.deepEqual(got.suiteWithOptions, [3, true, false]);
  assert.equal(of(out.recs, 'TASK').length, 0, 'nothing that is not a function opens a task');
});

test('a frame closes once', () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const f = __srt.call(fid, 0);
    __srt.thr(f, new Error('unwound'));
    const late = __srt.ret(f, 'late');
    __srt.thr(f, new Error('again'));
    const sibling = __srt.call(fid, 1);
    console.log(JSON.stringify({ late }));
  `);
  ok(out);
  assert.equal(of(out.recs, 'UNWIND').length, 1, 'the second exit of a closed frame is a no-op');
  assert.equal(of(out.recs, 'RETURN').length, 0);
  assert.equal(JSON.parse(out.res.stdout).late, 'late', 'ret still returns its value');
  const [, sibling] = of(out.recs, 'CALL');
  assert.equal(sibling.p, null, 'a closed frame is off the stack');
});

test('throw flow outside a frame carries a null frame', () => {
  const out = run(`
    const raised = __srt.raise(null, new Error('a'), 3);
    __srt.handled(null, new Error('b'), 4, 'sink_empty_catch');
    let swallowed = null;
    const sink = __srt.emptyCatch(null, 9, (reason) => { swallowed = reason; return 'from the original'; });
    const returned = sink('why');
    const [, activate] = __srt.task('t', () => { __srt.raise(null, 'in a task', 5); }, 1);
    activate();
    console.log(JSON.stringify({ raised: raised.message, swallowed, returned }));
  `);
  ok(out);
  const got = JSON.parse(out.res.stdout);
  assert.equal(got.raised, 'a', 'raise returns the value the source throws');
  assert.equal(got.swallowed, 'why', 'the original callback still runs');
  assert.equal(got.returned, 'from the original');
  const [outside, inTask] = of(out.recs, 'RAISE');
  assert.deepEqual([outside.f, outside.t, outside.how], [null, null, 'throw']);
  assert.equal(inTask.f, null);
  assert.equal(inTask.t, one(out.recs, 'TASK').id, 'a frameless raise still names its task');
  const [clause, callback] = of(out.recs, 'HANDLED');
  assert.deepEqual([clause.f, clause.how, clause.x.kind], [null, 'sink_empty_catch', 'throw']);
  assert.deepEqual([callback.f, callback.how, callback.x.kind],
    [null, 'sink_empty_catch_callback', 'rejection']);
  assert.deepEqual([callback.x.type, callback.x.msg, callback.l], ['string', 'why', 9]);
});

test('a hostile value never crashes the recorder', () => {
  const out = run(`
    __srt.raise(null, { get message() { throw new Error('nope'); } }, 1);
    __srt.raise(null, Object.create(null), 2);
    __srt.raise(null, { constructor: 5 }, 3);
    const sym = Symbol('s');
    __srt.raise(null, sym, 4);
    __srt.raise(null, sym, 5);
    __srt.raise(null, null, 6);
    __srt.raise(null, undefined, 7);
  `);
  ok(out);
  const raised = of(out.recs, 'RAISE');
  assert.deepEqual(raised.map((r) => [r.x.type, r.x.msg]), [
    ['Object', '<unread>'],
    ['unread', '<unread>'],
    ['unread', '[object Object]'],
    ['symbol', 'Symbol(s)'],
    ['symbol', 'Symbol(s)'],
    ['object', 'null'],
    ['undefined', 'undefined'],
  ]);
  assert.notEqual(raised[3].x.serial, raised[4].x.serial, 'a symbol is a primitive');
});

test("a frame's records agree about the frame's task", () => {
  // The `raise`/`handled` are reported from a turn that is outside the task's
  // async context entirely: a record that names a frame belongs to that
  // frame's task, not to whatever the store happens to hold.
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    let frame = null;
    const [, activate] = __srt.task('t', () => { frame = __srt.call(fid, 0); }, 1);
    activate();
    setImmediate(() => {
      const err = new Error('later');
      __srt.raise(frame, err, 3);
      __srt.handled(frame, err, 4, 'catch');
      __srt.ret(frame, 'done');
    });
  `);
  ok(out);
  const task = one(out.recs, 'TASK');
  const framed = out.recs.filter((r) => r.f !== undefined && r.f !== null);
  assert.deepEqual(framed.map((r) => r.e), ['CALL', 'RAISE', 'HANDLED', 'RETURN']);
  assert.deepEqual([...new Set(framed.map((r) => r.t))], [task.id],
    'every row of one frame carries one task');
});

test('a consumer name is capped on the wire', () => {
  const out = run(`
    __srt.nameProvider(() => 'p'.repeat(500));
    const [, activate] = __srt.task('short', () => {}, 0);
    activate();
    activate();
    const [, snow] = __srt.task('\u2603'.repeat(120), () => {}, 1);
    snow();
    __srt.nameProvider(null);
    const [, brief] = __srt.task('brief', () => {}, 1);
    brief();
    __srt.seen('s'.repeat(500));
    __srt.seen('seen briefly');
  `);
  ok(out);
  const [first, second, snow, brief] = of(out.recs, 'TASK');
  assert.equal(Buffer.byteLength(first.name), 200);
  assert.equal(first.name_trunc, true);
  // The `#k` of an activation is the recorder's own word and survives the cut.
  assert.equal(second.name, `${first.name}#2`);
  assert.equal(second.name_trunc, true);
  // A cut between characters, never through one.
  assert.ok(Buffer.byteLength(snow.name) <= 200 && Buffer.byteLength(snow.name) > 190);
  assert.ok(!snow.name.includes('\ufffd'));
  assert.equal(snow.name_trunc, true);
  // A name that fits says nothing about a cut that did not happen.
  assert.equal(brief.name, 'brief');
  assert.equal(Object.hasOwn(brief, 'name_trunc'), false);
  // A name the harness counted is cut by the same rule and says so the same
  // way: the converter compares the two, so they must be cut identically.
  const [cutSeen, wholeSeen] = of(out.recs, 'SEEN');
  assert.equal(Buffer.byteLength(cutSeen.name), 200);
  assert.equal(cutSeen.name_trunc, true);
  assert.equal(wholeSeen.name, 'seen briefly');
  assert.equal(Object.hasOwn(wholeSeen, 'name_trunc'), false);
});

test('a cut exception says what was cut', () => {
  // Every `exc` the runtime writes goes through one formatter, so the flags
  // are asserted on all four record kinds that carry one.
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const wordy = new Error('m'.repeat(500));
    __srt.raise(null, wordy, 1);
    __srt.handled(null, wordy, 2, 'catch');
    const f = __srt.call(fid, 0);
    __srt.thr(f, wordy);
    class C {}
    Object.defineProperty(C, 'name', { value: 'T'.repeat(400) });
    __srt.raise(null, new C(), 3);
    __srt.raise(null, new Error('\u2603'.repeat(200)), 4);
    __srt.raise(null, new Error('short'), 5);
    Promise.reject(new Error('u'.repeat(500)));
    await new Promise((res) => setTimeout(res, 20));
  `);
  ok(out);
  const [wordy, named, snow, short] = of(out.recs, 'RAISE').map((r) => r.x);
  // A message longer than the budget is cut to it, and says so.
  assert.equal(Buffer.byteLength(wordy.msg), 200);
  assert.equal(wordy.trunc, true);
  assert.equal(wordy.type, 'Error');
  assert.equal(Object.hasOwn(wordy, 'type_trunc'), false, 'the type was whole');
  // The same value through the other three kinds.
  for (const rec of [one(out.recs, 'HANDLED'), one(out.recs, 'UNWIND'), one(out.recs, 'UNHANDLED')]) {
    assert.equal(Buffer.byteLength(rec.x.msg), 200, `${rec.e} msg`);
    assert.equal(rec.x.trunc, true, `${rec.e} trunc`);
  }
  // A type name longer than the budget is cut on its own flag, and a value
  // with no message of its own has a short one.
  assert.equal(Buffer.byteLength(named.type), 200);
  assert.equal(named.type_trunc, true);
  assert.equal(named.msg, '[object Object]');
  assert.equal(Object.hasOwn(named, 'trunc'), false, 'the message was whole');
  // The cut falls between characters.
  assert.equal(snow.trunc, true);
  assert.ok(Buffer.byteLength(snow.msg) <= 200 && Buffer.byteLength(snow.msg) > 190);
  assert.ok(!snow.msg.includes('\ufffd'));
  // Nothing cut, nothing claimed — which is what makes the text an identity.
  assert.deepEqual(Object.keys(short).sort(), ['kind', 'msg', 'serial', 'type']);
});

test('a closed frame neither parks nor resumes', () => {
  const out = run(`
    const fid = __srt.file('t.ts', '/w/t.ts', [], 'sha');
    const f = __srt.call(fid, 0);
    __srt.ret(f, 'v');
    const parked = __srt.y(f, 'yielded', 0);
    const resumed = __srt.r(f, 'resumed');
    const sibling = __srt.call(fid, 1);
    __srt.ret(sibling, null);
    console.log(JSON.stringify({ parked, resumed }));
  `);
  ok(out);
  assert.deepEqual(of(out.recs, 'YIELD'), [], 'a closed frame does not park');
  assert.deepEqual(of(out.recs, 'RESUME'), [], 'a closed frame does not resume');
  assert.deepEqual(JSON.parse(out.res.stdout), { parked: 'yielded', resumed: 'resumed' },
    'both still return their value');
  const [, sibling] = of(out.recs, 'CALL');
  assert.equal(sibling.p, null, 'a closed frame was not put back on the stack');
});

test('the version on the wire is the package version', () => {
  // BOOT's `version` becomes every trace's `recorder` string, so these two must
  // not drift (R15). `boot names the writer` pins the other end of the chain.
  const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  assert.equal(VERSION, pkg.version);
});

test("the transform's own output runs against this runtime", () => {
  // Not a golden: the transform's real emitted calls, executed. This is the
  // only test that can catch the two modules disagreeing about an arity, a
  // return value or the order of a spliced argument list.
  const require = createRequire(import.meta.url);
  const source = [
    'function describe(title, fn) { fn(); }',
    'function it(title, fn) { fn(); }',
    'function guard(n) { if (n < 0) throw new Error("neg"); return n; }',
    'function* counter() { yield 1; yield 2; }',
    'async function twice(n) { return await Promise.resolve(n * 2); }',
    'describe("math", () => {',
    '  it("adds", async () => {',
    '    for (const x of counter()) guard(x);',
    '    await twice(3);',
    '    try { guard(-1); } catch (e) { }',
    '    await Promise.reject(new Error("r")).catch(() => {});',
    '  });',
    '});',
  ].join('\n');
  const out = transformSource(source, '/w/prog.test.mjs',
    { ts: require('typescript'), root: '/w', rtPath: RT });
  assert.ok(out && out.code, 'the transform produced instrumented source');
  const ran = run(out.code, { raw: true });
  ok(ran);
  const task = one(ran.recs, 'TASK');
  assert.deepEqual([task.name, task.basis, task.conflict], ['math > adds', 'title', false]);
  // The `describe`/`it` spread came back in the right order, and the callback
  // ran inside the task.
  const calls = of(ran.recs, 'CALL');
  const site = (/** @type {any} */ c) => out.manifest.instrumented[c.c].qualname;
  // `describe` and `it` are the consumer's own functions here, and a suite is
  // not a task: those three frames run outside every task, and everything the
  // wrapped TEST callback reaches is inside one — which is the whole of what
  // the task boundary claims.
  assert.deepEqual([...new Set(calls.filter((c) => c.t === null).map(site))],
    ['describe', '<anonymous>', 'it']);
  const inTask = calls.filter((c) => c.t === task.id);
  assert.deepEqual([...new Set(inTask.map(site))].sort(),
    ['<anonymous>.<anonymous>', '<anonymous>.<anonymous>.<anonymous>', 'counter', 'guard', 'twice']);
  // A generator parked at `yield` is not the parent of what runs next: the
  // `guard(x)` calls in the loop body belong to the test callback's frame.
  const generator = calls.find((c) => site(c) === 'counter');
  assert.deepEqual(calls.filter((c) => c.p === generator.f), [],
    'nothing nests under a parked generator');
  const body = calls.find((c) => site(c) === '<anonymous>.<anonymous>');
  assert.deepEqual([...new Set(calls.filter((c) => site(c) === 'guard').map((c) => c.p))],
    [body.f], 'the loop body called guard, not the generator');
  // One thrown object, followed from the `throw` through the unwind into the
  // clause that swallowed it.
  const serial = one(ran.recs, 'RAISE').x.serial;
  assert.equal(one(ran.recs, 'UNWIND').x.serial, serial);
  const [clause, callback] = of(ran.recs, 'HANDLED');
  assert.deepEqual([clause.how, clause.x.serial], ['sink_empty_catch', serial]);
  assert.deepEqual([callback.how, callback.x.kind], ['sink_empty_catch_callback', 'rejection']);
});


test('a generator its consumer closed early closes as a return it never read', () => {
  // R40. `break` out of a `for…of` issues `.return()` on the iterator, which
  // resumes the generator body at the `yield` with a RETURN completion: neither
  // the `ret` at the end of the body nor the `thr` in the catch runs, and the
  // frame stayed open to the end of the recording. It was reported as
  // `suspended at end of recording` — a loss claim about a generator that was
  // deliberately closed. The transform's `finally` calls `gclose`, which closes
  // it as a `return` whose value is unread: `.return()`'s value is the
  // consumer's, not the body's, and the body never produced one.
  const require = createRequire(import.meta.url);
  const source = [
    'function* counter() { yield 1; yield 2; yield 3; }',
    'function drain() { for (const x of counter()) { if (x === 2) break; } }',
    'drain();',
  ].join('\n');
  const out = transformSource(source, '/w/gen.mjs',
    { ts: require('typescript'), root: '/w', rtPath: RT });
  assert.ok(out && out.code, 'the transform produced instrumented source');
  const ran = run(out.code, { raw: true });
  ok(ran);
  const site = (/** @type {any} */ c) => out.manifest.instrumented[c.c].qualname;
  const generator = of(ran.recs, 'CALL').find((c) => site(c) === 'counter');
  const closed = of(ran.recs, 'RETURN').find((r) => r.f === generator.f);
  assert.ok(closed, 'the generator frame closed');
  assert.deepEqual(closed.v, { k: 'unread' });
  // It closed as a RETURN and not as an UNWIND: nothing was thrown at it.
  assert.deepEqual(of(ran.recs, 'UNWIND').filter((r) => r.f === generator.f), []);
  // And the two `yield`s it did reach are still on the record, in order.
  assert.deepEqual(of(ran.recs, 'YIELD').filter((r) => r.f === generator.f)
    .map((r) => r.k), ['yield', 'yield']);
  assert.ok(ran.recs.indexOf(closed) > ran.recs.lastIndexOf(
    of(ran.recs, 'YIELD').filter((r) => r.f === generator.f).at(-1)));
});

test('a generator that runs to its own end still closes with its own value', () => {
  // The `finally` must not overwrite an outcome the body reached: `gclose` is a
  // no-op on a frame `ret` (or `thr`) has already closed. Break this and every
  // generator in every recording reads `<unread>`.
  const require = createRequire(import.meta.url);
  const source = [
    'function* two() { yield 1; return 7; }',
    'function drain() { for (const x of two()) { void x; } }',
    'drain();',
  ].join('\n');
  const out = transformSource(source, '/w/gen2.mjs',
    { ts: require('typescript'), root: '/w', rtPath: RT });
  assert.ok(out && out.code, 'the transform produced instrumented source');
  const ran = run(out.code, { raw: true });
  ok(ran);
  const site = (/** @type {any} */ c) => out.manifest.instrumented[c.c].qualname;
  const generator = of(ran.recs, 'CALL').find((c) => site(c) === 'two');
  const closes = of(ran.recs, 'RETURN').filter((r) => r.f === generator.f);
  assert.equal(closes.length, 1, 'a frame closes once');
  assert.deepEqual(closes[0].v, { k: 'dbg', v: '7', trunc: false });
});

test('a name the harness could not supply is not a test called "null"', () => {
  // The setup file passes `expect.getState().currentTestName ?? null`, so a
  // `beforeEach` that runs outside any test hands `seen` a null. `String(null)`
  // made that a SEEN named `null`, which the converter counts in `tests_seen`:
  // a test the harness never registered, inflating the one number whose whole
  // job is to name the shortfall against tasks.
  const out = run(`
    __srt.seen(null);
    __srt.seen(undefined);
    __srt.seen(7);
    __srt.seen('a real one');
  `);
  ok(out);
  assert.deepEqual(of(out.recs, 'SEEN').map((r) => r.name), ['a real one']);
});
