// The focus tier's splices, on the branches a golden cannot show. The goldens
// pin whole files byte for byte; this file pins the RULES behind them — which
// statements mint a row and which do not, where a head row goes and where it
// must not, what a bare body's wrap does to the statements inside it, and what
// pass one alone answers for the resolver.
//
// Every assertion is made against the transform's real output for a fragment
// written here, so a rule that changed would move a substring, not a comment.
import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';

import { sitesOf, transformSource } from '../src/transform.mjs';

const require = createRequire(import.meta.url);
const ts = require('typescript');

const ROOT = '/w';
const RT = 'RT';
const FILE = `${ROOT}/src/a.ts`;

/**
 * @param {string[]} lines the fragment, one entry per line
 * @param {string[]} [focus]
 * @param {string} [file]
 * @returns {string} the instrumented source
 */
function run(lines, focus = ['f'], file = FILE) {
  const out = transformSource(`${lines.join('\n')}\n`, file, { root: ROOT, ts, rtPath: RT, focus });
  assert.ok(out && out.code !== null, 'the fragment parsed and was instrumented');
  return out.code;
}

/**
 * @param {string[]} lines
 * @param {string[]} [focus]
 * @returns {import('../src/transform.mjs').Manifest}
 */
function manifestOf(lines, focus = ['f']) {
  const out = transformSource(`${lines.join('\n')}\n`, FILE, { root: ROOT, ts, rtPath: RT, focus });
  assert.ok(out, 'the fragment is ours');
  return out.manifest;
}

