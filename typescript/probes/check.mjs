// THIS is the probes' gate, not the harness's exit status: the `probe` scripts
// run the harness and this checker with `;` and not `&&` on purpose, because two
// probes make `vitest run` red by design (an unhandled rejection, and a test
// that never settles) and a run that stopped there would never be checked.
//
// It reads every spool the recorder wrote and holds it to the rows the spike's
// findings §1.1-§1.3 pinned before this code existed, plus the rung-1 rulings the
// probe files were written for. Nothing here is eyeballed: a probe passes when
// its rows are asserted, and the JSON on stdout is the evidence.
//
//   node check.mjs <vitest|nodetest> <spool dir> <manifest dir>
//
// The manifest directory is REQUIRED in both modes: it carries the plugin's
// tally under vitest and the per-child tallies under `node --test` (including
// the one belonging to the child that recorded nothing), and a checker that let
// it be omitted would let those checks be skipped by leaving an argument off.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

/** The last `.` segment of a qualname: `viaEmitter.handler` is `handler`. */
const last = (/** @type {string} */ q) => q.split('.').pop() ?? q;

/** Values compare with whitespace removed: `[ 10, 20 ]` is `[10,20]` (§3, E3). */
const squash = (/** @type {string} */ s) => s.replace(/\s+/g, '');

/** The four scenarios and the negative control, verbatim from findings §1.1. */
const S1_ROWS = [
  ['CALL', 'a'], ['CALL', 'b'], ['CALL', 'c'],
  ['YIELD', 'c'], ['YIELD', 'b'], ['YIELD', 'a'],
  ['RESUME', 'c'], ['RETURN', 'c', '2'],
  ['RESUME', 'b'], ['RETURN', 'b', '3'],
  ['RESUME', 'a'], ['RETURN', 'a', '4'],
];
const S2_HEAD = [
  ['CALL', 'fanout'], ['CALL', 'p'], ['YIELD', 'p'],
  ['CALL', 'p'], ['YIELD', 'p'], ['YIELD', 'fanout'],
];
const S2_TAIL = [['RESUME', 'fanout'], ['RETURN', 'fanout', '[10,20]']];
const pair = (/** @type {string} */ x, /** @type {string} */ y) =>
  [['RESUME', 'p'], ['RETURN', 'p', x], ['RESUME', 'p'], ['RETURN', 'p', y]];

const SCENARIOS = [
  { id: 'S1', names: ['a', 'b', 'c'], alts: [S1_ROWS] },
  {
    id: 'S2',
    names: ['fanout', 'p'],
    // The two timers have equal delay, so the spec orders neither pair.
    alts: [
      [...S2_HEAD, ...pair('10', '20'), ...S2_TAIL],
      [...S2_HEAD, ...pair('20', '10'), ...S2_TAIL],
    ],
  },
  {
    id: 'S3',
    names: ['viaTimer', 'work'],
    alts: [[
      ['CALL', 'viaTimer'], ['YIELD', 'viaTimer'],
      ['CALL', 'work'], ['RETURN', 'work', '7'],
      ['RESUME', 'viaTimer'], ['RETURN', 'viaTimer', '7'],
    ]],
  },
  {
    id: 'S4',
    names: ['viaEmitter', 'handler'],
    alts: [[
      ['CALL', 'viaEmitter'], ['CALL', 'handler'], ['RETURN', 'handler'],
      ['YIELD', 'viaEmitter'], ['CALL', 'handler'], ['RETURN', 'handler'],
      ['RESUME', 'viaEmitter'], ['RETURN', 'viaEmitter', '2'],
    ]],
  },
];

/**
 * What §1.2 says each swallow shape's exception looks like. Shapes 1-5 are
 * rung 1's; 6-12 are rung 2's, one per `how` word the escape rule, the
 * rejection-callback wrapper and the `finally` sink can now write. A shape
 * whose reason was never THROWN — a `Promise.reject`, whose handler records a
 * HANDLED with no RAISE — raises nothing, and the empty list says so.
 * @type {Record<string, {raises: {type: string, msg: string}[], oneSerial?: boolean}>}
 */
const SWALLOW_EXC = {
  shape1: { raises: [{ type: 'Error', msg: 'e1' }] },
  shape2: { raises: [] },
  shape4: { raises: [{ type: 'string', msg: 'not-an-error' }] },
  shape5: { raises: [{ type: 'Error', msg: 'e5' }, { type: 'Error', msg: 'e5' }], oneSerial: true },
  shape6: { raises: [{ type: 'Error', msg: 'e6' }] },
  shape7: { raises: [{ type: 'Error', msg: 'e7' }] },
  shape8: { raises: [] },
  shape9: { raises: [] },
  shape10: { raises: [] },
  shape11: { raises: [] },
  shape12: { raises: [{ type: 'Error', msg: 'e12' }] },
};

