// The binding rules, one test per row of spec §3.2's table and per arm of the
// three lists the plan writes down (`writesOf`'s table, `headBindingsOf`'s
// list, `declaredIn`'s list). `bindings.mjs` is `escape.mjs`'s sibling — pure
// functions over the consumer's own AST, no state, no I/O — so these tests
// parse a fragment with that TypeScript, find the statement, and ask the
// function directly. No transform, no runtime, no spool.
//
// Order and duplicates are part of every answer (a LINE record's `deltas` are
// read left to right by the reader), so every assertion is a `deepEqual` on the
// whole array and never a set membership.
import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';

import {
  boundNames,
  declaredIn,
  headBindingsOf,
  headDeclaredOf,
  isStatementPosition,
  paramNames,
  writesOf,
} from '../src/bindings.mjs';

const require = createRequire(import.meta.url);
const ts = require('typescript');

/**
 * @param {string} src
 * @returns {import('typescript').SourceFile}
 */
function parse(src) {
  const sf = ts.createSourceFile('t.ts', src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  assert.deepEqual(/** @type {any} */ (sf).parseDiagnostics.map((/** @type {any} */ d) =>
    d.messageText), [], `the fragment parses: ${src}`);
  return sf;
}

/**
 * @param {import('typescript').Node} root
 * @param {(n: import('typescript').Node) => boolean} pred
 * @returns {any} the first node in document order the predicate accepts
 */
function find(root, pred) {
  /** @type {any} */
  let found = null;
  /** @param {import('typescript').Node} node */
  const visit = (node) => {
    if (found) return;
    if (pred(node)) {
      found = node;
      return;
    }
    ts.forEachChild(node, visit);
  };
  ts.forEachChild(root, visit);
  assert.ok(found, 'the fragment holds the node this row is about');
  return found;
}

/**
 * A statement of a function body. The wrapper is what makes `return`, `await`
 * and a bare block legal, and it is also the frame every probe would sit in.
 * @param {string} src one or more statements
 * @param {number} [index] which of them
 * @returns {any}
 */
function stmt(src, index = 0) {
  const sf = parse(`async function f() {\n${src}\n}\n`);
  const fn = find(sf, (n) => ts.isFunctionDeclaration(n));
  const found = fn.body.statements[index];
  assert.ok(found, `the fragment holds statement ${index}`);
  return found;
}

/** @param {string} src @param {number} [index] */
const writes = (src, index = 0) => writesOf(ts, stmt(src, index));
/** @param {string} src @param {number} [index] */
const heads = (src, index = 0) => headBindingsOf(ts, stmt(src, index));
/** @param {string} src @param {number} [index] */
const declaredHead = (src, index = 0) => headDeclaredOf(ts, stmt(src, index));
/** @param {string} src @param {number} [index] */
const declared = (src, index = 0) => declaredIn(ts, stmt(src, index));

// ---------------------------------------------------------------- boundNames

test('boundNames of a plain identifier is the name', () => {
  const decl = find(parse('const x = 1;'), (n) => ts.isVariableDeclaration(n));
  assert.deepEqual(boundNames(ts, decl.name), ['x']);
});

test('boundNames walks nested patterns, defaults and rest', () => {
  const decl = find(parse('const {a, b: [c] = [0], ...r} = o;'),
    (n) => ts.isVariableDeclaration(n));
  assert.deepEqual(boundNames(ts, decl.name), ['a', 'c', 'r']);
});

test('boundNames keeps a `_`-prefixed name — nothing here judges a spelling', () => {
  const decl = find(parse('const {_x, y: _y} = o;'), (n) => ts.isVariableDeclaration(n));
  assert.deepEqual(boundNames(ts, decl.name), ['_x', '_y']);
});

test('boundNames skips an array hole and reads the property name of nothing', () => {
  const decl = find(parse('const [, second] = xs;'), (n) => ts.isVariableDeclaration(n));
  assert.deepEqual(boundNames(ts, decl.name), ['second']);
});

// -------------------------------------------------------- isStatementPosition

test('isStatementPosition is true for a statement of a block', () => {
  assert.equal(isStatementPosition(ts, stmt('foo();')), true);
});

test('isStatementPosition is true for a then-statement', () => {
  const then = stmt('if (c) x = 1;').thenStatement;
  assert.equal(isStatementPosition(ts, then), true);
});

test('isStatementPosition is true for an else-statement', () => {
  const otherwise = stmt('if (c) x = 1; else x = 2;').elseStatement;
  assert.equal(isStatementPosition(ts, otherwise), true);
});

test('isStatementPosition is true for a loop body that is not a block', () => {
  const body = stmt('while (c) x = 1;').statement;
  assert.equal(isStatementPosition(ts, body), true);
});

test('isStatementPosition is true for a labeled statement body', () => {
  const body = stmt('outer: for (;;) break outer;').statement;
  assert.equal(isStatementPosition(ts, body), true);
});

test('isStatementPosition is true for a statement of a case clause', () => {
  const clause = find(parse('switch (k) { case 1: foo(); }'), (n) => ts.isCaseClause(n));
  assert.equal(isStatementPosition(ts, clause.statements[0]), true);
});

test('isStatementPosition is false for a case clause expression', () => {
  const clause = find(parse('switch (k) { case 1: foo(); }'), (n) => ts.isCaseClause(n));
  assert.equal(isStatementPosition(ts, clause.expression), false);
});

test('isStatementPosition is false for a return expression', () => {
  const expr = stmt('return g();').expression;
  assert.equal(isStatementPosition(ts, expr), false);
});

test('isStatementPosition is false at module level — module code is never a frame', () => {
  const sf = parse('foo();\n');
  assert.equal(isStatementPosition(ts, sf.statements[0]), false);
});

// ------------------------------------------------- writesOf: the declarations

test('writesOf a `let x;` is `x` — JavaScript binds it to undefined', () => {
  assert.deepEqual(writes('let x;'), ['x']);
});

test('writesOf a destructuring const is every identifier the pattern binds', () => {
  assert.deepEqual(writes('const {a, b: [c] = [0], ...r} = o;'), ['a', 'c', 'r']);
});

test('writesOf a multi-declaration statement is every name in source order', () => {
  assert.deepEqual(writes('let x = 1, y = 2;'), ['x', 'y']);
});

test('writesOf a `var` statement is its names — `var` writes like any other', () => {
  assert.deepEqual(writes('var v = 1;'), ['v']);
});

test('writesOf a `using` declaration is the name it binds', () => {
  assert.deepEqual(writes('using x = f();'), ['x']);
  assert.deepEqual(writes('await using y = g();'), ['y']);
});

test('writesOf a declaration also carries an assignment inside its initialiser', () => {
  assert.deepEqual(writes('const a = (b = 1);'), ['a', 'b']);
});

test('writesOf a class declaration is the class name', () => {
  assert.deepEqual(writes('class Foo {}'), ['Foo']);
});

test('writesOf a nameless default-exported class is empty — it binds nothing local', () => {
  const sf = parse('export default class {}\n');
  assert.deepEqual(writesOf(ts, sf.statements[0]), []);
});

// -------------------------------------------------- writesOf: the assignments

test('writesOf a plain assignment is its target', () => {
  assert.deepEqual(writes('x = 1;'), ['x']);
});

test('writesOf a compound assignment is its target', () => {
  assert.deepEqual(writes('x += 1;'), ['x']);
});

test('writesOf every compound operator reads the same', () => {
  for (const op of ['-=', '*=', '/=', '%=', '**=', '<<=', '>>=', '>>>=', '&=', '|=', '^=']) {
    assert.deepEqual(writes(`x ${op} 1;`), ['x'], op);
  }
});

test('writesOf a logical assignment is its target — it may not write, and says so', () => {
  assert.deepEqual(writes('x ||= 1;'), ['x']);
  assert.deepEqual(writes('x &&= 1;'), ['x']);
  assert.deepEqual(writes('x ??= 1;'), ['x']);
});

test('writesOf a postfix update is its operand', () => {
  assert.deepEqual(writes('i++;'), ['i']);
  assert.deepEqual(writes('i--;'), ['i']);
});

test('writesOf a prefix update is its operand', () => {
  assert.deepEqual(writes('++i;'), ['i']);
  assert.deepEqual(writes('--i;'), ['i']);
});

test('writesOf a swap is both targets in source order', () => {
  assert.deepEqual(writes('[a, b] = [b, a];'), ['a', 'b']);
});

test('writesOf an object destructuring assignment reads every property form', () => {
  assert.deepEqual(writes('({a, b: c, d: e = 1, ...rest} = o);'), ['a', 'c', 'e', 'rest']);
});

test('writesOf an array destructuring assignment reads defaults and rest', () => {
  assert.deepEqual(writes('[a = 1, ...rest] = xs;'), ['a', 'rest']);
});

test('writesOf reads an assignment at any depth of the statement', () => {
  assert.deepEqual(writes('foo(bar((x = 1)));'), ['x']);
});

test('writesOf names a target once however often it is written', () => {
  assert.deepEqual(writes('x = (x = 1) + x++;'), ['x']);
});

test('writesOf an expression statement that writes nothing is empty', () => {
  assert.deepEqual(writes('foo();'), []);
  assert.deepEqual(writes('await p;'), []);
  assert.deepEqual(writes('console.log(x);'), []);
});

// ------------------------------------------------- writesOf: the place writes

test('writesOf a property write is empty — a place write, declared', () => {
  assert.deepEqual(writes('a.b = 1;'), []);
});

test('writesOf an element write is empty, and still reads the index it updates', () => {
  assert.deepEqual(writes('a[i] = 1;'), []);
  assert.deepEqual(writes('arr[i++] = 0;'), ['i']);
});

test('writesOf a `delete` and a property update is empty', () => {
  assert.deepEqual(writes('delete a.b;'), []);
  assert.deepEqual(writes('a.b++;'), []);
});

// --------------------------------------------- writesOf: the closure boundary

test('writesOf never walks into an arrow body', () => {
  assert.deepEqual(writes('xs.map(y => (z = 1));'), []);
});

test('writesOf never walks into a function expression body', () => {
  assert.deepEqual(writes('const h = function () { z = 1; };'), ['h']);
});

test('writesOf never walks into a class member body', () => {
  assert.deepEqual(writes('const C = class { m() { z = 1; } };'), ['C']);
});

test('writesOf never walks into a nested function declaration', () => {
  assert.deepEqual(writes('function inner() { z = 1; }'), []);
});

test('writesOf still reads an assignment in a call that holds a callback', () => {
  assert.deepEqual(writes('run((n = 1), () => { z = 2; });'), ['n']);
});

test('writesOf walks a class heritage expression — it runs where the class stands', () => {
  assert.deepEqual(writes('const C = class extends (Base = f()) {};'), ['C', 'Base']);
  assert.deepEqual(writes('class Foo extends (Base = f()) {}'), ['Foo', 'Base']);
});

test('writesOf walks a computed member name — it runs where the class stands', () => {
  assert.deepEqual(writes('const D = class { [(k = 1)]() {} };'), ['D', 'k']);
});

test('writesOf stops at a member body and at a field initialiser, which run later', () => {
  assert.deepEqual(writes('const E = class { m() { z = 1; } p = (w = 2); };'), ['E']);
});

// ---------------------------------------------- writesOf: the block-likes

test('writesOf an if is the assignments of its test', () => {
  assert.deepEqual(writes('if ((x = f())) {}'), ['x']);
});

test('writesOf a while is the assignments of its test — plan P1, the last write', () => {
  assert.deepEqual(writes('while ((m = re.exec(s)) !== null) { const c = 1; }'), ['m']);
});

test('writesOf a do-while is the assignments of its test', () => {
  assert.deepEqual(writes('do { step(); } while ((m = next()) !== null);'), ['m']);
});

test('writesOf a switch is the assignments of its discriminant', () => {
  assert.deepEqual(writes('switch ((x = f())) { }'), ['x']);
});

test('writesOf a for reads its initialiser, condition and incrementor', () => {
  assert.deepEqual(writes('for (i = 0; (n = size()) > i; i++) {}'), ['i', 'n']);
});

test('writesOf a for whose head declares excludes the declared name (plan P1)', () => {
  assert.deepEqual(writes('for (let i = 0; i < n; i++) {}'), []);
});

test('writesOf a for whose head is a `var` keeps the name — `var` outlives the loop', () => {
  assert.deepEqual(writes('for (var i = 0; i < n; i++) {}'), ['i']);
});

test('writesOf a for-of over a declaration is empty', () => {
  assert.deepEqual(writes('for (const v of xs) { total += v; }'), []);
});

test('writesOf a for-of reads assignments in the iterated expression', () => {
  assert.deepEqual(writes('for (const v of (xs = list())) {}'), ['xs']);
});

test('writesOf a for-in over a declaration is empty', () => {
  assert.deepEqual(writes('for (const k in o) {}'), []);
});

test('writesOf a try, a labeled statement, a bare block and an empty statement is empty', () => {
  assert.deepEqual(writes('try { x = 1; } catch (e) {}'), []);
  assert.deepEqual(writes('outer: { x = 1; }'), []);
  assert.deepEqual(writes('{ x = 1; }'), []);
  assert.deepEqual(writes(';'), []);
});

// ------------------------------------------------------------ headBindingsOf

test('headBindingsOf a for-of declaration is what the pattern binds', () => {
  assert.deepEqual(heads('for (const v of xs) {}'), ['v']);
  assert.deepEqual(heads('for (const [k, v] of m) {}'), ['k', 'v']);
});

test('headBindingsOf a for-await reads exactly as a for-of', () => {
  assert.deepEqual(heads('for await (const v of xs) {}'), ['v']);
});

test('headBindingsOf a for-of over an existing binding is that binding', () => {
  assert.deepEqual(heads('for (x of xs) {}'), ['x']);
  assert.deepEqual(heads('for ([a, b] of pairs) {}'), ['a', 'b']);
});

test('headBindingsOf a for-in declaration is the key', () => {
  assert.deepEqual(heads('for (const k in o) {}'), ['k']);
});

test('headBindingsOf a for head declaration is every name it declares', () => {
  assert.deepEqual(heads('for (let i = 0, j = 1; i < n; i++) {}'), ['i', 'j']);
});

test('headBindingsOf a for head expression is its assignment targets', () => {
  assert.deepEqual(heads('for (i = 0; i < n; i++) {}'), ['i']);
});

test('headBindingsOf a for with no initialiser is empty', () => {
  assert.deepEqual(heads('for (;;) { break; }'), []);
});

test('headBindingsOf a while, a do and an if is the assignments of the test', () => {
  assert.deepEqual(heads('while ((m = re.exec(s)) !== null) {}'), ['m']);
  assert.deepEqual(heads('do { step(); } while ((m = next()));'), ['m']);
  assert.deepEqual(heads('if ((x = f())) {}'), ['x']);
});

test('headBindingsOf a guard that binds nothing is empty', () => {
  assert.deepEqual(heads('if (c) {}'), []);
});

test('headBindingsOf a switch is empty — a discriminant mints no head row', () => {
  assert.deepEqual(heads('switch ((x = f())) { }'), []);
});

test('headBindingsOf a catch clause is what its binding binds', () => {
  const clause = find(parse('try { r(); } catch (e) {}'), (n) => ts.isCatchClause(n));
  assert.deepEqual(headBindingsOf(ts, clause), ['e']);
});

test('headBindingsOf a destructured catch clause is every name it binds', () => {
  const clause = find(parse('try { r(); } catch ({code, causes: [first]}) {}'),
    (n) => ts.isCatchClause(n));
  assert.deepEqual(headBindingsOf(ts, clause), ['code', 'first']);
});

test('headBindingsOf a bindingless catch clause is empty', () => {
  const clause = find(parse('try { r(); } catch {}'), (n) => ts.isCatchClause(n));
  assert.deepEqual(headBindingsOf(ts, clause), []);
});

// ------------------------------------------------------------ headDeclaredOf

test('headDeclaredOf a for head `let` is the declared name', () => {
  assert.deepEqual(declaredHead('for (let i = 0; i < n; i++) {}'), ['i']);
});

test('headDeclaredOf a for head `const` of a for-of is the declared name', () => {
  assert.deepEqual(declaredHead('for (const v of xs) {}'), ['v']);
});

test('headDeclaredOf a for head `var` is empty — it is not block-scoped', () => {
  assert.deepEqual(declaredHead('for (var i = 0; i < n; i++) {}'), []);
  assert.deepEqual(declaredHead('for (var v of xs) {}'), []);
});

test('headDeclaredOf a head that only assigns is empty', () => {
  assert.deepEqual(declaredHead('while ((m = next())) {}'), []);
  assert.deepEqual(declaredHead('for (i = 0; i < n; i++) {}'), []);
  assert.deepEqual(declaredHead('if ((x = f())) {}'), []);
});

test('headDeclaredOf a for-of head `using` is the declared name — R18', () => {
  assert.deepEqual(declaredHead('for (using r of rs) {}'), ['r']);
  assert.deepEqual(declaredHead('for (await using r of rs) {}'), ['r']);
});

test('headDeclaredOf a catch clause is its binding', () => {
  const clause = find(parse('try { r(); } catch (e) {}'), (n) => ts.isCatchClause(n));
  assert.deepEqual(headDeclaredOf(ts, clause), ['e']);
});

// ----------------------------------------------------------------- declaredIn

test('declaredIn a bare block is its own direct declarations', () => {
  assert.deepEqual(declared('{ const y = 1; let z = 2; }'), ['y', 'z']);
});

test('declaredIn lists a direct class and function declaration, block-scoped in a module', () => {
  assert.deepEqual(declared('{ class K {} function g() {} }'), ['K', 'g']);
});

test('declaredIn never lists a `var` — it is function-scoped and never unbound', () => {
  assert.deepEqual(declared('{ var v = 1; const y = 2; }'), ['y']);
});

test('declaredIn lists a `using` declaration — R18, it dies with its block', () => {
  assert.deepEqual(declared('{ using x = f(); const y = 1; }'), ['x', 'y']);
  assert.deepEqual(declared('{ await using x = f(); }'), ['x']);
});

test('declaredIn an if lists both branch blocks', () => {
  assert.deepEqual(declared('if (c) { const y = 1; } else { const w = 2; }'), ['y', 'w']);
});

test('declaredIn an if lists only its DIRECT block — a nested if owns its own', () => {
  assert.deepEqual(declared('if (c) { const y = 1; if (d) { const z = 2; } }'), ['y']);
});

test('declaredIn a guard with a bare body is empty — a bare body declares nothing', () => {
  assert.deepEqual(declared('if (c) x = 1;'), []);
});

test('declaredIn a loop lists its body block and its head declaration', () => {
  assert.deepEqual(declared('for (let i = 0; i < n; i++) { const c = 1; }'), ['c', 'i']);
});

test('declaredIn a for with no body declarations is the head alone', () => {
  assert.deepEqual(declared('for (let i = 0; i < n; i++) {}'), ['i']);
});

test('declaredIn a while is its body block', () => {
  assert.deepEqual(declared('while ((m = re.exec(s)) !== null) { const c = 1; }'), ['c']);
});

test('declaredIn a try lists the try block, the catch binding, the catch block, the finally', () => {
  assert.deepEqual(
    declared('try { const a = 1; } catch (e) { const b = 2; } finally { const c = 3; }'),
    ['a', 'e', 'b', 'c'],
  );
});

test('declaredIn a switch lists a clause\'s DIRECT declarations', () => {
  assert.deepEqual(declared('switch (k) { case 1: const q = 1; break; default: let w = 2; }'),
    ['q', 'w']);
});

test('declaredIn a switch is empty when the inner bare block owns the name', () => {
  assert.deepEqual(declared('switch (k) { case 1: { const q = 1; } }'), []);
});

test('declaredIn a labeled statement is delegated to the statement it labels', () => {
  assert.deepEqual(declared('outer: { const y = 1; }'), ['y']);
  assert.deepEqual(declared('outer: for (const v of xs) { const c = 1; }'), ['c', 'v']);
});

test('declaredIn a statement that is not block-like is empty', () => {
  assert.deepEqual(declared('const y = 1;'), []);
  assert.deepEqual(declared('foo();'), []);
});

// ----------------------------------------------------------------- paramNames

test('paramNames reads every parameter, pattern, default and rest', () => {
  const fn = find(parse('function f(a, {b, c: [d]} = {}, ...rest) {}'),
    (n) => ts.isFunctionDeclaration(n));
  assert.deepEqual(paramNames(ts, fn), ['a', 'b', 'd', 'rest']);
});

test('paramNames skips a TypeScript `this` parameter — `this` is not a parameter', () => {
  const fn = find(parse('function f(this: Fog, a: number) {}'),
    (n) => ts.isFunctionDeclaration(n));
  assert.deepEqual(paramNames(ts, fn), ['a']);
});

test('paramNames of an arrow with no parameters is empty', () => {
  const fn = find(parse('const g = () => 1;'), (n) => ts.isArrowFunction(n));
  assert.deepEqual(paramNames(ts, fn), []);
});