/** @param {string} code @returns {number} how many statement probes it holds */
const rows = (code) => (code.match(/__srt\.line\(/g) ?? []).length;

// --- what mints a row, and what does not -----------------------------------

test('a completion — `return`, `throw`, `break`, `continue` — mints no row', () => {
  // None of them completes normally, and each one's exit is already on the
  // record: the RETURN, the UNWIND, or the enclosing statement's own row.
  const code = run([
    'export function f(xs: number[]): number {',
    '  for (const x of xs) {',
    '    if (x < 0) continue;',
    '    if (x > 9) break;',
    '    if (x === 3) throw new Error("three");',
    '  }',
    '  return 0;',
    '}',
  ]);
  assert.equal(code.includes('return __srt.ret(__sf,(0));__srt.line'), false);
  assert.equal(code.includes('continue;__srt.line'), false);
  assert.equal(code.includes('break;__srt.line'), false);
  assert.equal(code.includes('),5);__srt.line'), false, 'the throw keeps its raise and nothing else');
  // Three `if`s, their three wrapped bare bodies (which mint none of their own),
  // the head row none of them has, the `for`'s head row and the `for`'s row.
  assert.equal(rows(code), 5);
});

test('a `return` inside a wrapped bare body is wrapped and still mints no row', () => {
  // The wrap is what keeps the body's probe inside the guard (plan P2); a body
  // that is a `return` has no probe at all, and the wrap must not invent one.
  const code = run([
    'export function f(c: boolean): number {',
    '  if (c) return 1;',
    '  return 0;',
    '}',
  ]);
  assert.ok(code.includes('  if (c) {return __srt.ret(__sf,(1));}__srt.line(__sf,2,[]);'), code);
  assert.equal(rows(code), 1, "only the `if`'s own completion row");
});

test('a hoisted function declaration mints no row; a class declaration mints its name', () => {
  // A `function` statement executes nowhere in particular — it is hoisted — and
  // a `class` executes where it stands (spec §3.1).
  const code = run([
    'export function f(): unknown {',
    '  function helper(): number { return 1; }',
    '  class Foo {}',
    '  return new Foo();',
    '}',
  ]);
  assert.equal(code.includes('return 1; }__srt.line'), false);
  assert.equal(code.includes('return 1; };__srt.line'), false);
  assert.ok(code.includes('  class Foo {};__srt.line(__sf,3,["Foo",Foo]);'), code);
  assert.equal(rows(code), 1);
});

test('R17: an interface, a type alias and a `declare` statement mint no row', () => {
  // TypeScript erases all three, so each would be a row for a line that never
  // ran. `enum` and `class` are not erased and are pinned by the golden.
  const code = run([
    'export function f(n: number): number {',
    '  interface Point { x: number }',
    '  type Pair = [number, number];',
    '  declare const later: number;',
    '  const p: Point = { x: n };',
    '  return p.x + later;',
    '}',
  ]);
  assert.equal(code.includes('interface Point { x: number };__srt.line'), false);
  assert.equal(code.includes('type Pair = [number, number];__srt.line'), false);
  assert.equal(code.includes('declare const later: number;__srt.line'), false);
  assert.ok(code.includes('  const p: Point = { x: n };__srt.line(__sf,5,["p",p]);'), code);
  assert.equal(rows(code), 1);
});

test('an empty statement mints no row, and a bare block mints one with its dead names', () => {
  const code = run([
    'export function f(): number {',
    '  let out = 0;',
    '  ;',
    '  {',
    '    const z = 1;',
    '    out = z;',
    '  }',
    '  return out;',
    '}',
  ]);
  assert.equal(code.includes('  ;__srt.line'), false);
  assert.ok(code.includes('  };__srt.line(__sf,4,[],["z"]);'), code);
});

// --- the guard's two rows ---------------------------------------------------

test("a guard's block body mints no row of its own: the guard's row is its row", () => {
  // The block completes when the guard does, and `declaredIn` already reports
  // the block's dead names on the guard's row — a second row would report one
  // completion twice and pop the same names twice.
  const code = run([
    'export function f(c: boolean): number {',
    '  let out = 0;',
    '  if (c) {',
    '    const y = 1;',
    '    out = y;',
    '  }',
    '  return out;',
    '}',
  ]);
  assert.ok(code.includes('  };__srt.line(__sf,3,[],["y"]);'), code);
  assert.equal(rows(code), 4, 'out, y, out = y — and one row for the whole `if`');
});

test('P1: a `for (let i …)` completion row excludes `i`, and lists it as unbound', () => {
  // `i` is dead by the time the loop completes, so it is `unbound` and never a
  // delta; the head row is where its per-iteration value is reported.
  const code = run([
    'export function f(n: number): number {',
    '  let s = 0;',
    '  for (let i = 0; i < n; i++) {',
    '    s += i;',
    '  }',
    '  return s;',
    '}',
  ]);
  assert.ok(code.includes('  for (let i = 0; i < n; i++) {__srt.line(__sf,3,["i",i]);'), code);
  assert.ok(code.includes('  };__srt.line(__sf,3,[],["i"]);'), code);
});

test("§3.2: an `else` branch is not an entry, so it carries no head row", () => {
  // The head row says a guard was ENTERED with these names bound. A falsy test
  // entered nothing, and what it wrote is reported by the `if`'s own completion
  // row instead (plan P1) — which is why the wrap is still made for a bare
  // `else` body: the body's own probe has to sit inside the branch.
  const code = run([
    'export function f(n: number): number {',
    '  let x = 0;',
    '  if ((x = n)) {',
    '    x += 1;',
    '  } else {',
    '    x -= 1;',
    '  }',
    '  return x;',
    '}',
  ]);
  assert.ok(code.includes('  if ((x = n)) {__srt.line(__sf,3,["x",x]);'), code);
  assert.ok(code.includes('  } else {\n'), code);
  assert.ok(code.includes('  };__srt.line(__sf,3,["x",x]);'), code);
});

test('an `else if` body is wrapped like any other, and mints its own row inside', () => {
  const code = run([
    'export function f(a: boolean, b: boolean): number {',
    '  let x = 0;',
    '  if (a) x = 1;',
    '  else if (b) x = 2;',
    '  return x;',
    '}',
  ]);
  assert.ok(code.includes('  if (a) {x = 1;__srt.line(__sf,3,["x",x]);}\n'), code);
  // The inner `if`'s row closes inside the outer `else`'s wrap, and the outer
  // `if`'s row lands outside it — after the whole `if`/`else`, which is where
  // that statement ends.
  assert.ok(code.includes(
    '  else {if (b) {x = 2;__srt.line(__sf,4,["x",x]);}__srt.line(__sf,4,[]);}'
    + '__srt.line(__sf,3,[]);'), code);
});

test('R15/R16: a labeled loop is not wrapped and the label mints no row', () => {
  // Wrapping a labeled loop in a block turns `continue outer` into a syntax
  // error — the label would no longer name a loop. The label mints nothing of
  // its own either: it is not a statement that runs.
  const code = run([
    'export function f(xs: number[]): number {',
    '  let n = 0;',
    '  outer: for (const x of xs) {',
    '    for (const y of xs) {',
    '      if (y > x) continue outer;',
    '      n += 1;',
    '    }',
    '  }',
    '  return n;',
    '}',
  ]);
  assert.ok(code.includes('  outer: for (const x of xs) {__srt.line(__sf,3,["x",x]);'), code);
  assert.equal(code.includes('outer: {'), false, 'the labeled loop keeps its label on the loop');
  // Two rows per loop (a head row and a completion row), one for `n += 1`, one
  // for the `if` — and none at all for the label, which would double the outer
  // loop's completion row on the very same offset.
  assert.equal(rows(code), 7);
  const sf = ts.createSourceFile(FILE, code, ts.ScriptTarget.Latest, false, ts.ScriptKind.TS);
  assert.deepEqual(/** @type {any} */ (sf).parseDiagnostics.map((/** @type {any} */ d) =>
    d.messageText), [], 'the labeled output still parses');
});

test('a labeled BLOCK is probed as its own statement: the label mints nothing', () => {
  const code = run([
    'export function f(c: boolean): number {',
    '  let out = 0;',
    '  done: {',
    '    const y = 1;',
    '    if (c) break done;',
    '    out = y;',
    '  }',
    '  return out;',
    '}',
  ]);
  assert.ok(code.includes('  };__srt.line(__sf,3,[],["y"]);'), code);
  assert.equal(rows(code), 5, 'out, the block, y, the `if`, out = y — the label mints none');
});

test('a `switch` gets no head row; its clause statements and blocks are probed', () => {
  const code = run([
    'export function f(k: number): number {',
    '  let out = 0;',
    '  switch (k) {',
    '    case 1: {',
    '      const q = 1;',
    '      out = q;',
    '      break;',
    '    }',
    '    default:',
    '      out = 2;',
    '  }',
    '  return out;',
    '}',
  ]);
  assert.ok(code.includes('  switch (k) {\n'), 'no head row after the discriminant');
  assert.ok(code.includes('    };__srt.line(__sf,4,[],["q"]);'), code);
  assert.ok(code.includes('      out = 2;__srt.line(__sf,10,["out",out]);'), code);
  assert.ok(code.includes('  };__srt.line(__sf,3,[]);'), code);
});

test('a `catch` head row follows the HANDLED, and a destructured binding is read', () => {
  const code = run([
    'export function f(): number {',
    '  let n = 0;',
    '  try {',
    '    risky();',
    '  } catch ({ code }) {',
    '    n = 1;',
    '  }',
    '  return n;',
    '}',
  ]);
  assert.ok(code.includes(
    '  } catch ({ code }) {__srt.handled(__sf,undefined,5,"catch_escaped");'
    + '__srt.line(__sf,5,["code",code]);'), code);
  assert.ok(code.includes('  };__srt.line(__sf,3,[],["code"]);'), code);
});

test('a `catch` with no binding gets the runtime one and no head row', () => {
  const code = run([
    'export function f(): number {',
    '  try {',
    '    risky();',
    '  } catch {',
    '    return 1;',
    '  }',
    '  return 0;',
    '}',
  ]);
  assert.ok(code.includes('  } catch(__sce) {__srt.handled(__sf,__sce,4,"catch");\n'), code);
  assert.equal(code.includes('__sce]'), false, 'the runtime binding is never a delta');
});

test('P3: a suspension that is a whole statement closes INSIDE the row', () => {
  // The ordering the whole file rests on. `yield` with no expression and no
  // semicolon ends where its statement ends, so the suspension rewrite's closer
  // and the row are registered at ONE offset; the row goes first, and
  // magic-string renders it last. Registered the other way round, the closer
  // would land after the row and the module would not parse.
  //
  // Both splices give that statement the semicolon ASI gave it, so the output
  // carries an empty statement between them — legal, deliberate, and pinned
  // here rather than discovered later.
  const code = run([
    'export function* f(xs: number[]): Generator<number> {',
    '  let i = 0;',
    '  yield',
    '  for (const x of xs) yield x;',
    '  i += 1;',
    '}',
  ]);
  assert.ok(code.includes(
    '  __srt.r(__sf,yield __srt.y(__sf,(undefined),1));;__srt.line(__sf,3,[]);'), code);
  assert.ok(code.includes(
    '  for (const x of xs) {__srt.line(__sf,4,["x",x]);'
    + '__srt.r(__sf,yield __srt.y(__sf,(x),1));__srt.line(__sf,4,[]);}'
    + '__srt.line(__sf,4,[],["x"]);'), code);
  const sf = ts.createSourceFile(FILE, code, ts.ScriptTarget.Latest, false, ts.ScriptKind.TS);
  assert.deepEqual(/** @type {any} */ (sf).parseDiagnostics.map((/** @type {any} */ d) =>
    d.messageText), []);
});

// --- the frame, and what is not one -----------------------------------------

test("an unfocused function's output is byte-identical to the same file with no focus", () => {
  const lines = [
    'export function f(a: number): number {',
    '  const b = a + 1;',
    '  return b;',
    '}',
    '',
    'export function g(a: number): number {',
    '  const b = a + 1;',
    '  return b;',
    '}',
  ];
  const focused = run(lines, ['f']);
  const plain = run(lines, []);
  const tail = (/** @type {string} */ code) => code.slice(code.indexOf('export function g'));
  assert.equal(tail(focused), tail(plain));
  assert.equal(plain.includes('__srt.line('), false, 'no focus, no statement probes at all');
  assert.equal(plain.includes('__srt.call(__sfile,0);'), true, 'and no arguments either');
});

test('a nested function is focused by naming its container, and is its own frame', () => {
  const code = run([
    'export function f(): number {',
    '  const inner = (n: number): number => {',
    '    const m = n * 2;',
    '    return m;',
    '  };',
    '  return inner(1);',
    '}',
  ], ['f']);
  assert.ok(code.includes('(n: number): number => {const __sf=__srt.call(__sfile,1,["n",n]);'), code);
  assert.ok(code.includes('    const m = n * 2;__srt.line(__sf,3,["m",m]);'), code);
});

test('a statement of a NESTED unfocused function is not probed', () => {
  // `--focus f.inner` reaches one callback; `f`'s own statements are not it.
  const code = run([
    'export function f(): number {',
    '  const inner = (n: number): number => {',
    '    const m = n * 2;',
    '    return m;',
    '  };',
    '  return inner(1);',
    '}',
  ], ['f.inner']);
  assert.ok(code.includes('    const m = n * 2;__srt.line(__sf,3,["m",m]);'), code);
  assert.ok(code.includes('export function f(): number {const __sf=__srt.call(__sfile,0);try{'), code);
  assert.equal(rows(code), 1, "only the inner arrow's statement");
});

test('a focused function with no parameters carries an EMPTY argument list', () => {
  // "no arguments" and "the arguments were not read" are two different facts:
  // the empty array is the first, an absent third argument the second.
  const code = run(['export function f(): number {', '  return 1;', '}']);
  assert.ok(code.includes('__srt.call(__sfile,0,[]);'), code);
});

test('a focused CALL reads every name its parameters bind, `this` excluded', () => {
  const code = run([
    'export function f(this: unknown, { a, b: [c] }: any, d = 1, ...rest: number[]): number {',
    '  return a + c + d + rest.length;',
    '}',
  ]);
  assert.ok(code.includes('__srt.call(__sfile,0,["a",a,"c",c,"d",d,"rest",rest]);'), code);
});

test('a spec naming another file focuses nothing here', () => {
  const code = run(['export function f(): number {', '  return 1;', '}'], ['other.ts:f']);
  assert.equal(code.includes('__srt.line('), false);
  assert.ok(code.includes('__srt.call(__sfile,0);'), code);
});

// --- the manifest -----------------------------------------------------------

test("the manifest names the sites the focus selected, and marks each site", () => {
  const m = manifestOf([
    'export function f(): number {',
    '  const inner = () => 1;',
    '  return inner();',
    '}',
    'export function g(): number {',
    '  return 2;',
    '}',
  ], ['f']);
  assert.deepEqual(m.instrumented, [
    { qualname: 'f', line: 1, kind: 'function', focused: true },
    { qualname: 'f.inner', line: 2, kind: 'function', focused: true },
    { qualname: 'g', line: 5, kind: 'function', focused: false },
  ]);
  assert.deepEqual(m.focused, ['f', 'f.inner']);
});

test('with no focus the manifest lists none, and every site says so', () => {
  const m = manifestOf(['export function f(): number {', '  return 1;', '}'], []);
  assert.deepEqual(m.focused, []);
  assert.deepEqual(m.instrumented, [{ qualname: 'f', line: 1, kind: 'function', focused: false }]);
});

// --- pass one alone, for the resolver ---------------------------------------

test('sitesOf answers pass one and splices nothing', () => {
  const src = [
    'export function f(): number {',
    '  return 1;',
    '}',
    'declare function ambient(): void;',
    '',
  ].join('\n');
  const out = sitesOf(src, FILE, { root: ROOT, ts });
  assert.ok(out);
  assert.equal(out.rel, 'src/a.ts');
  assert.deepEqual(out.sites, [{ qualname: 'f', line: 1, kind: 'function', focused: false }]);
  assert.deepEqual(out.excluded, { ambient: 1 });
  const focused = sitesOf(src, FILE, { root: ROOT, ts, focus: ['f'] });
  assert.deepEqual(focused?.sites.map((s) => s.focused), [true]);
});

test('sitesOf returns null for a path this recorder does not transform', () => {
  const src = 'export function f(): void {}\n';
  assert.equal(sitesOf(src, '/elsewhere/src/a.ts', { root: ROOT, ts }), null);
  assert.equal(sitesOf(src, path.join(ROOT, 'node_modules', 'dep', 'i.js'), { root: ROOT, ts }), null);
  assert.equal(sitesOf(src, `${ROOT}/src/legacy.cjs`, { root: ROOT, ts }), null);
});

test('sitesOf reports a file that does not parse rather than guessing at its sites', () => {
  const out = sitesOf('export function f() {\n  g(\n}\n', FILE, { root: ROOT, ts });
  assert.ok(out);
  assert.deepEqual(out.sites, []);
  assert.deepEqual(out.excluded, { 'parse-error': 1 });
});
