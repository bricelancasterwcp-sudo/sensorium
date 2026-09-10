// The runtime. Every instrumented file imports this module and calls into it,
// so it imports `node:` builtins and nothing else, boots lazily on its first
// record, and is a complete no-op when the tier is not `call` — the whole cost
// of `off` is the transform (E1, 1.058).
//
// What it holds: the tasks a test callback opens, the frame stack each task
// owns, the values it is allowed to read, and the JSONL spool it appends to.
// One spool per container `(pid, threadId)`; one JSON object per line; the
// converter (`sensorium ts ingest`) is the only reader.
import { AsyncLocalStorage } from 'node:async_hooks';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { isMainThread, threadId } from 'node:worker_threads';

import { cap, dbg, exc } from './dbg.mjs';
import { VERSION } from './index.mjs';

/** @typedef {{id: number, name: string, stack: Frame[]}} Task */
/** @typedef {{id: number, task: Task|null, open: boolean, mark: Record<string, unknown>|null}} Frame */
/** @typedef {{name: string, basis: 'vitest'|'title', conflict: boolean}} Named */
/** @typedef {Record<string, unknown>} Record_ */

/** The tier is read ONCE, at module load: a run does not change instrument. */
const TIER = process.env.SENSORIUM_TIER ?? 'off';
const SPOOL_DIR = process.env.SENSORIUM_SPOOL ?? '';
const INVOCATION = process.env.SENSORIUM_INVOCATION ?? null;

const FLUSH_MS = 100;
const BUFFERED = 256;
/** @type {NodeJS.Signals[]} */
const SIGNALS = ['SIGTERM', 'SIGINT', 'SIGHUP'];
const UNNAMED = '<unnamed: title not a string>';

/**
 * What this recorder DECLARES it produces, written into every BOOT record and
 * passed through by the converter (§2.4). `err_flow` says the throw-flow rows
 * are complete enough to be judged: every `throw` statement, every `catch`
 * clause with the transform's verdict about its binding, every rejection
 * handler and every `finally` that discards a throw in flight. A spool whose
 * BOOT lacks the key reads `false`, so a trace this recorder did not write is
 * still refused — what it lacks is a record, not a permission.
 * @type {Record<string, boolean>}
 */
const CAPABILITIES = { err_flow: true };

/**
 * Recording at all. A tier that is not `call` records nothing, and neither does
 * a `call` tier with nowhere to write: a spool directory that was not given is
 * not guessed at. Cleared for good if the disk refuses a write.
 */
let on = TIER === 'call' && SPOOL_DIR !== '';

/** @type {AsyncLocalStorage<Task>} */
const als = new AsyncLocalStorage();
/** Frames running in no task — a hook, a module body — share the container's. */
/** @type {Frame[]} */
const rootStack = [];
/** The `describe` chain, per container, as it stands during collection. */
/** @type {{title: string}[]} */
const suiteStack = [];

/**
 * How many activations this CONTAINER has already given each capped task name.
 * Module-level and not per registration (R39): `#k` exists to tell two runs of
 * one test apart, and a reader who sees `#2` reads "the second time this name
 * ran here" -- which is a fact about the container, not about which `test(...)`
 * call produced it. Held in `wrapTask`'s closure, two registrations that shared
 * a name both printed the bare name and the ledger's promise was false.
 * @type {Map<string, number>}
 */
const activations = new Map();
/** @type {(() => unknown)|null} */
let provider = null;

let nextFile = 1;
let nextTask = 1;
let nextFrame = 1;

/** @type {string[]} */
const buf = [];
let spoolPath = '';
let booted = false;

/** Monotonic nanoseconds, the clock every record is stamped with. */
const now = () => Number(process.hrtime.bigint());

/**
 * The Rust recorder's recipe: sorted `k=v` lines, sha256, first 16 hex.
 * Comparable within one language, and the ledger says so.
 * @param {Record<string, string|undefined>} env
 * @returns {string}
 */
function envHash(env) {
  const lines = Object.keys(env).sort().map((k) => `${k}=${env[k]}`).join('\n');
  return crypto.createHash('sha256').update(lines).digest('hex').slice(0, 16);
}

// --- the spool -------------------------------------------------------------

