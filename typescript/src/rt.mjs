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

import { dbg, exc } from './dbg.mjs';
import { VERSION } from './index.mjs';

/** @typedef {{id: number, name: string, stack: Frame[]}} Task */
/** @typedef {{id: number, task: Task|null, open: boolean}} Frame */
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
 * @param {Record_} rec
 * @returns {void}
 */
function emit(rec) {
  if (!on) return;
  if (!booted) {
    boot();
    if (!on) return;
  }
  buf.push(JSON.stringify(rec));
  if (buf.length >= BUFFERED) flush();
}

/**
 * The same, for the record kinds that carry a timestamp (`ts` last, always).
 * @param {Record_} rec
 * @returns {void}
 */
function emitTs(rec) {
  if (!on) return;
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
      // Put the default disposition back and die of the signal we were sent:
      // the recorder does not decide whether the process survives one.
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
  let activations = 0;
  return /** @this {unknown} */ function sensoriumTask(/** @type {unknown[]} */ ...args) {
    activations += 1;
    const named = nameFor(title, lexical, flags);
    const name = activations >= 2 ? `${named.name}#${activations}` : named.name;
    /** @type {Task} */
    const t = { id: nextTask++, name, stack: [] };
    emit({ e: 'TASK', id: t.id, name, basis: named.basis, conflict: named.conflict });
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
  const f = { id: nextFrame++, task: t, open: true };
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
 * fan-out's siblings from nesting under one another.
 * @template T
 * @param {Frame|null} f
 * @param {T} x the awaited or yielded value
 * @param {number} kind 0 for `await`, 1 for `yield`
 * @returns {T}
 */
export function y(f, x, kind) {
  if (!on || !f) return x;
  emitTs({ e: 'YIELD', f: f.id, t: taskId(f), k: kind === 1 ? 'yield' : 'await' });
  drop(f);
  return x;
}

/**
 * Resume: the frame goes back on its stack.
 * @template T
 * @param {Frame|null} f
 * @param {T} v the value the suspension produced
 * @returns {T}
 */
export function r(f, v) {
  if (!on || !f) return v;
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
  emitTs({
    e: 'RAISE',
    f: f ? f.id : null,
    t: current(),
    x: exc(e, 'throw'),
    l: line,
    how: 'throw',
  });
  return e;
}

/**
 * A `catch` clause, or the empty-block sink that has none.
 * @param {Frame|null} f
 * @param {unknown} e
 * @param {number} line
 * @param {string} how `catch` or `sink_empty_catch`
 * @returns {void}
 */
export function handled(f, e, line, how) {
  if (!on) return;
  record(f, e, line, how, 'throw');
}

/**
 * `.catch(() => {})` — a callback that swallows a rejection. The original is
 * called with the reason it was given and its result is returned: wrapping a
 * sink must not change what the sink does.
 * @param {Frame|null} f
 * @param {number} line
 * @param {Function} fn
 * @returns {Function}
 */
export function emptyCatch(f, line, fn) {
  if (!on) return fn;
  return /** @this {unknown} */ function sensoriumEmptyCatch(/** @type {unknown} */ reason) {
    record(f, reason, line, 'sink_empty_catch_callback', 'rejection');
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
  emitTs({ e: 'HANDLED', f: f ? f.id : null, t: current(), x: exc(e, kind), l: line, how });
}

/** @returns {number|null} the task this record belongs to, frame or no frame */
function current() {
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
 * @param {string} name
 * @returns {void}
 */
export function seen(name) {
  if (!on) return;
  emit({ e: 'SEEN', name });
}
