// THROWAWAY spike runtime (S5 rung 0). Not the recorder; an instrument that
// answers the pre-registered endpoints in docs/superpowers/spikes/
// 2026-09-08-typescript-mechanics-spike.md. One spool per (pid, threadId).
import { AsyncLocalStorage } from 'node:async_hooks';
import { threadId, isMainThread } from 'node:worker_threads';
import fs from 'node:fs';
import path from 'node:path';
import util from 'node:util';
import crypto from 'node:crypto';

const TIER = process.env.SENSORIUM_TIER || 'off';
const SPOOL_DIR = process.env.SENSORIUM_SPOOL || '';
const ON = TIER === 'call' && SPOOL_DIR !== '';
const CAP = 200;

const als = new AsyncLocalStorage();
let nextFrame = 1;
let nextTask = 1;
let nextSerial = 1;
let nextFile = 1;
const serials = new WeakMap();
const rootStack = []; // frames running in no task
const buf = [];
let spoolPath = null;
let booted = false;

function envHash() {
  const lines = Object.keys(process.env).sort().map((k) => `${k}=${process.env[k]}`).join('\n');
  return crypto.createHash('sha256').update(lines).digest('hex').slice(0, 16);
}

export function flush() {
  if (!ON || buf.length === 0 || !spoolPath) return;
  fs.appendFileSync(spoolPath, buf.join('\n') + '\n');
  buf.length = 0;
}

function emit(rec) {
  if (!ON) return;
  if (!booted) boot();
  rec.ts = Number(process.hrtime.bigint());
  buf.push(JSON.stringify(rec));
  if (buf.length >= 256) flush();
}

function boot() {
  booted = true;
  fs.mkdirSync(SPOOL_DIR, { recursive: true });
  spoolPath = path.join(SPOOL_DIR, `${process.pid}-${threadId}.jsonl`);
  buf.push(JSON.stringify({
    e: 'BOOT', pid: process.pid, ppid: process.ppid, threadId, isMainThread,
    argv: process.argv, cwd: process.cwd(), envHash: envHash(),
    startTs: Date.now() / 1000, tier: TIER, node: process.version,
    vitestWorker: process.env.VITEST_WORKER_ID || null, vitestPool: process.env.VITEST_POOL_ID || null,
    ts: Number(process.hrtime.bigint()),
  }));
  // vitest may kill a worker without an 'exit' turn, so the spool is flushed
  // eagerly: after every task, on a timer, and on every terminal signal we can see.
  const timer = setInterval(flush, 100);
  if (timer.unref) timer.unref();
  const exitRec = (code) => {
    buf.push(JSON.stringify({ e: 'EXIT', code, endTs: Date.now() / 1000, ts: Number(process.hrtime.bigint()) }));
    flush();
  };
  process.on('exit', exitRec);
  process.on('beforeExit', () => flush());
  for (const sig of ['SIGTERM', 'SIGINT', 'SIGHUP']) {
    process.on(sig, () => { flush(); process.exit(0); });
  }
  process.on('unhandledRejection', (reason) => {
    emit({ e: 'RAISE', f: null, t: null, x: fmtExc(reason), basis: 'unhandledRejection' });
  });
}

function fmtExc(e) {
  let serial;
  if (e !== null && (typeof e === 'object' || typeof e === 'function')) {
    serial = serials.get(e);
    if (serial === undefined) { serial = nextSerial++; serials.set(e, serial); }
  } else {
    serial = nextSerial++;
  }
  const type = e && typeof e === 'object' && e.constructor ? e.constructor.name : typeof e;
  const msg = e && typeof e === 'object' && 'message' in e ? String(e.message) : String(e);
  return { type, msg, serial };
}

function dbg(v) {
  if (v === undefined) return { k: 'dbg', v: 'undefined', trunc: false };
  let s;
  try {
    s = util.inspect(v, { depth: 2, breakLength: Infinity, maxArrayLength: 8, maxStringLength: 100, compact: true });
  } catch (err) {
    return { k: 'unread' };
  }
  const trunc = s.length > CAP;
  if (trunc) s = s.slice(0, CAP);
  return { k: 'dbg', v: s, trunc };
}

function curTask() { return als.getStore() || null; }
function stackOf(task) { return task ? task.stack : rootStack; }

// ---- API the transform emits calls to ----------------------------------

export function file(relPath, codes, sha) {
  const id = nextFile++;
  emit({ e: 'FILE', id, path: relPath, codes, sha });
  return id;
}

export function task(name, fn) {
  if (!ON) return fn;
  return function sensoriumTask(...args) {
    const t = { id: nextTask++, name, stack: [] };
    emit({ e: 'TASK', id: t.id, name });
    const out = als.run(t, () => fn.apply(this, args));
    if (out && typeof out.then === 'function') {
      return out.then((v) => { flush(); return v; }, (err) => { flush(); throw err; });
    }
    flush();
    return out;
  };
}

export function call(fileId, codeIdx) {
  if (!ON) return null;
  const t = curTask();
  const st = stackOf(t);
  const parent = st.length ? st[st.length - 1] : null;
  const f = { id: nextFrame++, open: true, task: t };
  st.push(f);
  emit({ e: 'CALL', f: f.id, p: parent ? parent.id : null, file: fileId, c: codeIdx, t: t ? t.id : null });
  return f;
}

function pop(f) {
  const st = stackOf(f.task);
  const i = st.lastIndexOf(f);
  if (i >= 0) st.splice(i, 1);
}

export function ret(f, v) {
  if (!ON || !f || !f.open) return v;
  f.open = false;
  pop(f);
  emit({ e: 'RETURN', f: f.id, t: f.task ? f.task.id : null, v: dbg(v) });
  return v;
}

export function thr(f, e) {
  if (!ON || !f || !f.open) return;
  f.open = false;
  pop(f);
  emit({ e: 'UNWIND', f: f.id, t: f.task ? f.task.id : null, x: fmtExc(e) });
}

// `await X` becomes `r(f, await y(f, X))`: YIELD before parking, RESUME after.
export function y(f, x) {
  if (!ON || !f) return x;
  emit({ e: 'YIELD', f: f.id, t: f.task ? f.task.id : null });
  pop(f);
  return x;
}

export function r(f, v) {
  if (!ON || !f) return v;
  stackOf(f.task).push(f);
  emit({ e: 'RESUME', f: f.id, t: f.task ? f.task.id : null });
  return v;
}

export function raise(f, e, line) {
  if (!ON) return e;
  const t = curTask();
  emit({ e: 'RAISE', f: f ? f.id : null, t: t ? t.id : null, x: fmtExc(e), l: line });
  return e;
}

export function handled(f, e, line, sink) {
  if (!ON) return;
  const t = curTask();
  const rec = { e: 'HANDLED', f: f ? f.id : null, t: t ? t.id : null, x: fmtExc(e), l: line };
  if (sink) rec.sink = sink;
  emit(rec);
}

export function emptyCatch(f, line, fn) {
  if (!ON) return fn;
  return function sensoriumEmptyCatch(reason) {
    handled(f, reason, line, 'empty_catch_callback');
    return fn(reason);
  };
}