/**
 * Append what is buffered. Exported because the harness wiring flushes at the
 * end of a test file, and cheap enough to call when there is nothing to write.
 * @returns {void}
 */
export function flush() {
  if (!on || spoolPath === '' || buf.length === 0) return;
  const text = `${buf.join('\n')}\n`;
  buf.length = 0;
  try {
    fs.appendFileSync(spoolPath, text);
  } catch (err) {
    // A recorder that cannot write says so once and stops; it does not retry
    // into a full disk, and it does not pretend the records were kept.
    on = false;
    process.emitWarning(`sensorium: recording stopped, cannot write ${spoolPath}: ${err}`);
  }
}

/**
 * Boot on the first record, and say whether there is anywhere to write.
 * @returns {boolean}
 */
function ready() {
  if (!on) return false;
  if (!booted) boot();
  return on;
}

/**
 * @param {Record_} rec
 * @returns {void}
 */
function emit(rec) {
  if (!ready()) return;
  buf.push(JSON.stringify(rec));
  if (buf.length >= BUFFERED) flush();
}

/**
 * The same, for the record kinds that carry a timestamp (`ts` last, always).
 * The clock is read AFTER the boot it may trigger, so BOOT's `ts` is the
 * smallest on the wire and no record appears to predate the run.
 * @param {Record_} rec
 * @returns {void}
 */
function emitTs(rec) {
  if (!ready()) return;
  rec.ts = now();
  emit(rec);
}

/** The first record of the spool, written on the first record of the run. */
function boot() {
  booted = true;
  try {
    fs.mkdirSync(SPOOL_DIR, { recursive: true });
  } catch (err) {
    on = false;
    process.emitWarning(`sensorium: recording stopped, cannot use ${SPOOL_DIR}: ${err}`);
    return;
  }
  spoolPath = path.join(SPOOL_DIR, `${process.pid}-${threadId}.jsonl`);
  const env = { ...process.env };
  buf.push(JSON.stringify({
    e: 'BOOT',
    wire: 1,
    pid: process.pid,
    ppid: process.ppid,
    threadId,
    isMainThread,
    argv: process.argv,
    cwd: process.cwd(),
    env,
    envHash: envHash(env),
    node: process.version,
    version: VERSION,
    tier: TIER,
    capabilities: { ...CAPABILITIES },
    invocation: INVOCATION,
    startTs: Date.now() / 1000,
    ts: now(),
  }));
  install();
}

/**
 * Every path by which records reach the disk. A container killed by `SIGKILL`
 * — vitest's teardown timeout — still loses its unflushed tail and its EXIT,
 * and no count of the loss is written, because the process cannot know one.
 */
function install() {
  setInterval(flush, FLUSH_MS).unref();
  process.on('exit', (code) => {
    emitTs({ e: 'EXIT', code: process.exitCode ?? code, endTs: Date.now() / 1000 });
    flush();
  });
  process.on('beforeExit', () => flush());
  for (const sig of SIGNALS) {
    /** @type {NodeJS.SignalsListener} */
    const handler = () => {
      flush();
      // A signalled container still says how it ended (R13): EXIT is the last
      // line, `code` null because none was chosen and `signal` naming what
      // ended it. Only an uncatchable SIGKILL leaves a spool without one.
      emitTs({ e: 'EXIT', code: null, signal: sig, endTs: Date.now() / 1000 });
      flush();
      // Then put the default disposition back and die of the signal we were
      // sent: the recorder does not decide whether the process survives one.
      process.removeListener(sig, handler);
      process.kill(process.pid, sig);
    };
    process.on(sig, handler);
  }
  process.on('unhandledRejection', (reason) => {
    emitTs({ e: 'UNHANDLED', x: exc(reason, 'rejection') });
    flush();
  });
}

// --- files, tests and suites -----------------------------------------------

/**
 * The per-module header: one FILE record, one id the file's calls carry.
 * @param {string} rel root-relative path
 * @param {string} abs absolute path
 * @param {[string, number, string][]} codes `[qualname, line, kind]` per site
 * @param {string} sha sha256 of the ORIGINAL source
 * @returns {number} the file id
 */