const EACH_NAMES = ['adds 1 + 2 = 3', 'adds 2 + 3 = 5', 'adds 4 + 5 = 9'];

/**
 * The probe files a `node --test` run must have recorded, by root-relative
 * path -- one per extension the hook can be handed. `nodetest/ext.probe.test.cjs`
 * is NOT here: it is excluded, so it declares no file and writes no spool, and
 * what answers for it is its tally (`ext:cjs:tally`).
 */
const NODETEST_PROBES = [
  'nodetest/async.probe.test.ts', 'nodetest/ext.probe.test.mts',
  'nodetest/ext.probe.test.mjs',
];

/** The probe files a full vitest run must have recorded, by root-relative path. */
const VITEST_PROBES = [
  'src/async.probe.test.ts', 'src/async.jsdom.probe.test.ts', 'src/sites.probe.test.ts',
  'src/swallow.probe.test.ts', 'src/swallow3.probe.test.ts', 'src/escape.probe.test.ts',
  'src/each.probe.test.ts', 'src/focus.probe.test.ts',
  'src/concurrent.probe.test.ts', 'src/never_settles.probe.test.ts',
  'src/describe_chain.probe.test.ts', 'src/timer_parentless.probe.test.ts',
];

/** The focus probe, whose two readings `checkFocus` tells apart. */
const FOCUS_PROBE = 'src/focus.probe.test.ts';

// --- reading ---------------------------------------------------------------

/**
 * @param {string} dir
 * @returns {{name: string, records: any[]}[]}
 */
function readSpools(dir) {
  const out = [];
  for (const name of fs.readdirSync(dir).sort()) {
    if (!name.endsWith('.jsonl')) continue;
    const text = fs.readFileSync(path.join(dir, name), 'utf8');
    const records = text.split('\n').filter((line) => line !== '').map((line, i) => {
      try {
        return JSON.parse(line);
      } catch (err) {
        throw new Error(`${name}: line ${i + 1} is not JSON: ${err}`);
      }
    });
    out.push({ name, records });
  }
  return out;
}

/**
 * One spool, indexed: the files it declared, the tasks it opened, the name every
 * frame carries, and the causal rows in the order they were written.
 * @param {{name: string, records: any[]}} spool
 */
function index(spool) {
  const files = new Map();
  const tasks = new Map();
  const frames = new Map();
  const rows = [];
  for (const r of spool.records) {
    if (r.e === 'FILE') files.set(r.id, r);
    else if (r.e === 'TASK') tasks.set(r.id, r);
    else if (r.e === 'CALL') {
      const code = files.get(r.file)?.codes?.[r.c];
      const name = code ? last(code[0]) : '<unknown>';
      frames.set(r.f, { name, line: code ? code[1] : null });
      rows.push({ kind: 'CALL', name, task: r.t, rec: r });
    } else if (['RETURN', 'UNWIND', 'YIELD', 'RESUME'].includes(r.e)) {
      rows.push({ kind: r.e, name: frames.get(r.f)?.name ?? '<unknown>', task: r.t, rec: r });
    }
  }
  const probe = [...files.values()].find((f) => /\.probe\.test\.[cm]?[jt]sx?$/.test(f.rel));
  return { ...spool, files, tasks, frames, rows, probe: probe ? probe.rel : null };
}

// --- assertions ------------------------------------------------------------

class Checker {
  constructor() {
    /** @type {{id: string, ok: boolean, detail?: unknown}[]} */
    this.checks = [];
    /** @type {Record<string, unknown>} */
    this.report = {};
  }

  /**
   * @param {string} id
   * @param {boolean} ok
   * @param {unknown} [detail] shown always, so a pass is as legible as a failure
   */
  check(id, ok, detail) {
    this.checks.push(detail === undefined ? { id, ok } : { id, ok, detail });
  }

  /** @param {string} id @param {unknown} got @param {unknown} want */
  equal(id, got, want) {
    const ok = JSON.stringify(got) === JSON.stringify(want);
    this.check(id, ok, ok ? got : { got, want });
  }

  get failures() {
    return this.checks.filter((c) => !c.ok);
  }
}

