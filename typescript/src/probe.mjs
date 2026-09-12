// The focus tier's splices: the rows a FOCUSED function's body writes as it
// runs. `transform.mjs`'s visitor calls `spliceFocused` for every node inside
// such a function, and this module decides what — if anything — that node owes
// the record (spec §3.1–§3.4).
//
// Three splices, and nothing else:
//   * a STATEMENT ROW after every statement that completes normally, carrying
//     the names it wrote (`writesOf`) and the block-scoped names that died with
//     it (`declaredIn`);
//   * a HEAD ROW as the first statement inside a guard's body, carrying the
//     names the guard bound as it entered (`headBindingsOf`) — once per entry
//     or iteration;
//   * a WRAP, `{…}`, around a guard body written without braces, so the body's
//     own row runs only when the body does (plan P2: appended after a bare
//     body, a probe would run unconditionally — Rust's A1, transferred).
//
// It owns no name rules: `bindings.mjs` answers every "which names" question
// and this file only asks. It owns no positions either — `lineOf` and
// `terminatorFor` are `transform.mjs`'s. That import is a cycle, and a safe
// one: both are hoisted function declarations, called during a transform and
// never while either module is being evaluated.
//
// Two orderings the whole file rests on, both measured (see the tests):
//   * `prependRight` renders EARLIER-registered content to the RIGHT of later
//     content at one offset. So a statement's row is registered BEFORE the
//     statement's children are visited (plan P3) — a descendant's closer
//     (`await p` as a whole statement: the suspension rewrite's `),0))`) then
//     lands INSIDE the probe rather than after it — and a guard's own row is
//     registered before its body's wrap, so at the one offset where a guard,
//     its wrap and its last statement all end, the output reads
//     `stmt;<stmt row>}<guard row>`.
//   * `appendLeft` renders in registration order, so a `catch` clause's head
//     row follows the HANDLED that `spliceCatch` registered first.
import {
  declaredIn,
  headBindingsOf,
  isStatementPosition,
  writesOf,
} from './bindings.mjs';
import { lineOf, terminatorFor } from './transform.mjs';

/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').Statement} Statement */
/** @typedef {import('./transform.mjs').Splicer} Splicer */

/**
 * A `[name, value, …]` argument list, spelled for the runtime: the names are
 * the transform's own (JSON strings) and the values are the program's own
 * identifiers, read where the splice stands.
 * @param {string[]} names
 * @returns {string} the list's contents, without its brackets
 */
export function pairsOf(names) {
  return names.flatMap((name) => [JSON.stringify(name), name]).join(',');
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean} whether the node is a guard that binds on entry: the six
 *   with a body this recorder wraps. A `LabeledStatement` is NOT one (R15):
 *   wrapping a labeled loop in a block turns `continue label` into a syntax
 *   error, and a labeled body that is itself a guard is spliced as that guard
 *   when the visitor reaches it.
 */
function isGuard(ts, node) {
  return (
    ts.isIfStatement(node) ||
    ts.isForStatement(node) ||
    ts.isForInStatement(node) ||
    ts.isForOfStatement(node) ||
    ts.isWhileStatement(node) ||
    ts.isDoStatement(node)
  );
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean} whether the node carries a `declare` modifier of its own
 */
function isDeclared(ts, node) {
  const modifiers = /** @type {{modifiers?: readonly import('typescript').ModifierLike[]}} */ (
    node
  ).modifiers;
  return !!modifiers && modifiers.some((m) => m.kind === ts.SyntaxKind.DeclareKeyword);
}

/**
 * Whether a node is a guard's BLOCK body, whose completion is the guard's own.
 *
 * Such a block mints no row: the guard's row is minted at the same moment and
 * `declaredIn` already reports the block's dead names on it, so a second row
 * would report one completion twice and pop the same names twice. A bare body
 * is different — it is an ordinary statement inside the block this recorder
 * synthesised, and it keeps its row.
 *
 * A LABELED body is not one either: the label mints nothing of its own (R16),
 * so its body statement must.
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean}
 */
function isGuardBody(ts, node) {
  const parent = node.parent;
  if (!ts.isBlock(node) || !parent) return false;
  if (ts.isIfStatement(parent)) {
    return parent.thenStatement === node || parent.elseStatement === node;
  }
  return isGuard(ts, parent) &&
    /** @type {{statement?: Node}} */ (parent).statement === node;
}

/**
 * Whether a node in statement position owes the record a row of its own.
 *
 * The completions mint none: `return`, `throw`, `break` and `continue` never
 * complete normally, and each one's exit is already the RETURN, the UNWIND or
 * the enclosing statement's row (spec §3.1). A `FunctionDeclaration` is hoisted
 * and executes nowhere in particular. An `EmptyStatement` is not a statement
 * anybody wrote. A `LabeledStatement` is a label, not a step (R16).
 *
 * The type-only three mint none either (R17): an interface, a type alias and
 * anything `declare`d are ERASED before the program runs, so a row for one
 * would name a line that never ran. An `enum` and a `class` are not erased —
 * they execute where they stand — and both keep their row.
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean}
 */