export function file(rel, abs, codes, sha) {
  if (!on) return 0;
  const id = nextFile++;
  emit({ e: 'FILE', id, rel, abs, codes, sha });
  return id;
}

/**
 * A test's argument list, read from the end: `rest` is `[...between, fn, flags]`
 * — the flags always last, the callback the one before it, and `between` the
 * options object vitest's `test(name, options, fn)` form allows (R8c). The
 * flags are the transform's own knowledge of the title and are consumed here;
 * everything else comes back in the order the source wrote it.
 * @param {unknown} title
 * @param {...unknown} rest
 * @returns {unknown[]} `[title, ...between, wrapped]`
 */
export function task(title, ...rest) {
  const fn = rest[rest.length - 2];
  const head = rest.slice(0, -1);
  if (!on || typeof fn !== 'function') return [title, ...head];
  const flags = Number(rest[rest.length - 1]) || 0;
  return [title, ...head.slice(0, -1), wrapTask(titleOf(title), fn, flags)];
}

/**
 * A suite's argument list: `[...between, fn]`, no flags — a suite is not named
 * by the harness, it only lends its title to the tasks registered inside it.
 * @param {unknown} title
 * @param {...unknown} rest
 * @returns {unknown[]} `[title, ...between, wrapped]`
 */
export function suite(title, ...rest) {
  const fn = rest[rest.length - 1];
  if (!on || typeof fn !== 'function') return [title, ...rest];
  return [title, ...rest.slice(0, -1), wrapSuite(titleOf(title), fn)];
}

/**
 * Register the harness's own name for the test now running. The vitest setup
 * file supplies `() => expect.getState().currentTestName ?? null`; under
 * `node --test` there is no provider and the lexical name is the name.
 * @param {unknown} fn
 * @returns {void}
 */
export function nameProvider(fn) {
  if (!on) return;
  provider = typeof fn === 'function' ? /** @type {() => unknown} */ (fn) : null;
}

/** @param {unknown} title @returns {string} */
const titleOf = (title) => (typeof title === 'string' ? title : UNNAMED);

/**
 * @param {string} title
 * @param {Function} fn
 * @param {number} flags bit 1: a plain string literal; bit 2: a `.each` chain
 * @returns {Function}
 */
function wrapTask(title, fn, flags) {
  const lexical = [...suiteStack.map((s) => s.title), title].join(' > ');
  // Activations are counted PER NAME, per CONTAINER — see `activations` above.
  // A harness that gave this activation a name of its own — `test.each`
  // expanding a template into a row's values — has already told them apart, and
  // numbering those would rename tests that never repeated.
  return /** @this {unknown} */ function sensoriumTask(/** @type {unknown[]} */ ...args) {
    const named = nameFor(title, lexical, flags);
    // The name came from the consumer — a title, or whatever the harness calls
    // this test — so it is capped like every other consumer string (R14). The
    // `#k` suffix is the recorder's own and is added after the cut, because two
    // names that were cut to the same text are the same name to a reader.
    const capped = cap(named.name);
    const k = (activations.get(capped.v) ?? 0) + 1;
    activations.set(capped.v, k);
    const name = k >= 2 ? `${capped.v}#${k}` : capped.v;
    /** @type {Task} */
    const t = { id: nextTask++, name, stack: [] };
    /** @type {Record_} */
    const rec = { e: 'TASK', id: t.id, name, basis: named.basis, conflict: named.conflict };
    if (capped.trunc) rec.name_trunc = true;
    emit(rec);
    // A task's records reach the disk when the task settles — however it
    // settles — whatever the harness does to this worker afterwards.
    try {
      // Every continuation of this callback — microtask, timer, jsdom timer,
      // emitter callback — resolves to this task, because the task is a
      // property of the async context and not of the call stack.
      const out = als.run(t, () => fn.apply(this, args));
      if (thenable(out)) return out.then(taskSettled, taskFailed);
      flush();
      return out;
    } catch (err) {
      return taskFailed(err);
    }
  };
}

/** @param {unknown} v @returns {unknown} */
function taskSettled(v) {
  flush();
  return v;
}

/** @param {unknown} err @returns {never} */
function taskFailed(err) {
  flush();
  throw err;
}