/**
 * Read `// <TAG> …` markers out of a probe's source. A marker's expectation is
 * always the NEXT line, so moving the code moves the expectation with it.
 * @param {string} file
 * @param {string} tag
 * @returns {{args: string[], line: number}[]}
 */
function markers(file, tag) {
  const out = [];
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  for (let i = 0; i < lines.length; i += 1) {
    const m = lines[i].match(new RegExp(`^\\s*//\\s+${tag}\\s+(.+?)\\s*$`));
    if (m) out.push({ args: m[1].split(/\s+/), line: i + 2 });
  }
  return out;
}

/**
 * @param {{kind: string, name: string, rec: any}[]} rows
 * @returns {(string|null)[][]} rows as `[kind, name]` or `[kind, name, value]`
 */
function shape(rows) {
  return rows.map((r) => {
    if (r.kind !== 'RETURN') return [r.kind, r.name];
    const v = r.rec.v;
    return [r.kind, r.name, v && v.k === 'dbg' ? squash(v.v) : null];
  });
}

/**
 * Compare a scenario's rows against its alternatives, ignoring the value of a
 * RETURN the table gave no value for (§3, E3: the checker defect that read one).
 * @param {(string|null)[][]} got
 * @param {string[][]} want
 * @returns {boolean}
 */
function matches(got, want) {
  if (got.length !== want.length) return false;
  return want.every((row, i) =>
    row[0] === got[i][0] && row[1] === got[i][1] && (row.length < 3 || row[2] === got[i][2]));
}

// --- the probes ------------------------------------------------------------

/**
 * E3 in one spool: the four scenarios, then the negative control.
 * @param {Checker} k
 * @param {ReturnType<typeof index>} s
 * @param {string} label
 * @param {string} basis the naming basis this harness produces
 */
function checkAsync(k, s, label, basis) {
  const taskOf = (/** @type {string} */ id) =>
    [...s.tasks.values()].find((t) => t.name.startsWith(`${id} `)) ?? null;
  for (const sc of SCENARIOS) {
    const task = taskOf(sc.id);
    if (!task) {
      k.check(`${label}:${sc.id}`, false, `no task named ${sc.id}`);
      continue;
    }
    const got = shape(s.rows.filter((r) => r.task === task.id && sc.names.includes(r.name)));
    k.check(`${label}:${sc.id}`, sc.alts.some((alt) => matches(got, alt)),
      { task: task.name, basis: task.basis, rows: got });
    k.check(`${label}:${sc.id}:basis`, task.basis === basis, task.basis);
  }
  checkControl(k, s, label, taskOf('T1'), taskOf('T2'));
}

/**
 * The negative control: T2's rows are T2's, and not one of S1's names carries
 * T1 after T1 has returned.
 * @param {Checker} k
 * @param {ReturnType<typeof index>} s
 * @param {string} label
 * @param {any} t1
 * @param {any} t2
 */
function checkControl(k, s, label, t1, t2) {
  if (!t1 || !t2 || t1.id === t2.id) {
    k.check(`${label}:control`, false, { t1: t1?.id ?? null, t2: t2?.id ?? null });
    return;
  }
  const chain = s.rows.filter((r) => ['a', 'b', 'c'].includes(r.name));
  const end = chain.findIndex((r) => r.kind === 'RETURN' && r.name === 'a' && r.task === t1.id);
  const after = end === -1 ? [] : chain.slice(end + 1);
  k.check(`${label}:control:leak`, end !== -1 && after.every((r) => r.task === t2.id),
    { rows_after_T1: after.length, carrying_T1: after.filter((r) => r.task === t1.id).length });
  k.check(`${label}:control:T2`, matches(shape(after.filter((r) => r.task === t2.id)), S1_ROWS));
}

/**
 * E4: every `// SITE` marker's function starts on the line under it.
 * @param {Checker} k
 * @param {ReturnType<typeof index>} s
 */
function checkSites(k, s) {
  const sources = ['src/sites.probe.test.ts', 'src/sites.component.tsx'];
  const want = sources.flatMap((rel) =>
    markers(path.join(HERE, rel), 'SITE').map((m) => ({ name: m.args[0], line: m.line })));
  const codes = [...s.files.values()].flatMap((f) =>
    /** @type {[string, number, string][]} */ (f.codes).map((c) => [last(c[0]), c[1]]));
  const wrong = [];
  for (const site of want) {
    const hits = codes.filter(([name]) => name === site.name).map(([, line]) => line);
    if (hits.length !== 1 || hits[0] !== site.line) wrong.push({ ...site, got: hits });
  }
  k.check('sites:count', want.length === 20, want.length);
  k.check('sites:lines', wrong.length === 0, { on_line: want.length - wrong.length, wrong });
}

