// The rewriter. Source text + path + root in; edited text, a source map and a
// per-file manifest out. Nothing here runs the program and nothing here does I/O.
//
// Two properties the whole recorder rests on:
//   * NO edit contains a newline, so every line of the output is the same line
//     of the input and `firstlineno` is the line a human sees (design §3).
//   * Positions come from the consumer's own TypeScript AST, and edits are
//     magic-string splices: closing insertions that land on one offset are made
//     with `prependRight`, which orders them innermost-first.
import crypto from 'node:crypto';
import path from 'node:path';

import MagicString from 'magic-string';

import { paramNames } from './bindings.mjs';
import { callbackHow, catchHow, finallyCompletes } from './escape.mjs';
import { specMatches } from './focus.mjs';
// `probe.mjs` imports `lineOf` and `terminatorFor` back out of this module. The
// cycle is deliberate and safe: both are hoisted function declarations, so the
// binding exists before either module's body runs, and neither is called until
// a transform is under way.
import { pairsOf, spliceFocused } from './probe.mjs';
import { qualnameFor } from './qualname.mjs';
// `tasks.mjs` names nothing of ours at runtime — only the `Splicer` type, in
// JSDoc — so this edge is one-way; either way both modules only define.
import { isTestFile, spliceTaskBoundary } from './tasks.mjs';

/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').SourceFile} SourceFile */
/** @typedef {import('typescript').FunctionLikeDeclaration} FunctionLike */
/** @typedef {'function'|'coroutine'|'generator'|'async_generator'} FrameKind */
/** @typedef {{qualname: string, line: number, kind: FrameKind, focused: boolean}} Site */
/** @typedef {{qualname: string, line: number, reason: string}} ExcludedSite */
/** @typedef {{file: string, rel: string, sha256: string, instrumented: Site[], focused: string[], excluded: Record<string, number>, diagnostics?: string[]}} Manifest */

/** Extensions the recorder can instrument; CommonJS is counted, never transformed. */
const ELIGIBLE = new Set(['.ts', '.tsx', '.mts', '.js', '.jsx', '.mjs']);
const COMMONJS = new Set(['.cjs', '.cts']);
const DECLARATION = /\.d\.[cm]?ts$/;

/** `vi.*` calls vitest hoists above every import, our header included. */
const HOISTED_VI = new Set(['mock', 'doMock', 'hoisted', 'unmock']);

/** Suspension kinds on the wire: `await` parks a coroutine, `yield` a generator. */
const AWAIT = 0;
const YIELD = 1;

const CLOSE_BLOCK = ';__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}';
/**
 * A generator's close (R40). A consumer that abandons a generator — `break` out
 * of a `for…of`, an explicit `.return()` — resumes the body at its `yield` with
 * a RETURN completion: the `ret` above never runs and the `catch` never fires,
 * so only a `finally` can see it. `gclose` is a no-op on a frame either of the
 * other two already closed.
 */
const CLOSE_BLOCK_GEN = `${CLOSE_BLOCK}finally{__srt.gclose(__sf)}`;
/** The two frame kinds whose bodies a consumer can close from outside. */
const GENERATORS = new Set(['generator', 'async_generator']);
const CLOSE_EXPRESSION = '))}catch(__se){__srt.thr(__sf,__se);throw __se}}';

/**
 * Whether a file is transformed, skipped outright, or skipped but counted.
 *
 * `commonjs` is the one exclusion the per-file manifest cannot carry — the file
 * has no manifest, because it is never parsed — so the caller (the vite plugin)
 * tallies it into the run's `transform_excluded` from this verdict.
 * @param {string} filePath absolute path to the file
 * @param {string} root absolute path to the invocation root
 * @returns {'transform'|'skip'|'commonjs'}
 */