/**
 * The four branches of the naming rule (spec §4, D4).
 * @param {string} title
 * @param {string} lexical
 * @param {number} flags
 * @returns {Named}
 */
function nameFor(title, lexical, flags) {
  const provided = ask();
  if (typeof provided !== 'string') return { name: lexical, basis: 'title', conflict: false };
  // The cross-check is only possible where the transform saw a plain string
  // literal that is not a `.each` template. A `.concurrent` task's provider
  // name is uncheckable for a different reason, and the ledger says so.
  const checkable = (flags & 1) !== 0 && (flags & 2) === 0;
  if (checkable && !provided.endsWith(title)) {
    return { name: lexical, basis: 'title', conflict: true };
  }
  return { name: provided, basis: 'vitest', conflict: false };
}

/** @returns {unknown} the provider's name, or null when there is none to ask */
function ask() {
  if (!provider) return null;
  try {
    return provider();
  } catch {
    // `expect.getState()` outside a test throws; that is not this run's news.
    return null;
  }
}

/**
 * The `describe` title stands while its callback runs, so a task registered
 * inside it knows its lexical chain at REGISTRATION time.
 *
 * A callback that returns a promise keeps its title until the promise settles.
 * The stack is then a temporal approximation of the lexical chain, not the
 * chain itself: a test registered after an `await` inside an async `describe`
 * can see titles pushed by other suites that ran while this one was parked.
 * Where vitest's own name provider runs, that name is the authority; the
 * lexical name is the fallback, and this is one of the places it can be wrong.
 * @param {string} title
 * @param {Function} fn
 * @returns {Function}
 */
function wrapSuite(title, fn) {
  return /** @this {unknown} */ function sensoriumSuite(/** @type {unknown[]} */ ...args) {
    const entry = { title };
    const done = (/** @type {unknown} */ v) => {
      leave(entry);
      return v;
    };
    const failed = (/** @type {unknown} */ err) => {
      leave(entry);
      throw err;
    };
    suiteStack.push(entry);
    try {
      const out = fn.apply(this, args);
      return thenable(out) ? out.then(done, failed) : done(out);
    } catch (err) {
      return failed(err);
    }
  };
}

/** @param {{title: string}} entry @returns {void} */
function leave(entry) {
  const i = suiteStack.lastIndexOf(entry);
  if (i >= 0) suiteStack.splice(i, 1);
}

/** @param {any} v @returns {v is PromiseLike<unknown>} */
const thenable = (v) => v !== null && typeof v === 'object' && typeof v.then === 'function';

// --- frames ----------------------------------------------------------------

/** @param {Frame|null} f @returns {number|null} */
const taskId = (f) => (f && f.task ? f.task.id : null);

/** @param {Frame} f @returns {Frame[]} */
const stackOf = (f) => (f.task ? f.task.stack : rootStack);

/** @param {Frame} f @returns {void} */
function drop(f) {
  const stack = stackOf(f);
  const i = stack.lastIndexOf(f);
  if (i >= 0) stack.splice(i, 1);
}

/**
 * Enter an instrumented function: the parent is whatever frame is beneath this
 * one on the stack this one pushes onto. A continuation that runs when its
 * task's stack is empty — a timer callback — opens a parentless frame, and the
 * converter writes `caller: "untraced"` for it.
 * @param {number} fileId
 * @param {number} c index into the file's `codes`
 * @returns {Frame|null}
 */
export function call(fileId, c) {
  if (!on) return null;
  const t = als.getStore() ?? null;
  const stack = t ? t.stack : rootStack;
  const parent = stack.length > 0 ? stack[stack.length - 1] : null;
  /** @type {Frame} */
  const f = { id: nextFrame++, task: t, open: true, mark: null };
  stack.push(f);
  emitTs({ e: 'CALL', f: f.id, p: parent ? parent.id : null, file: fileId, c, t: t ? t.id : null });
  return f;
}

/**
 * Leave by returning. A frame that is already closed is left alone: a
 * generator's wrapper can see this after an UNWIND.
 * @template T
 * @param {Frame|null} f
 * @param {T} v
 * @returns {T} the value the source returns
 */