/**
 * E8's swallow shapes — 1, 2 and 4-12, every one in `SWALLOW_EXC`: the marked
 * lines, the `how` each was recorded with, and what the exception itself looks
 * like.
 * @param {Checker} k
 * @param {ReturnType<typeof index>} s
 */
function checkSwallow(k, s) {
  const marks = markers(path.join(HERE, 'src/swallow.probe.test.ts'), 'SWALLOW');
  for (const [id, exc] of Object.entries(SWALLOW_EXC)) {
    const task = [...s.tasks.values()].find((t) => t.name.startsWith(`${id} `));
    const want = marks.filter((m) => m.args[0] === id)
      .map((m) => [m.args[1] === 'raise' ? 'RAISE' : 'HANDLED', m.args[2], m.line]);
    const got = s.records
      .filter((r) => (r.e === 'RAISE' || r.e === 'HANDLED') && task && r.t === task.id)
      .map((r) => [r.e, r.how, r.l]);
    k.equal(`swallow:${id}:rows`, sorted(got), sorted(want));
    const raises = s.records.filter((r) => r.e === 'RAISE' && task && r.t === task.id);
    k.equal(`swallow:${id}:exc`, raises.map((r) => ({ type: r.x.type, msg: r.x.msg })), exc.raises);
    if (exc.oneSerial) {
      k.check(`swallow:${id}:serial`, new Set(raises.map((r) => r.x.serial)).size === 1,
        raises.map((r) => r.x.serial));
    }
  }
}

/** @param {unknown[][]} rows @returns {unknown[][]} */
const sorted = (rows) => [...rows].sort((x, y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));

/**
 * E8's escape specimens: every `// ESCAPE <id> <how>` marker's clause recorded
 * its HANDLED on the marked line, carrying the word the marker names. The
 * clause's line is the record's line, so the marker is the only place the
 * expectation is written down — and the `how` is what the reader turns into a
 * SWALLOWED, which is why the rule is checked on the WIRE here and not only in
 * the unit tests that ask it directly.
 * @param {Checker} k
 * @param {ReturnType<typeof index>} s
 */
function checkEscape(k, s) {
  const want = markers(path.join(HERE, 'src/escape.probe.test.ts'), 'ESCAPE')
    .map((m) => ({ id: m.args[0], how: m.args[1], line: m.line }));
  const got = new Map(s.records.filter((r) => r.e === 'HANDLED').map((r) => [r.l, r.how]));
  const wrong = want
    .filter((w) => got.get(w.line) !== w.how)
    .map((w) => ({ ...w, got: got.get(w.line) ?? null }));
  k.check('escape:count', want.length === 14, want.length);
  k.check('escape:how', wrong.length === 0, { as_marked: want.length - wrong.length, wrong });
}

/**
 * Shape 3: an UNHANDLED written by the process listener, outside every frame and
 * every task — the record carries no `f` and no `t`, and it must not invent one.
 * @param {Checker} k
 * @param {ReturnType<typeof index>} s
 */
function checkUnhandled(k, s) {
  const got = s.records.filter((r) => r.e === 'UNHANDLED');
  k.check('swallow:shape3:count', got.length === 1, got.length);
  if (got.length !== 1) return;
  k.equal('swallow:shape3:keys', Object.keys(got[0]).sort(), ['e', 'ts', 'x']);
  k.equal('swallow:shape3:exc',
    { kind: got[0].x.kind, type: got[0].x.type, msg: got[0].x.msg },
    { kind: 'rejection', type: 'Error', msg: 'e3' });
}

/** @param {Checker} k @param {ReturnType<typeof index>} s */
function checkEach(k, s) {
  const tasks = [...s.tasks.values()];
  k.equal('each:names', tasks.map((t) => t.name), EACH_NAMES);
  k.equal('each:basis', tasks.map((t) => [t.basis, t.conflict]), EACH_NAMES.map(() => ['vitest', false]));
}

/** @param {Checker} k @param {ReturnType<typeof index>} s */
function checkDescribeChain(k, s) {
  k.equal('describe_chain:name', [...s.tasks.values()].map((t) => t.name), ['outer > inner > leaf']);
}

/**
 * A frame that parks and never comes back: a YIELD, no RETURN, no UNWIND — and
 * the container still ends with an EXIT.
 * @param {Checker} k @param {ReturnType<typeof index>} s
 */