export function classify(filePath, root) {
  const rel = path.relative(root, filePath);
  if (rel === '' || rel.startsWith('..') || path.isAbsolute(rel)) return 'skip';
  if (rel.split(path.sep).includes('node_modules')) return 'skip';
  if (DECLARATION.test(filePath)) return 'skip';
  const ext = path.extname(filePath);
  if (COMMONJS.has(ext)) return 'commonjs';
  return ELIGIBLE.has(ext) ? 'transform' : 'skip';
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {node is FunctionLike}
 */
function isFunctionLike(ts, node) {
  return (
    ts.isFunctionDeclaration(node) ||
    ts.isFunctionExpression(node) ||
    ts.isArrowFunction(node) ||
    ts.isMethodDeclaration(node) ||
    ts.isConstructorDeclaration(node) ||
    ts.isGetAccessorDeclaration(node) ||
    ts.isSetAccessorDeclaration(node)
  );
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @param {import('typescript').SyntaxKind} kind
 * @returns {boolean}
 */
function hasModifier(ts, node, kind) {
  const modifiers = /** @type {{modifiers?: readonly import('typescript').ModifierLike[]}} */ (node)
    .modifiers;
  return !!modifiers && modifiers.some((m) => m.kind === kind);
}

/**
 * @param {TS} ts
 * @param {FunctionLike} node
 * @returns {FrameKind} the contract's frame kind
 */
function frameKind(ts, node) {
  const isAsync = hasModifier(ts, node, ts.SyntaxKind.AsyncKeyword);
  const isGenerator = !!(/** @type {{asteriskToken?: Node}} */ (node).asteriskToken);
  if (isAsync && isGenerator) return 'async_generator';
  if (isAsync) return 'coroutine';
  if (isGenerator) return 'generator';
  return 'function';
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean} whether the node sits in a `declare`d context
 */
function isAmbient(ts, node) {
  /** @type {Node|undefined} */
  let cur = node;
  while (cur) {
    if (hasModifier(ts, cur, ts.SyntaxKind.DeclareKeyword)) return true;
    cur = cur.parent;
  }
  return false;
}

/**
 * Why a function with no body is not instrumented. Each reason is named so the
 * count in the trace is a number, not a hope.
 * @param {TS} ts
 * @param {FunctionLike} node
 * @returns {string}
 */
function bodilessReason(ts, node) {
  if (isAmbient(ts, node)) return 'ambient';
  if (hasModifier(ts, node, ts.SyntaxKind.AbstractKeyword)) return 'abstract';
  return 'overload-signature';
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean} whether the node is a `vi.mock`/`doMock`/`hoisted`/`unmock` call
 */
function isHoistedCall(ts, node) {
  return (
    ts.isCallExpression(node) &&
    ts.isPropertyAccessExpression(node.expression) &&
    ts.isIdentifier(node.expression.expression) &&
    node.expression.expression.text === 'vi' &&
    HOISTED_VI.has(node.expression.name.text)
  );
}

/**
 * @param {SourceFile} sf
 * @param {number} pos
 * @returns {number} the 1-based line
 */
export function lineOf(sf, pos) {
  return sf.getLineAndCharacterOfPosition(pos).line + 1;
}

/**
 * Pass one: number every function-like in source order, decide eligibility,
 * name every one of them (an excluded function still needs a name, because a
 * function nested inside it is named against it), and mark the ones a focus
 * selected.
 *
 * Only an INSTRUMENTED function can be focused: an excluded one opens no frame,
 * so there is nothing for a statement of it to be a statement OF.
 * @param {TS} ts
 * @param {SourceFile} sf
 * @param {string} rel the root-relative path a spec's file part is matched on
 * @param {string[]} focus the specs, `[]` for no focus at all
 * @returns {{sites: Site[], indexOf: Map<Node, number>, focused: Set<Node>,
 *   excluded: Record<string, number>, excludedSites: ExcludedSite[]}}
 *   `excluded` COUNTS the exclusions and is what a manifest carries;
 *   `excludedSites` NAMES them, one entry each, and is for the resolver
 *   (R26), which has to tell a spec that matched nothing from a spec that
 *   matched only functions this recorder never instruments.
 */
function planSites(ts, sf, rel, focus) {
  /** @type {Site[]} */
  const sites = [];
  /** @type {Map<Node, number>} */
  const indexOf = new Map();
  /** @type {Set<Node>} */
  const focused = new Set();
  /** @type {Map<Node, string>} */
  const qualnames = new Map();
  /** @type {Record<string, number>} */
  const excluded = {};
  /** @type {ExcludedSite[]} */
  const excludedSites = [];
  let hoistedDepth = 0;

  /**
   * @param {Node} node the function-like this recorder is not instrumenting
   * @param {string} reason
   */
  const exclude = (node, reason) => {
    excluded[reason] = (excluded[reason] ?? 0) + 1;
    excludedSites.push({
      qualname: /** @type {string} */ (qualnames.get(node)),
      line: lineOf(sf, node.getStart(sf)),
      reason,
    });
  };

  /** @param {Node} node */
  const visit = (node) => {
    if (isHoistedCall(ts, node)) {
      hoistedDepth += 1;
      ts.forEachChild(node, visit);
      hoistedDepth -= 1;
      return;
    }
    if (isFunctionLike(ts, node)) {
      qualnames.set(node, qualnameFor(ts, node, qualnames));
      if (hoistedDepth > 0) exclude(node, 'vitest-hoisted-factory');
      else if (!node.body) exclude(node, bodilessReason(ts, node));
      else {
        const qualname = /** @type {string} */ (qualnames.get(node));
        const selected = focus.some((spec) => specMatches(spec, rel, qualname));
        if (selected) focused.add(node);
        indexOf.set(node, sites.length);
        sites.push({
          qualname,
          line: lineOf(sf, node.getStart(sf)),
          kind: frameKind(ts, node),
          focused: selected,
        });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { sites, indexOf, focused, excluded, excludedSites };
}

/**
 * The state pass two threads through every splice: the consumer's TypeScript,
 * the parsed file, the edit buffer, which function-likes are recorded, and
 * which of those the focus selected.
 * @typedef {{ts: TS, sf: SourceFile, s: MagicString, indexOf: Map<Node, number>, focused: Set<Node>, isTestFile: boolean}} Splicer
 */

/**
 * @param {Splicer} ctx
 * @param {Node} node
 * @returns {boolean} whether the node sits inside a recorded frame
 */
function isRecorded(ctx, node) {
  let parent = node.parent;
  while (parent) {
    if (isFunctionLike(ctx.ts, parent)) return ctx.indexOf.has(parent);
    parent = parent.parent;
  }
  return false;
}

/**
 * @param {Splicer} ctx
 * @param {Node} node
 * @returns {string} the frame variable, spelled `null` outside every frame
 */
function frameVar(ctx, node) {
  return isRecorded(ctx, node) ? '__sf' : 'null';
}

/**
 * Whether the node sits inside a FOCUSED frame — the nearest function-like
 * above it is one the focus selected. Every statement of such a frame owes the
 * record a row; a statement of a nested function that the focus did not reach
 * is that function's business, not this one's (spec §3.1).
 * @param {Splicer} ctx
 * @param {Node} node
 * @returns {boolean}
 */
function isFocusedFrame(ctx, node) {
  let parent = node.parent;
  while (parent) {
    if (isFunctionLike(ctx.ts, parent)) return ctx.focused.has(parent);
    parent = parent.parent;
  }
  return false;
}

/**
 * The frame's entry, and — on a focused site only — the arguments it was
 * entered with, read at body entry so a default is the value the body saw
 * (spec §3.3). An unfocused site passes no third argument at all, which is why
 * an unfocused file's output is byte-identical to 0.2.0's.
 * @param {Splicer} ctx
 * @param {FunctionLike} node a recorded function-like
 */
function spliceFunction(ctx, node) {
  const { ts, sf, s } = ctx;
  const index = ctx.indexOf.get(node);
  const args = ctx.focused.has(node) ? `,[${pairsOf(paramNames(ts, node))}]` : '';
  const body = /** @type {import('typescript').Block|import('typescript').Expression} */ (
    node.body
  );
  if (ts.isBlock(body)) {
    s.appendLeft(body.getStart(sf) + 1, `const __sf=__srt.call(__sfile,${index}${args});try{`);
    // Only a generator gets the `finally`: nothing else can be resumed with a
    // completion its own body did not choose, and an extra clause on every
    // function would be an edit with no fact behind it.
    s.prependRight(body.end - 1,
      GENERATORS.has(frameKind(ts, node)) ? CLOSE_BLOCK_GEN : CLOSE_BLOCK);
    return;
  }
  s.appendLeft(
    body.getStart(sf),
    `{const __sf=__srt.call(__sfile,${index}${args});try{return __srt.ret(__sf,(`,
  );
  s.prependRight(body.end, CLOSE_EXPRESSION);
}

/**
 * A bare `return` or `yield` that ASI terminated is now an expression, and the
 * next line would join it: `return\n(g)()` would call our `ret(...)` result
 * instead of returning. A statement-level one is given the semicolon the source
 * left to ASI — always legal there, and never inserted twice (R12).
 * @param {Splicer} ctx
 * @param {Node} statement the whole statement the splice terminates
 * @returns {string} `';'` when the statement has none of its own
 */
export function terminatorFor(ctx, statement) {
  return ctx.sf.text[statement.end - 1] === ';' ? '' : ';';
}

/**
 * @param {Splicer} ctx
 * @param {import('typescript').ReturnStatement} node
 */
function spliceReturn(ctx, node) {
  const { sf, s } = ctx;
  if (!isRecorded(ctx, node)) return;
  if (!node.expression) {
    const end = terminatorFor(ctx, node);
    s.appendLeft(node.getStart(sf) + 'return'.length, ` __srt.ret(__sf,undefined)${end}`);
    return;
  }
  s.appendLeft(node.expression.getStart(sf), '__srt.ret(__sf,(');
  s.prependRight(node.expression.end, '))');
}

/**
 * `await X` and `yield X` take one form: the value flows out through `y` and
 * back in through `r`, so the runtime can pop the frame while it is parked.
 * @param {Splicer} ctx
 * @param {import('typescript').AwaitExpression|import('typescript').YieldExpression} node
 * @param {number} kind
 * @param {string} keyword
 */
function spliceSuspension(ctx, node, kind, keyword) {
  const { ts, sf, s } = ctx;
  if (!isRecorded(ctx, node)) return;
  s.appendLeft(node.getStart(sf), '__srt.r(__sf,');
  if (!node.expression) {
    // Only a whole statement may take a terminator; a nested `yield` may not.
    const parent = node.parent;
    const end = ts.isExpressionStatement(parent) && parent.expression === node
      ? terminatorFor(ctx, parent)
      : '';
    s.appendLeft(node.getStart(sf) + keyword.length, ` __srt.y(__sf,(undefined),${kind}))${end}`);
    return;
  }
  s.appendLeft(node.expression.getStart(sf), '__srt.y(__sf,(');
  s.prependRight(node.expression.end, `),${kind}))`);
}

/**
 * @param {Splicer} ctx
 * @param {import('typescript').ThrowStatement} node
 */
function spliceThrow(ctx, node) {
  const { sf, s } = ctx;
  const line = lineOf(sf, node.getStart(sf));
  s.appendLeft(node.expression.getStart(sf), `__srt.raise(${frameVar(ctx, node)},(`);
  s.prependRight(node.expression.end, `),${line})`);
}

/**
 * A `catch` clause records a HANDLED as its first statement; a clause with no
 * binding is given one, and an empty block is a sink, not a silence. The `how`
 * word is the escape rule's verdict about what the body did with the binding
 * (`escape.mjs`, spec §2.1) — the record says whether the failure got out, not
 * merely that something caught it.
 * @param {Splicer} ctx
 * @param {import('typescript').CatchClause} node
 */
function spliceCatch(ctx, node) {
  const { ts, sf, s } = ctx;
  const line = lineOf(sf, node.getStart(sf));
  const how = `"${catchHow(ts, node)}"`;
  const open = node.block.getStart(sf) + 1;
  const declared = node.variableDeclaration;
  if (!declared) {
    s.appendLeft(node.getStart(sf) + 'catch'.length, '(__sce)');
    s.appendLeft(open, `__srt.handled(${frameVar(ctx, node)},__sce,${line},${how});`);
    return;
  }
  // A destructuring binding has no name to hand back; the HANDLED is recorded
  // without the object rather than guessed at.
  const bound = ts.isIdentifier(declared.name) ? declared.name.text : 'undefined';
  s.appendLeft(open, `__srt.handled(${frameVar(ctx, node)},${bound},${line},${how});`);
}

/**
 * A rejection handler — `p.catch(<arg>)` or the second argument of
 * `p.then(<x>, <arg>)` — wrapped so the reason it is given is recorded before it
 * runs (spec §2.2). `p.catch()` with no argument, `.then(x)` with one and
 * `.finally(fn)` are not handlers and are not touched (P4).
 *
 * The `how` word is the splice's own verdict about the handler's SHAPE, decided
 * here and written down by the runtime unexamined. The argument is wrapped in
 * parentheses of its own so that whatever expression it is — an arrow, a
 * conditional, an `await` — arrives at `catchCb` as exactly one argument, and so
 * that a closer a descendant registers on the same offset lands inside ours.
 *
 * A call holding a SPREAD argument is left alone entirely. `...args` is not an
 * expression and cannot be parenthesised, so wrapping it produces source the
 * consumer's own parser rejects — the recorder breaking the program it observes
 * — and a spread also hides which argument the handler even IS: `p.then(...a)`
 * may carry two, and `p.then(...a, b)`'s `b` may be the third. One argument the
 * splice cannot read is enough to leave the whole call to the program.
 * @param {Splicer} ctx
 * @param {import('typescript').CallExpression} node
 * @returns {boolean} whether this call was a rejection handler
 */
function spliceRejectionCallback(ctx, node) {
  const { ts, sf, s } = ctx;
  const callee = node.expression;
  if (!ts.isPropertyAccessExpression(callee)) return false;
  if (node.arguments.some((a) => ts.isSpreadElement(a))) return false;
  const name = callee.name.text;
  const arg = name === 'catch' && node.arguments.length === 1
    ? node.arguments[0]
    : name === 'then' && node.arguments.length === 2
      ? node.arguments[1]
      : null;
  if (!arg) return false;
  const line = lineOf(sf, callee.name.getStart(sf));
  const how = callbackHow(ts, arg);
  s.appendLeft(arg.getStart(sf), `__srt.catchCb(${frameVar(ctx, node)},${line},"${how}",(`);
  s.prependRight(arg.end, '))');
  return true;
}

/**
 * A `finally` block that COMPLETES — `return`, `break` or `continue` at closure
 * depth 0 — discards whatever was travelling through the frame, so it is a sink
 * and gains `handledFinally` as its first statement (spec §2.3).
 *
 * A `try` with no `catch` of its own also gains one: `catch(__sfe){mark;throw}`
 * spliced before the `finally` keyword, which is how a library's throw and an
 * awaited rejection — neither of them a `throw` statement this recorder saw —
 * reach the frame's mark (P1). It rethrows the very value it caught, so the
 * program's control flow, and the `finally`'s own precedence over it, are
 * unchanged. A `try` with a `catch` needs none: that clause's HANDLED already
 * ends the flight, and the mark it clears is what keeps the `finally` beneath a
 * caught throw from claiming a swallow.
 *
 * A `try` outside every recorded frame has no mark to read and is left alone.
 * @param {Splicer} ctx
 * @param {import('typescript').TryStatement} node
 */
function spliceFinally(ctx, node) {
  const { ts, sf, s } = ctx;
  if (!node.finallyBlock || !finallyCompletes(ts, node.finallyBlock)) return;
  if (!isRecorded(ctx, node)) return;
  const keyword = node.getChildren(sf).find((c) => c.kind === ts.SyntaxKind.FinallyKeyword);
  if (!keyword) return;
  const frame = frameVar(ctx, node);
  const line = lineOf(sf, keyword.getStart(sf));
  if (!node.catchClause) {
    s.appendLeft(keyword.getStart(sf), `catch(__sfe){__srt.mark(${frame},__sfe);throw __sfe}`);
  }
  s.appendLeft(node.finallyBlock.getStart(sf) + 1, `__srt.handledFinally(${frame},${line});`);
}

/**
 * Pass two: the splices. Every insertion is newline-free; every closing
 * insertion uses `prependRight` so two closers landing on one offset come out
 * innermost first.
 * @param {Splicer} ctx
 */
function splice(ctx) {
  const { ts, sf } = ctx;
  /** @param {Node} node */
  const visit = (node) => {
    if (isHoistedCall(ts, node)) return; // vitest hoists it above our header
    if (isFunctionLike(ts, node) && ctx.indexOf.has(node)) spliceFunction(ctx, node);
    else if (ts.isReturnStatement(node)) spliceReturn(ctx, node);
    else if (ts.isAwaitExpression(node)) spliceSuspension(ctx, node, AWAIT, 'await');
    else if (ts.isYieldExpression(node)) spliceSuspension(ctx, node, YIELD, 'yield');
    else if (ts.isThrowStatement(node)) spliceThrow(ctx, node);
    else if (ts.isTryStatement(node)) spliceFinally(ctx, node);
    else if (ts.isCatchClause(node)) spliceCatch(ctx, node);
    else if (ts.isCallExpression(node) && !spliceRejectionCallback(ctx, node)) {
      spliceTaskBoundary(ctx, node);
    }
    // After the chain and before the children: the focus tier's rows (spec
    // §3.1). A `CatchClause`'s head row must follow the HANDLED the chain just
    // registered, and every statement's row must be registered before its own
    // descendants' closers (plan P3).
    if (isFocusedFrame(ctx, node)) spliceFocused(ctx, node);
    ts.forEachChild(node, visit);
  };
  visit(sf);
}

/**
 * The parser's own complaints about a file. TypeScript's parser recovers from
 * anything, so a broken file still yields a tree — with positions that mean
 * nothing. Splicing into it would corrupt the source, so a file that does not
 * parse is reported and left alone (R10).
 * @param {SourceFile} sf
 * @returns {string[]} the first three message texts, flattened
 */
function parseErrors(sf) {
  const diagnostics = /** @type {import('typescript').Diagnostic[]|undefined} */ (
    /** @type {any} */ (sf).parseDiagnostics
  );
  // An absent field is not an absence of errors. A TypeScript build that dropped
  // or renamed it would have us splice into a tree we cannot vouch for (R10a).
  if (!Array.isArray(diagnostics)) {
    throw new Error(
      'sensorium-ts: this TypeScript build exposes no parseDiagnostics; refusing to transform blind',
    );
  }
  if (diagnostics.length === 0) return [];
  return diagnostics.slice(0, 3).map((d) =>
    typeof d.messageText === 'string' ? d.messageText : d.messageText.messageText,
  );
}

/**
 * @param {TS} ts
 * @param {string} filePath
 * @returns {import('typescript').ScriptKind}
 */
function scriptKindFor(ts, filePath) {
  const ext = path.extname(filePath);
  if (ext === '.tsx') return ts.ScriptKind.TSX;
  if (ext === '.ts' || ext === '.mts') return ts.ScriptKind.TS;
  // JSX in a `.js` file is common and parsing it as plain JS would mangle
  // positions; `.ts` is the only extension where JSX mode changes meaning.
  return ts.ScriptKind.JSX;
}

/**
 * Where the header goes. Two things must stay ahead of it, and neither may be
 * pushed onto a line of its own: a shebang, which has to be the first line, and
 * a directive prologue — `'use client'` stops being a directive the moment an
 * import precedes it, and demoting it would change what the program does.
 *
 * A directive written without its semicolon (prettier `--semi false`) needs one
 * supplied, or the header is glued to it: `'use client'import * as __srt` is a
 * syntax error. A shebang needs no terminator — it ends at its newline, and a
 * semicolon there would be an empty statement of pure noise.
 * @param {TS} ts
 * @param {SourceFile} sf
 * @param {string} code
 * @returns {{offset: number, terminator: string}|null} null for a file with no code
 */
function headerPlacement(ts, sf, code) {
  let offset = 0;
  let terminator = '';
  if (code.startsWith('#!')) {
    const newline = code.indexOf('\n');
    // A file that is nothing but a shebang line has no code to record.
    if (newline === -1) return null;
    offset = newline + 1;
  }
  for (const statement of sf.statements) {
    if (!ts.isExpressionStatement(statement) || !ts.isStringLiteral(statement.expression)) break;
    offset = statement.end;
    terminator = code[offset - 1] === ';' ? '' : ';';
  }
  return { offset, terminator };
}

/**
 * The header carries the file's identity: the root-relative path the fingerprint
 * hashes, the absolute path the contract stores, the site table, and the digest
 * of the source as it was read. It never adds a line.
 * @param {MagicString} s
 * @param {{offset: number, terminator: string}|null} placement
 * @param {string} header
 */
function prependHeader(s, placement, header) {
  if (!placement) return;
  const text = placement.terminator + header;
  if (placement.offset === 0) s.prepend(text);
  else s.appendLeft(placement.offset, text);
}

/**
 * The parse every pass starts from, or a verdict instead of one.
 * @param {string} code
 * @param {string} filePath
 * @param {{root: string, ts: TS}} opts
 * @returns {{rel: string, sf: SourceFile, diagnostics: string[]}|null} null for
 *   a path this recorder does not transform
 * @throws when the TypeScript build exposes no `parseDiagnostics` (R10a)
 */
function parseFile(code, filePath, opts) {
  if (classify(filePath, opts.root) !== 'transform') return null;
  const ts = opts.ts;
  const rel = path.relative(opts.root, filePath).split(path.sep).join('/');
  const sf = ts.createSourceFile(
    filePath,
    code,
    ts.ScriptTarget.Latest,
    true,
    scriptKindFor(ts, filePath),
  );
  return { rel, sf, diagnostics: parseErrors(sf) };
}

/**
 * Pass one alone: what functions this file offers and what a focus would
 * select, with nothing spliced and no source produced. The resolver asks it
 * before a run, to answer `--focus` with a list or a refusal rather than with
 * a recording nobody wanted.
 * @param {string} code the source as read
 * @param {string} filePath absolute path to the file
 * @param {{root: string, ts: TS, focus?: string[]}} opts
 * @returns {{rel: string, sites: Site[], excluded: Record<string, number>,
 *   excludedSites: ExcludedSite[]}|null}
 *   null for a path this recorder does not transform. A file that did not parse
 *   offers no sites and says why: `excluded['parse-error']`, never a guess --
 *   and it names no excluded function either, because a file this recorder
 *   could not read the shape of has no functions to have skipped.
 */
export function sitesOf(code, filePath, opts) {
  const parsed = parseFile(code, filePath, opts);
  if (parsed === null) return null;
  const { rel, sf, diagnostics } = parsed;
  if (diagnostics.length > 0) {
    return { rel, sites: [], excluded: { 'parse-error': 1 }, excludedSites: [] };
  }
  const { sites, excluded, excludedSites } = planSites(opts.ts, sf, rel, opts.focus ?? []);
  return { rel, sites, excluded, excludedSites };
}

/**
 * Instrument one file.
 * @param {string} code the source as read
 * @param {string} filePath absolute path to the file
 * @param {{root: string, ts: TS, rtPath: string, focus?: string[]}} opts the
 *   invocation root, the consumer's own TypeScript, the import specifier of the
 *   runtime module, and the focus specs (none by default — and with none, this
 *   emits exactly what it emitted before the focus tier existed)
 * @returns {{code: string|null, map: import('magic-string').SourceMap|null, manifest: Manifest}|null}
 *   null for a path this recorder does not transform — outside the root, under
 *   any `node_modules`, a declaration file, CommonJS, or an ineligible
 *   extension. A bare null carries no manifest and means 'not ours'; `classify`
 *   says which it was. A manifest with `code: null` means 'ours, untouched,
 *   counted': the file did not parse, and `excluded['parse-error']` says so.
 * @throws when the TypeScript build exposes no `parseDiagnostics` (R10a): an
 *   absent field is not an absence of errors, and this refuses to splice blind.
 */
export function transformSource(code, filePath, opts) {
  const parsed = parseFile(code, filePath, opts);
  if (parsed === null) return null;
  const ts = opts.ts;
  const { rel, sf, diagnostics } = parsed;

  const sha256 = crypto.createHash('sha256').update(code).digest('hex');
  if (diagnostics.length > 0) {
    return {
      code: null,
      map: null,
      manifest: {
        file: filePath,
        rel,
        sha256,
        instrumented: [],
        focused: [],
        excluded: { 'parse-error': 1 },
        diagnostics,
      },
    };
  }

  const { sites, indexOf, focused, excluded } = planSites(ts, sf, rel, opts.focus ?? []);
  const s = new MagicString(code);
  splice({ ts, sf, s, indexOf, focused, isTestFile: isTestFile(ts, sf, filePath) });

  // The header's table stays three columns: the runtime never needs to know
  // which sites were focused — a focused CALL says so by carrying its `a`.
  const codes = sites.map((site) => [site.qualname, site.line, site.kind]);
  prependHeader(
    s,
    headerPlacement(ts, sf, code),
    `import * as __srt from ${JSON.stringify(opts.rtPath)};` +
      `const __sfile=__srt.file(${JSON.stringify(rel)},${JSON.stringify(filePath)},` +
      `${JSON.stringify(codes)},${JSON.stringify(sha256)});`,
  );

  return {
    code: s.toString(),
    map: s.generateMap({ hires: true, source: filePath, includeContent: true }),
    manifest: {
      file: filePath,
      rel,
      sha256,
      instrumented: sites,
      focused: sites.filter((site) => site.focused).map((site) => site.qualname),
      excluded,
    },
  };
}
