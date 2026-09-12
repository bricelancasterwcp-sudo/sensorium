// The test-file rule and the task boundary. Split out of `transform.mjs`
// 2026-09-11 (S5 rung 4) because that file reached 765 lines against the
// repo-wide 800-line ceiling; every line below the imports is the line that
// was there, moved and not rewritten.
//
// What lives here is one question and one splice: whether a file holds tests
// (R8, R8b) — the answer the whole test/suite wrap is gated on — and the splice
// that hands a `test`/`describe` call's title and callback to the runtime
// (R8a, R8c), with the two callee sets and the two helpers only those need.
//
// The JSDoc `import('./transform.mjs')` below is a TYPE reference and emits no
// runtime import, so `transform.mjs` importing this module is not a cycle;
// were it one it would still be safe, since both modules only define.
import path from 'node:path';

/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').SourceFile} SourceFile */
/** @typedef {import('./transform.mjs').Splicer} Splicer */

/** A file whose name says it holds tests, whatever it imports. */
const TEST_FILE = /\.(test|spec)\.[cm]?[jt]sx?$/;
/** A file that imports one of these holds tests, whatever it is named. */
const HARNESS_MODULES = new Set(['vitest', 'node:test', '@jest/globals']);

const TASK_CALLEES = new Set(['test', 'it']);
const SUITE_CALLEES = new Set(['describe', 'suite']);

/**
 * A type-only import brings no `test` to call: `import type { Mock } from
 * 'vitest'`, or a clause whose every specifier is `type`-qualified, does not
 * make a test file (R8b). A bare `import 'vitest'` does — it runs the harness.
 * @param {TS} ts
 * @param {import('typescript').ImportDeclaration} node
 * @returns {boolean}
 */
function isTypeOnlyImport(ts, node) {
  const clause = node.importClause;
  if (!clause) return false;
  if (clause.isTypeOnly) return true;
  const bindings = clause.namedBindings;
  if (!clause.name && bindings && ts.isNamedImports(bindings) && bindings.elements.length > 0) {
    return bindings.elements.every((element) => element.isTypeOnly);
  }
  return false;
}

/**
 * Whether this file holds tests. The test/suite wrap applies here and nowhere
 * else: `test`, `it`, `describe` and `suite` are ordinary identifiers, and a
 * consumer may own them — the lens does, a local `describe(label, formula,
 * value)` in `src/lib/combat/attackRoll.ts`. Rewriting that call would change
 * what the program does, which is the one thing this recorder may never do.
 * Inside a test file the rule is the opposite: every second argument is wrapped,
 * an identifier included, so no task boundary goes missing (controller R8).
 * @param {TS} ts
 * @param {SourceFile} sf
 * @param {string} filePath
 * @returns {boolean}
 */
export function isTestFile(ts, sf, filePath) {
  if (TEST_FILE.test(path.basename(filePath))) return true;
  let found = false;
  /** @param {Node} node */
  const visit = (node) => {
    if (found) return;
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier) &&
        HARNESS_MODULES.has(node.moduleSpecifier.text) && !isTypeOnlyImport(ts, node)) {
      found = true;
      return;
    }
    if (ts.isCallExpression(node) && node.arguments.length > 0 &&
        ts.isStringLiteral(node.arguments[0]) &&
        HARNESS_MODULES.has(node.arguments[0].text) &&
        (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
          (ts.isIdentifier(node.expression) && node.expression.text === 'require'))) {
      found = true;
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return found;
}

/**
 * The identifier chain of a call's callee — `test.each(table)` is
 * `['test', 'each']` — or null when it is not rooted at a plain identifier.
 * @param {TS} ts
 * @param {import('typescript').Expression} callee
 * @returns {string[]|null}
 */
function calleeChain(ts, callee) {
  /** @type {string[]} */
  const chain = [];
  let cur = callee;
  for (;;) {
    if (ts.isCallExpression(cur)) { cur = cur.expression; continue; }
    if (ts.isTaggedTemplateExpression(cur)) { cur = cur.tag; continue; }
    if (ts.isPropertyAccessExpression(cur)) {
      chain.unshift(cur.name.text);
      cur = cur.expression;
      continue;
    }
    if (ts.isIdentifier(cur)) { chain.unshift(cur.text); return chain; }
    return null;
  }
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean} whether a test title is a literal string in the source
 */
function isLiteralTitle(ts, node) {
  return ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node);
}

/**
 * A test or a suite: the title and the callback are handed to the runtime as the
 * call's own argument list, and every other argument stays exactly where the
 * source put it — nothing is moved, so nothing carries a line, or a closing
 * splice, to a place it does not belong (R8c).
 *
 * The rule is file-scoped (R8, `isTestFile`). Inside a test file the callback
 * argument is wrapped whatever its shape — a bare identifier included, which the
 * runtime passes through unchanged — so no task boundary goes missing; outside
 * one, nothing is wrapped, so a consumer's own `describe` is never rewritten.
 *
 * vitest also documents an options signature, `test(name, options, fn)`, where
 * the second argument is not the callback (R8a). The callback is then the third,
 * and the options simply stay between them:
 *
 *   test("x", {timeout: 100}, fn, 5000)
 *     -> test(...__srt.task(("x"), {timeout: 100}, fn,1), 5000)
 *   describe("y", {concurrent: true}, fn, 1000)
 *     -> describe(...__srt.suite(("y"), {concurrent: true}, fn), 1000)
 *   test("x", fn)     -> test(...__srt.task(("x"),fn,1))
 *   describe("x", fn) -> describe(...__srt.suite(("x"),fn))
 *
 * The runtime contract that pairs with it (Task 3) reads the argument list from
 * the end: `task(title, ...rest)` with `rest = [...between, fn, flags]` — flags
 * is always the last element and the callback the one before it — and
 * `suite(title, ...rest)` with `rest = [...between, fn]`. Both return
 * `[title, ...between, wrapped]`.
 *
 * Both closing insertions are `prependRight`, and both are registered here,
 * before the call's own children are visited. `prependRight` renders in reverse
 * registration order, so ours end up outermost and a closer a descendant puts on
 * the same offset — an arrow title's, a conditional callback's, an `await`'s —
 * is spliced inside ours rather than around it.
 * @param {Splicer} ctx
 * @param {import('typescript').CallExpression} node
 */
export function spliceTaskBoundary(ctx, node) {
  const { ts, sf, s } = ctx;
  if (!ctx.isTestFile || node.arguments.length < 2) return;
  const chain = calleeChain(ts, node.expression);
  if (!chain) return;
  const isTask = TASK_CALLEES.has(chain[0]);
  if (!isTask && !SUITE_CALLEES.has(chain[0])) return;

  const title = node.arguments[0];
  const hasOptions = ts.isObjectLiteralExpression(node.arguments[1]);
  // `test(name, options)` names no callback at all: it is not a task.
  if (hasOptions && node.arguments.length < 3) return;
  const fn = node.arguments[hasOptions ? 2 : 1];

  const flags = isTask
    ? `,${(isLiteralTitle(ts, title) ? 1 : 0) | (chain.includes('each') ? 2 : 0)}`
    : '';
  s.appendLeft(title.getStart(sf), `...__srt.${isTask ? 'task' : 'suite'}((`);
  s.prependRight(title.end, ')');
  s.prependRight(fn.end, `${flags})`);
}