export function ret(f, v) {
  if (!on || !f || !f.open) return v;
  f.open = false;
  drop(f);
  emitTs({ e: 'RETURN', f: f.id, t: taskId(f), v: dbg(v) });
  return v;
}

/**
 * Close a generator frame its consumer abandoned (R40).
 *
 * `break` out of a `for…of`, a `return` from inside one, an explicit
 * `.return()`: every one of them resumes the generator body at its `yield`
 * with a RETURN completion, so the body's own `ret` never runs and its `catch`
 * never sees a throw. Without this the frame stayed open to the end of the
 * recording and read `suspended at end of recording` — a loss claim about a
 * generator somebody deliberately closed.
 *
 * The value is `unread`, not `undefined`: `.return(v)`'s value belongs to the
 * consumer and never reaches the body, so the body produced none, and
 * `undefined` would be a value this recorder invented. A frame `ret` or `thr`
 * has already closed is left exactly as they left it.
 * @param {Frame|null} f
 * @returns {void}
 */
export function gclose(f) {
  if (!on || !f || !f.open) return;
  f.open = false;
  drop(f);
  emitTs({ e: 'RETURN', f: f.id, t: taskId(f), v: { k: 'unread' } });
}

/**
 * Leave by throwing.
 * @param {Frame|null} f
 * @param {unknown} e
 * @returns {void}
 */
export function thr(f, e) {
  if (!on || !f || !f.open) return;
  f.open = false;
  drop(f);
  emitTs({ e: 'UNWIND', f: f.id, t: taskId(f), x: exc(e, 'throw') });
}

/**
 * Park: the frame comes OFF its stack while it waits, which is what keeps a
 * fan-out's siblings from nesting under one another. A frame that has already
 * closed neither parks nor is recorded — it is not on a stack to leave.
 * @template T
 * @param {Frame|null} f
 * @param {T} x the awaited or yielded value
 * @param {number} kind 0 for `await`, 1 for `yield`
 * @returns {T}
 */
export function y(f, x, kind) {
  if (!on || !f || !f.open) return x;
  emitTs({ e: 'YIELD', f: f.id, t: taskId(f), k: kind === 1 ? 'yield' : 'await' });
  drop(f);
  return x;
}

/**
 * Resume: the frame goes back on its stack — unless it has closed, which would
 * put a finished frame back on a live stack and make it the parent of whatever
 * ran next.
 * @template T
 * @param {Frame|null} f
 * @param {T} v the value the suspension produced
 * @returns {T}
 */
export function r(f, v) {
  if (!on || !f || !f.open) return v;
  stackOf(f).push(f);
  emitTs({ e: 'RESUME', f: f.id, t: taskId(f) });
  return v;
}

// --- throw flow ------------------------------------------------------------

/**
 * A `throw` statement, and nothing else.
 * @template T
 * @param {Frame|null} f the enclosing frame, or null outside every one
 * @param {T} e
 * @param {number} line
 * @returns {T} the value the source throws
 */
export function raise(f, e, line) {
  if (!on) return e;
  const x = exc(e, 'throw');
  emitTs({ e: 'RAISE', f: f ? f.id : null, t: taskOf(f), x, l: line, how: 'throw' });
  // The throw is now in flight through this frame: a `finally` beneath it that
  // completes discards THIS value, and the mark is how it learns which.
  if (f && f.open) f.mark = x;
  return e;
}

/**
 * A `catch` clause, or the empty-block sink that has none. Whatever the clause
 * then does with the value, the flight this frame was carrying is over: the
 * mark is cleared, so a `finally` beneath a `catch` claims nothing.
 * @param {Frame|null} f
 * @param {unknown} e
 * @param {number} line
 * @param {string} how `catch`, `catch_escaped` or `sink_empty_catch`
 * @returns {void}
 */
export function handled(f, e, line, how) {
  if (!on) return;
  record(f, e, line, how, 'throw');
  if (f) f.mark = null;
}

/**
 * A throw is in flight through `f` and this runtime is holding the value.
 *
 * The transform's synthetic clause calls it — `catch(__sfe){mark(__sf,__sfe);
 * throw __sfe}` before a completing `finally` — which is what lets a library's
 * throw and an awaited rejection be marked as well as a `throw` statement (P1).
 * The whole `exc` is kept and not just its serial: the contract requires
 * `type` on every one, and here the value is in hand, so nothing goes unread.
 * @param {Frame|null} f
 * @param {unknown} e
 * @returns {void}
 */