function mintsRow(ts, node) {
  if (
    ts.isReturnStatement(node) ||
    ts.isThrowStatement(node) ||
    ts.isBreakStatement(node) ||
    ts.isContinueStatement(node) ||
    ts.isFunctionDeclaration(node) ||
    ts.isEmptyStatement(node) ||
    ts.isLabeledStatement(node) ||
    ts.isInterfaceDeclaration(node) ||
    ts.isTypeAliasDeclaration(node) ||
    isDeclared(ts, node)
  ) {
    return false;
  }
  return !isGuardBody(ts, node);
}

/**
 * One completed statement's row, after the statement (spec §3.1).
 *
 * It carries the semicolon the source left to ASI when the statement has none
 * of its own — a block-like statement ends in `}`, and `}__srt.line(…)` would
 * be read as a call on whatever the block produced.
 * @param {Splicer} ctx
 * @param {Node} node a node in statement position that mints a row
 * @returns {void}
 */
function spliceStatement(ctx, node) {
  const { ts, sf, s } = ctx;
  const line = lineOf(sf, node.getStart(sf));
  const deltas = pairsOf(writesOf(ts, node));
  const gone = declaredIn(ts, node);
  const tail = gone.length > 0 ? `,${JSON.stringify(gone)}` : '';
  s.prependRight(node.end, `${terminatorFor(ctx, node)}__srt.line(__sf,${line},[${deltas}]${tail});`);
}

/**
 * A guard's body: the head row inside it, and the braces a bare one needs.
 * @param {Splicer} ctx
 * @param {Node} body the body statement
 * @param {string} headRow the row to open the body with, or '' for none
 * @returns {void}
 */
function spliceBody(ctx, body, headRow) {
  const { ts, sf, s } = ctx;
  if (ts.isBlock(body)) {
    if (headRow !== '') s.appendLeft(body.getStart(sf) + 1, headRow);
    return;
  }
  // Registered BEFORE the body is visited, so the body's own row renders
  // inside these braces rather than after them.
  s.appendLeft(body.getStart(sf), `{${headRow}`);
  s.prependRight(body.end, '}');
}

/**
 * A guard's head row, and its bodies.
 *
 * The head row goes into the bodies a guard ENTERS: an `if`'s then-branch and a
 * loop's body. An `else` branch is not an entry (spec §3.2) — a falsy test
 * bound nothing, and what its head WROTE is on the `if`'s own completion row
 * instead (plan P1) — so it is wrapped like any other body and given no row.
 * A `switch` has no body to enter and no head row at all (spec §3.2, §3.9).
 * @param {Splicer} ctx
 * @param {Node} node a guard
 * @returns {void}
 */
function spliceGuard(ctx, node) {
  const { ts, sf } = ctx;
  const heads = headBindingsOf(ts, node);
  const headRow = heads.length > 0
    ? `__srt.line(__sf,${lineOf(sf, node.getStart(sf))},[${pairsOf(heads)}]);`
    : '';
  if (ts.isIfStatement(node)) {
    spliceBody(ctx, node.thenStatement, headRow);
    if (node.elseStatement) spliceBody(ctx, node.elseStatement, '');
    return;
  }
  spliceBody(ctx, /** @type {{statement: Statement}} */ (/** @type {unknown} */ (node)).statement,
    headRow);
}

/**
 * A `catch` clause's binding, as the body's first row.
 *
 * It follows the HANDLED `spliceCatch` registered on the same offset — the
 * visitor reaches the clause's own splice first, and `appendLeft` renders in
 * registration order. A clause with no binding has nothing to report: the
 * runtime's own `__sce` is not a name the program wrote.
 * @param {Splicer} ctx
 * @param {import('typescript').CatchClause} node
 * @returns {void}
 */
function spliceCatchHead(ctx, node) {
  const { ts, sf, s } = ctx;
  const heads = headBindingsOf(ts, node);
  if (heads.length === 0) return;
  const line = lineOf(sf, node.getStart(sf));
  s.appendLeft(node.block.getStart(sf) + 1, `__srt.line(__sf,${line},[${pairsOf(heads)}]);`);
}

/**
 * Every splice a node inside a focused function owes, in the one order the
 * offsets allow: the node's own row FIRST, then its bodies. A guard and its
 * last statement can end on the same offset, and the row registered first is
 * the one rendered last — which is what puts the guard's row outside the brace
 * its wrap closes.
 * @param {Splicer} ctx
 * @param {Node} node a node whose enclosing frame is focused
 * @returns {void}
 */
export function spliceFocused(ctx, node) {
  const { ts } = ctx;
  if (ts.isCatchClause(node)) {
    spliceCatchHead(ctx, node);
    return;
  }
  if (isStatementPosition(ts, node) && mintsRow(ts, node)) spliceStatement(ctx, node);
  if (isGuard(ts, node)) spliceGuard(ctx, node);
}