function checkNeverSettles(k, s) {
  const rows = s.rows.filter((r) => r.name === 'parks');
  k.equal('never_settles:rows', rows.map((r) => r.kind), ['CALL', 'YIELD']);
  k.check('never_settles:exit', s.records[s.records.length - 1]?.e === 'EXIT',
    s.records[s.records.length - 1]?.e);
}

/** @param {Checker} k @param {ReturnType<typeof index>} s */
function checkTimerParentless(k, s) {
  const calls = s.records.filter((r) => r.e === 'CALL')
    .filter((r) => last(s.files.get(r.file).codes[r.c][0]) === 'onTimer');
  const task = [...s.tasks.values()][0];
  k.check('timer_parentless:count', calls.length === 1, calls.length);
  if (calls.length !== 1) return;
  k.equal('timer_parentless:frame', { p: calls[0].p, t: calls[0].t }, { p: null, t: task.id });
}

/**
 * Reported, never gated: the concurrent naming hazard, counted.
 * @param {Checker} k @param {ReturnType<typeof index>} s
 */
function checkConcurrent(k, s) {
  const tasks = [...s.tasks.values()];
  k.report.concurrent = {
    tasks: tasks.map((t) => ({ name: t.name, basis: t.basis, conflict: t.conflict })),
    conflicts: tasks.filter((t) => t.conflict).length,
  };
  k.check('concurrent:tasks', tasks.length === 2, tasks.length);
}

/**
 * What every spool owes, whatever it recorded: one BOOT, first; an EXIT, last;
 * and under vitest exactly one FILE_START naming the environment it ran in.
 * @param {Checker} k @param {ReturnType<typeof index>} s @param {boolean} wantFileStart
 */
function checkContainer(k, s, wantFileStart) {
  const boots = s.records.filter((r) => r.e === 'BOOT');
  const label = s.probe ?? s.name;
  k.check(`container:${label}:one_boot`, boots.length === 1 && s.records[0]?.e === 'BOOT', boots.length);
  k.check(`container:${label}:exit`, s.records[s.records.length - 1]?.e === 'EXIT');
  const starts = s.records.filter((r) => r.e === 'FILE_START');
  if (!wantFileStart) {
    k.check(`container:${label}:no_setup`, starts.length === 0, starts.length);
    return;
  }
  k.check(`container:${label}:file_start`,
    starts.length === 1 && ['node', 'jsdom'].includes(starts[0].environment),
    starts.map((r) => ({ path: path.basename(String(r.path)), environment: r.environment })));
}

/**
 * One `// LINE <fn> …` marker, parsed. `-` is a row that wrote nothing;
 * `unbound:a,b` is the names it reported out of scope; everything else is a
 * `<name>=<text>` delta, whose text is compared with whitespace squashed.
 * @param {string} text the marker's arguments
 * @param {number} line the line the row it describes is recorded at
 * @returns {{fn: string, line: number, bad: string[],
 *   row: {d: Record<string, string>, u: string[]}}}
 */
function parseFocusMarker(text, line) {
  const [fn, ...args] = text.split(/\s+/);
  /** @type {Record<string, string>} */
  const d = {};
  /** @type {string[]} */
  const u = [];
  /** @type {string[]} */
  const bad = [];
  for (const arg of args) {
    if (arg === '-') continue;
    if (arg.startsWith('unbound:')) u.push(...arg.slice('unbound:'.length).split(','));
    else if (arg.includes('=')) d[arg.slice(0, arg.indexOf('='))] = arg.slice(arg.indexOf('=') + 1);
    else bad.push(arg);
  }
  return { fn, line, bad, row: { d, u: u.sort() } };
}

/**
 * Every `// LINE` marker in a probe, in source order, each attached to the next
 * line that is not itself a marker.
 *
 * Consecutive markers all describe THAT line, in order: one line can carry
 * several rows — a `for` head binds once per iteration, and the loop's own
 * completion row is recorded at the same line — and a rule that gave each
 * marker its own next line could not say so. A marker attached to a line with
 * no row fails its check rather than passing quietly.
 * @param {string} file
 * @returns {ReturnType<typeof parseFocusMarker>[]}
 */
function focusMarkers(file) {
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  const out = [];
  /** @type {string[]} */
  let pending = [];
  for (let i = 0; i < lines.length; i += 1) {
    const m = lines[i].match(/^\s*\/\/\s+LINE\s+(.+?)\s*$/);
    if (m) {
      pending.push(m[1]);
      continue;
    }
    for (const text of pending) out.push(parseFocusMarker(text, i + 1));
    pending = [];
  }
  return out;
}

