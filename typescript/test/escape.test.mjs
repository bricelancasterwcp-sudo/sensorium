// The escape rule, one test per row of the table spec §2.1-§2.3 writes down.
// `escape.mjs` holds pure functions over the consumer's own AST, so these tests
// parse a fragment with that TypeScript and ask the function directly — no
// transform, no runtime, no spool. The rule is what decides a `how` word, and a
// `how` word is what the reader turns into SWALLOWED, so every branch is a row
// here before it is a splice anywhere.
import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';

import { callbackHow, catchHow, finallyCompletes } from '../src/escape.mjs';

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

/** @param {string} clause a `catch …` clause, spliced onto a try */
const clauseOf = (clause) =>
  find(parse(`function f() {\n  try {\n    risky();\n  } ${clause}\n}\n`),
    (n) => ts.isCatchClause(n));

/** @param {string} arg the argument of a `.catch(…)` */
const argOf = (arg) =>
  find(parse(`function f() {\n  return risky().catch(${arg});\n}\n`),
    (n) => ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) &&
      n.expression.name.text === 'catch').arguments[0];

/** @param {string} body the statements of a `finally` block */
const finallyOf = (body) =>
  find(parse(`function f() {\n  for (const it of xs) {\n    try {\n      risky();\n    } finally {\n      ${body}\n    }\n  }\n}\n`),
    (n) => ts.isTryStatement(n) && !!n.finallyBlock).finallyBlock;

/**
 * §2.1's table. A binding is `e` throughout; the third column is the `how` the
 * clause is recorded with.
 * @type {[string, string, string][]}
 */
const CATCH_ROWS = [
  ['an empty block is a sink, binding or not', 'catch (e) {}', 'sink_empty_catch'],
  ['a clause with no binding has nothing that can escape', 'catch { report(); }', 'catch'],
  ['a destructuring binding is an escape: the runtime never sees what it bound',
    'catch ({ message }) { report(message); }', 'catch_escaped'],
  ['a body that never mentions the binding swallowed it', 'catch (e) { report(); }', 'catch'],
  ['a bare console argument is a log', 'catch (e) { console.error(e); }', 'catch'],
  ['a template literal in a console argument is a log',
    'catch (e) { console.warn(`failed: ${e}`); }', 'catch'],
  ['a String(e) inside a console argument is a log', 'catch (e) { console.log(String(e)); }', 'catch'],
  ['a property of the binding inside a console argument is a log',
    'catch (e) { console.debug(e.message); }', 'catch'],
  ['every logging member counts', 'catch (e) { console.trace(e); console.info(e); }', 'catch'],
  ['a console member that is not logging is not a log',
    'catch (e) { console.table(e); }', 'catch_escaped'],
  ['returning it escapes', 'catch (e) { return e; }', 'catch_escaped'],
  ['assigning it escapes', 'catch (e) { last = e; }', 'catch_escaped'],
  ['pushing it escapes', 'catch (e) { seen.push(e); }', 'catch_escaped'],
  ['an argument to any non-logging call escapes', 'catch (e) { notify(e); }', 'catch_escaped'],
  ['a rendering of it that goes anywhere else escapes',
    'catch (e) { return String(e); }', 'catch_escaped'],
  ['a closure that captures it escapes, log or no log',
    'catch (e) { queue(() => console.error(e)); }', 'catch_escaped'],
  ['a function body that captures it escapes',
    'catch (e) { register(function () { console.error(e); }); }', 'catch_escaped'],
  ['a shorthand property mentions it', 'catch (e) { report({ e }); }', 'catch_escaped'],
  ['an object key spelled like it does not', 'catch (e) { report({ e: 1 }); }', 'catch'],
  ['a property spelled like it does not', 'catch (e) { report(other.e); }', 'catch'],
  // Ruled 2026-09-10 (Task 6): a BARE rethrow is a traced exit, not an escape.
  // The value reaches nothing, it leaves the way it arrived, and the RAISE the
  // throw writes carries the same serial -- so the rule module reads the pair
  // as a hop and judges the rethrow's own block. Anything BUILT out of the
  // binding is still an escape, and so is a rethrow inside a closure.
  ['a bare rethrow is a traced exit', 'catch (e) { throw e; }', 'catch'],
  ['a parenthesised bare rethrow is one too', 'catch (e) { throw (e); }', 'catch'],
  ['logging then rethrowing is still a traced exit',
    'catch (e) { console.error(e); throw e; }', 'catch'],
  ['a rethrow does not excuse another mention',
    'catch (e) { seen.push(e); throw e; }', 'catch_escaped'],
  ['a wrapped rethrow mentions it', 'catch (e) { throw new Wrapped(e); }', 'catch_escaped'],
  ['throwing a property of it mentions it', 'catch (e) { throw e.cause; }', 'catch_escaped'],
  ['throwing a call on it mentions it', 'catch (e) { throw wrap(e); }', 'catch_escaped'],
  ['a rethrow inside a closure escapes: the closure keeps it',
    'catch (e) { retry(() => { throw e; }); }', 'catch_escaped'],
  ['the callee of a logging call is not its argument', 'catch (e) { console.error(e(1)); }', 'catch'],
];