export function mark(f, e) {
  if (on && f && f.open) f.mark = exc(e, 'throw');
}

/**
 * A `finally` block that completes — `return`, `break` or `continue` at closure
 * depth 0 — discards whatever was travelling through the frame. It records a
 * HANDLED only when something WAS: a `finally` reached on the normal path, or
 * one discarding a throw this recorder never saw raised, holds no mark and
 * writes nothing (a declared blind spot, §2.3). The mark is one slot, so the
 * first sink to read it is the one that reports the discard.
 * @param {Frame|null} f
 * @param {number} line
 * @returns {void}
 */
export function handledFinally(f, line) {
  if (!on || !f || !f.open || f.mark === null) return;
  emitTs({
    e: 'HANDLED',
    f: f.id,
    t: taskOf(f),
    x: f.mark,
    l: line,
    how: 'sink_finally_return',
  });
  f.mark = null;
}

/**
 * A rejection handler — `p.catch(<arg>)`, `p.then(x, <arg>)` — wrapped so the
 * reason it is given is recorded before it runs. `how` is the transform's
 * verdict about the handler's SHAPE, decided at splice time and written down
 * here unexamined (§2.2).
 *
 * What the wrapper must not change is what the chain continues with: the
 * original is called with the same `this` and the same reason, and its result
 * is returned untouched. A handler that is not callable is a shape the
 * transform does not emit; it is handed straight back rather than wrapped,
 * because breaking the program to record it would be the larger harm.
 * @param {Frame|null} f
 * @param {number} line
 * @param {string} how one of §2.5's callback words
 * @param {Function} fn
 * @returns {Function}
 */
export function catchCb(f, line, how, fn) {
  if (!on || typeof fn !== 'function') return fn;
  return /** @this {unknown} */ function sensoriumCatchCb(/** @type {unknown} */ reason) {
    record(f, reason, line, how, 'rejection');
    return fn.call(this, reason);
  };
}

/**
 * @param {Frame|null} f
 * @param {unknown} e
 * @param {number} line
 * @param {string} how
 * @param {'throw'|'rejection'} kind
 */
function record(f, e, line, how, kind) {
  emitTs({ e: 'HANDLED', f: f ? f.id : null, t: taskOf(f), x: exc(e, kind), l: line, how });
}

/**
 * The task a throw-flow record belongs to. A record that names a FRAME belongs
 * to that frame's task, whichever async context the throw was reported from —
 * the same source `ret`, `thr`, `y` and `r` read, so one frame's rows cannot
 * disagree about their task. Only a frameless record falls back to the async
 * context, which is all there is to ask.
 * @param {Frame|null} f
 * @returns {number|null}
 */
function taskOf(f) {
  if (f) return taskId(f);
  const t = als.getStore();
  return t ? t.id : null;
}

// --- what the harness wiring records ---------------------------------------

/**
 * The start of one test file, from the setup file that runs before it.
 * @param {string} file_ root-relative path
 * @param {string|null} environment vitest's environment name
 * @returns {void}
 */
export function fileStart(file_, environment) {
  if (!on) return;
  emit({ e: 'FILE_START', path: file_, environment });
}

/**
 * One test the harness itself saw, whatever the transform made of it: the
 * count that catches tests registered through a shape we did not wrap.
 *
 * A non-string is not a test. The setup file passes
 * `expect.getState().currentTestName ?? null`, so a `beforeEach` that runs
 * where the harness has no current test hands this a null; `String(null)` made
 * that a test called `null` and inflated `tests_seen`, which is the one number
 * whose whole job is to name the shortfall against tasks.
 * @param {unknown} name
 * @returns {void}
 */
export function seen(name) {
  if (!on || typeof name !== 'string') return;
  // Cut exactly as a TASK name is (R14a): the converter compares the two, and
  // two names cut by different rules would not compare.
  const capped = cap(name);
  /** @type {Record_} */
  const rec = { e: 'SEEN', name: capped.v };
  if (capped.trunc) rec.name_trunc = true;
  emit(rec);
}