/**
 * A capture as the markers spell it: the `dbg` text with its whitespace
 * squashed, and anything else named by its kind rather than by a value it does
 * not have (an unread capture must never read as the word `undefined`).
 * @param {any} capture
 * @returns {string}
 */
const spelt = (capture) => (capture && capture.k === 'dbg' ? squash(String(capture.v)) : `<${capture && capture.k}>`);

/**
 * @param {any} rec a LINE record
 * @returns {{d: Record<string, string>, u: string[]}}
 */
function focusRow(rec) {
  /** @type {Record<string, string>} */
  const d = {};
  for (const [name, capture] of Object.entries(rec.d ?? {})) d[name] = spelt(capture);
  return { d, u: [...(rec.u ?? [])].sort() };
}

/**
 * One per-file manifest the transform wrote, by root-relative path.
 * @param {string} dir the manifest directory
 * @param {string} rel
 * @returns {any|null} null when the file is absent
 */
function readManifest(dir, rel) {
  const file = path.join(dir, `${rel.split('/').join('__')}.json`);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

/**
 * The focus tier, in whichever of its two readings this run produced (R20).
 *
 * The probe project records itself WITH a focus (`vitest.config.ts`'s direct
 * branch names nine functions) and the driver records it WITHOUT one until the
 * driver learns `--focus`. Both are the contract, so both are asserted and
 * neither is skipped: the BOOT's own declaration says which run this is, the
 * manifest says what the transform did, and `focus:agree` holds the two
 * together — a transform that focused nine functions while the runtime
 * declared nothing is a broken invocation, not an unfocused one.
 * @param {Checker} k
 * @param {ReturnType<typeof index>} s
 * @param {string} manifestDir
 */
function checkFocus(k, s, manifestDir) {
  const source = path.join(HERE, FOCUS_PROBE);
  const boot = s.records.find((r) => r.e === 'BOOT');
  const caps = (boot && boot.capabilities) || {};
  const lines = s.records.filter((r) => r.e === 'LINE');
  const calls = s.records.filter((r) => r.e === 'CALL');
  const manifest = readManifest(manifestDir, FOCUS_PROBE);
  if (manifest === null) {
    // Without it there is nothing to hold the declaration to, and a checker
    // that carried on would be asserting one half of a two-sided fact.
    k.check('focus:manifest', false, `no manifest for ${FOCUS_PROBE} under ${manifestDir}`);
    return;
  }
  /** @type {string[]} */
  const selected = manifest.focused ?? [];
  const declared = caps.line === true;
  k.check('focus:agree', selected.length > 0 === declared, { focused: selected, line: declared });
  if (!declared) {
    // Driven with no `--focus`: nothing was instrumented for statements, and
    // the absence is the assertion.
    k.check('focus:mode', true, 'unfocused');
    k.check('focus:unfocused:no_lines', lines.length === 0, lines.length);
    const carrying = calls.filter((r) => Object.hasOwn(r, 'a')).length;
    k.check('focus:unfocused:no_args', carrying === 0, carrying);
    return;
  }
  k.check('focus:mode', true, 'focused');
  k.check('focus:caps', caps.line === true && caps.locals === true, caps);

  const want = focusMarkers(source);
  k.equal('focus:markers', want.flatMap((m) => m.bad), []);
  k.check('focus:count', lines.length === want.length,
    { records: lines.length, markers: want.length });
  /** @type {Map<string, {d: Record<string, string>, u: string[]}[]>} */
  const got = new Map();
  for (const rec of lines) {
    const key = `${s.frames.get(rec.f)?.name ?? '<unknown>'}:${rec.l}`;
    got.set(key, [...(got.get(key) ?? []), focusRow(rec)]);
  }
  /** @type {Map<string, {d: Record<string, string>, u: string[]}[]>} */
  const marked = new Map();
  for (const m of want) {
    const key = `${m.fn}:${m.line}`;
    marked.set(key, [...(marked.get(key) ?? []), m.row]);
  }
  for (const key of [...new Set([...marked.keys(), ...got.keys()])].sort()) {
    k.equal(`focus:${key}`, got.get(key) ?? [], marked.get(key) ?? []);
  }

  // The CALL's own map (spec §3.3): read at entry, and written for a focused
  // site only -- the test callbacks in the same file are frames too, and
  // theirs must stay absent.
  const focusedNames = new Set(selected.map((q) => last(q)));
  const argsMark = markers(source, 'ARGS');
  k.check('focus:args:marked', argsMark.length === 1, argsMark.length);
  for (const m of argsMark) {
    const [fn, ...pairs] = m.args;
    const call = calls.find((r) => s.frames.get(r.f)?.name === fn);
    /** @type {Record<string, string>} */
    const spelled = {};
    for (const [name, capture] of Object.entries((call && call.a) ?? {})) {
      spelled[name] = spelt(capture);
    }
    k.equal(`focus:args`, spelled,
      Object.fromEntries(pairs.map((p) => [p.slice(0, p.indexOf('=')), p.slice(p.indexOf('=') + 1)])));
  }
  const wrong = calls
    .map((r) => ({ name: s.frames.get(r.f)?.name ?? '<unknown>', a: Object.hasOwn(r, 'a') }))
    .filter((c) => c.a !== focusedNames.has(c.name));
  k.equal('focus:args:by_site', wrong, []);
}

// --- the runs --------------------------------------------------------------

/**
 * @param {Checker} k
 * @param {ReturnType<typeof index>[]} spools
 * @param {string} manifestDir
 */
function runVitest(k, spools, manifestDir) {
  const by = new Map(spools.map((s) => [s.probe, s]));
  k.equal('probes:present', VITEST_PROBES.filter((p) => !by.has(p)), []);
  for (const s of spools) checkContainer(k, s, true);
  const use = (/** @type {string} */ rel, /** @type {(s: any) => void} */ fn) => {
    const s = by.get(rel);
    if (s) fn(s);
  };
  use('src/async.probe.test.ts', (s) => checkAsync(k, s, 'node', 'vitest'));
  use('src/async.jsdom.probe.test.ts', (s) => checkAsync(k, s, 'jsdom', 'vitest'));
  use('src/sites.probe.test.ts', (s) => checkSites(k, s));
  use('src/swallow.probe.test.ts', (s) => checkSwallow(k, s));
  use('src/swallow3.probe.test.ts', (s) => checkUnhandled(k, s));
  use('src/escape.probe.test.ts', (s) => checkEscape(k, s));
  use('src/each.probe.test.ts', (s) => checkEach(k, s));
  use(FOCUS_PROBE, (s) => checkFocus(k, s, manifestDir));
  use('src/describe_chain.probe.test.ts', (s) => checkDescribeChain(k, s));
  use('src/never_settles.probe.test.ts', (s) => checkNeverSettles(k, s));
  use('src/timer_parentless.probe.test.ts', (s) => checkTimerParentless(k, s));
  use('src/concurrent.probe.test.ts', (s) => checkConcurrent(k, s));
  const jsdom = by.get('src/async.jsdom.probe.test.ts');
  k.report.environments = spools.map((s) => ({
    probe: s.probe,
    environment: s.records.find((r) => r.e === 'FILE_START')?.environment ?? null,
  }));
  k.check('pragma:jsdom_honoured',
    jsdom?.records.find((r) => r.e === 'FILE_START')?.environment === 'jsdom');
}

/**
 * One extension's probe: it recorded a spool, and that spool opened at least
 * one task. `basis` is asserted where the pre-registration named it and left
 * null where it did not -- a checker that asserts more than the table it was
 * written against is a checker nobody pre-registered.
 * @param {Checker} k
 * @param {ReturnType<typeof index>|undefined} s
 * @param {string} ext the label the check is named by
 * @param {string|null} basis the naming basis, or null to leave it unasserted
 */
function checkExt(k, s, ext, basis) {
  const tasks = s ? [...s.tasks.values()] : [];
  const named = basis === null || tasks.every((t) => t.basis === basis);
  k.check(`ext:${ext}:tasks`, tasks.length >= 1 && named,
    tasks.map((t) => ({ name: t.name, basis: t.basis })));
}

/**
 * The `.cjs` probe's own child, which recorded nothing and counted itself.
 * `node --test` runs one process per test file, so that child is the one
 * whose `_tally-<pid>.json` belongs to no spool in this directory.
 * @param {Checker} k
 * @param {string} dir the manifest directory
 * @param {ReturnType<typeof index>[]} spools
 */
function checkCjsTally(k, dir, spools) {
  const pids = new Set(spools.map((s) => s.name.split('-')[0]));
  const tallies = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((n) => /^_tally-\d+\.json$/.test(n)) : [];
  const orphans = tallies.filter((n) => !pids.has(n.slice('_tally-'.length, -'.json'.length)));
  if (orphans.length !== 1) {
    k.check('ext:cjs:tally', false, { tallies, spool_pids: [...pids], orphans });
    return;
  }
  k.equal('ext:cjs:tally', JSON.parse(fs.readFileSync(path.join(dir, orphans[0]), 'utf8')),
    { files_transformed: 0, functions_focused: 0, excluded: { commonjs: 1 } });
}

/**
 * @param {Checker} k
 * @param {ReturnType<typeof index>[]} spools
 * @param {string} manifestDir
 */
function runNodeTest(k, spools, manifestDir) {
  const by = new Map(spools.map((s) => [s.probe, s]));
  k.equal('probes:present', NODETEST_PROBES.filter((probe) => !by.has(probe)), []);
  // The `.cjs` one is present by being ABSENT: a spool for it would mean the
  // hook had instrumented a file it says it excluded.
  k.check('probes:no_cjs_spool', !by.has('nodetest/ext.probe.test.cjs'), [...by.keys()]);
  for (const s of spools) checkContainer(k, s, false);
  const async_ = by.get('nodetest/async.probe.test.ts');
  // No setup file, so no provider: a task is named by its lexical title.
  if (async_) checkAsync(k, async_, 'nodetest', 'title');
  checkExt(k, by.get('nodetest/ext.probe.test.mts'), 'mts', 'title');
  checkExt(k, by.get('nodetest/ext.probe.test.mjs'), 'mjs', null);
  checkCjsTally(k, manifestDir, spools);
}

/**
 * The plugin's own count of what it did, when the manifest directory was set.
 * @param {Checker} k @param {string} dir
 */
function checkTally(k, dir) {
  const file = path.join(dir, '_tally.json');
  if (!fs.existsSync(file)) {
    k.check('tally:written', false, `${file} is absent`);
    return;
  }
  const tally = JSON.parse(fs.readFileSync(file, 'utf8'));
  k.report.tally = tally;
  k.check('tally:written', typeof tally.files_transformed === 'number' &&
    tally.files_transformed > 0 && typeof tally.excluded === 'object', tally);
  // One manifest per file the plugin looked at, `files_transformed` for the ones
  // it edited. The two agree exactly when nothing failed to parse — and a file
  // Vite asked for twice (one module graph per transform mode) is one file.
  const manifests = fs.readdirSync(dir).filter((n) => n.endsWith('.json') && n !== '_tally.json');
  k.equal('tally:files', {
    files_transformed: tally.files_transformed,
    parse_errors: tally.excluded['parse-error'] ?? 0,
  }, { files_transformed: manifests.length, parse_errors: 0 });
}

/** One line, and never a guess about what the caller meant. */
const USAGE = 'usage: node check.mjs <vitest|nodetest> <spool dir> <manifest dir>';

/**
 * @param {string} reason
 * @returns {never}
 */
function refuse(reason) {
  process.stderr.write(`check.mjs: ${reason}. ${USAGE}\n`);
  process.exit(2);
}

function main() {
  const [mode, spoolDir, manifestDir] = process.argv.slice(2);
  // An unset `SENSORIUM_SPOOL` reaches a shell script as an empty argument, so
  // empty and absent are the same refusal: nothing was recorded to check.
  if (mode !== 'vitest' && mode !== 'nodetest') refuse(`unknown mode ${JSON.stringify(mode ?? null)}`);
  if (!spoolDir) refuse('no spool directory — is SENSORIUM_SPOOL set?');
  if (!manifestDir) refuse('no manifest directory — is SENSORIUM_MANIFEST_DIR set?');
  if (!fs.existsSync(spoolDir)) refuse(`${spoolDir} does not exist — did the run record anything?`);
  const k = new Checker();
  const spools = readSpools(spoolDir).map(index);
  k.check('spools:any', spools.length > 0, spools.length);
  if (spools.length > 0 && mode === 'nodetest') runNodeTest(k, spools, manifestDir);
  if (spools.length > 0 && mode === 'vitest') runVitest(k, spools, manifestDir);
  if (mode === 'vitest') checkTally(k, manifestDir);
  const ok = k.failures.length === 0;
  process.stdout.write(`${JSON.stringify({
    mode, spool_dir: spoolDir, spools: spools.length,
    ok, failures: k.failures, report: k.report, checks: k.checks,
  }, null, 2)}\n`);
  process.exitCode = ok ? 0 : 1;
}

main();