for (const [name, clause, how] of CATCH_ROWS) {
  test(`catchHow: ${name}`, () => {
    assert.equal(catchHow(ts, clauseOf(clause)), how, clause);
  });
}

/**
 * §2.2's table, over the argument of a `.catch(…)`.
 * @type {[string, string, string][]}
 */
const CALLBACK_ROWS = [
  ['a named handler is opaque: its parameter was never analysed', 'handler', 'catch_callback_opaque'],
  ['a member reference is opaque', 'this.onError', 'catch_callback_opaque'],
  ['a call returning a function is opaque', 'makeHandler(1)', 'catch_callback_opaque'],
  ['an empty arrow is a sink', '() => {}', 'sink_empty_catch_callback'],
  ['an empty arrow with a parameter is still a sink', '(e) => {}', 'sink_empty_catch_callback'],
  ['an empty function expression is a sink too', 'function () {}', 'sink_empty_catch_callback'],
  ['a parameterless body handled it and let nothing out', '() => { report(); }', 'catch_callback'],
  ['a logged parameter is a swallow', '(e) => { console.error(e); }', 'catch_callback'],
  ['a parameter that goes anywhere else escapes', '(e) => { seen.push(e); }', 'catch_callback_escaped'],
  ['a returned parameter escapes', '(e) => { return e; }', 'catch_callback_escaped'],
  ['a destructuring parameter escapes', '({ message }) => { report(message); }', 'catch_callback_escaped'],
  ['an expression body is walked like a block', '(e) => console.warn(e)', 'catch_callback'],
  ['an expression body that escapes escapes', '(e) => e', 'catch_callback_escaped'],
  ['a function expression is read the same way',
    'function (e) { console.error(e); }', 'catch_callback'],
  // Ruled 2026-09-10 (fix round 2): ONE rule, two syntaxes. §2.2 defines the
  // callback word as §2.1's rule applied to the parameter, and a rethrow from a
  // handler carries the serial exactly as a clause's does -- so the bare-rethrow
  // exclusion holds here too, in both spellings, and nowhere else moves.
  ['a bare rethrow is a traced exit, arrow spelling',
    '(e) => { throw e; }', 'catch_callback'],
  ['a bare rethrow is a traced exit, function spelling',
    'function (e) { throw e; }', 'catch_callback'],
  ['logging then rethrowing is still a traced exit',
    '(e) => { console.error(e); throw e; }', 'catch_callback'],
  ['a rethrow does not excuse another mention',
    '(e) => { seen.push(e); throw e; }', 'catch_callback_escaped'],
  ['a wrapped rethrow mentions it', '(e) => { throw wrap(e); }', 'catch_callback_escaped'],
  ['a rethrow inside a closure escapes: the closure keeps it',
    'function (e) { retry(() => { throw e; }); }', 'catch_callback_escaped'],
];

for (const [name, arg, how] of CALLBACK_ROWS) {
  test(`callbackHow: ${name}`, () => {
    assert.equal(callbackHow(ts, argOf(arg)), how, arg);
  });
}

/**
 * §2.3's rule as this rung reads it: `return` at closure depth 0 anywhere in the
 * block; `break` and `continue` only where nothing inside the block catches them.
 * @type {[string, string, boolean][]}
 */
const FINALLY_ROWS = [
  ['a return completes', 'return 1;', true],
  ['a return inside an if completes', 'if (x) { return 1; }', true],
  ['a break that leaves the block completes', 'break;', true],
  ['a continue that leaves the block completes', 'continue;', true],
  ['a block with no completion statement discards nothing', 'cleanup();', false],
  ['a return inside a nested function is that function\'s, not the block\'s',
    'queue(() => { return 1; });', false],
  ['a return inside a function expression is not the block\'s',
    'register(function () { return 1; });', false],
  ['a break its own loop catches discards nothing', 'for (const y of ys) { break; }', false],
  ['a continue its own loop catches discards nothing', 'while (x) { continue; }', false],
  ['a break its own switch catches discards nothing', 'switch (x) { case 1: break; }', false],
  ['a return beside a caught break still completes', 'for (const y of ys) { break; }\n      return 2;',
    true],
];

for (const [name, body, want] of FINALLY_ROWS) {
  test(`finallyCompletes: ${name}`, () => {
    assert.equal(finallyCompletes(ts, finallyOf(body)), want, body);
  });
}
