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

import { qualnameFor } from './qualname.mjs';

/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').SourceFile} SourceFile */
/** @typedef {import('typescript').FunctionLikeDeclaration} FunctionLike */
/** @typedef {'function'|'coroutine'|'generator'|'async_generator'} FrameKind */
/** @typedef {{qualname: string, line: number, kind: FrameKind}} Site */
/** @typedef {{file: string, rel: string, sha256: string, instrumented: Site[], excluded: Record<string, number>, diagnostics?: string[]}} Manifest */

/** Extensions the recorder can instrument; CommonJS is counted, never transformed. */
const ELIGIBLE = new Set(['.ts', '.tsx', '.mts', '.js', '.jsx', '.mjs']);
const COMMONJS = new Set(['.cjs', '.cts']);
const DECLARATION = /\.d\.[cm]?ts$/;

/** A file whose name says it holds tests, whatever it imports. */
const TEST_FILE = /\.(test|spec)\.[cm]?[jt]sx?$/;
/** A file that imports one of these holds tests, whatever it is named. */
const HARNESS_MODULES = new Set(['vitest', 'node:test', '@jest/globals']);

/** `vi.*` calls vitest hoists above every import, our header included. */
const HOISTED_VI = new Set(['mock', 'doMock', 'hoisted', 'unmock']);
const TASK_CALLEES = new Set(['test', 'it']);
const SUITE_CALLEES = new Set(['describe', 'suite']);

/** Suspension kinds on the wire: `await` parks a coroutine, `yield` a generator. */
const AWAIT = 0;
const YIELD = 1;

const CLOSE_BLOCK = ';__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}';
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
function isTestFile(ts, sf, filePath) {
  if (TEST_FILE.test(path.basename(filePath))) return true;
  let found = false;
  /** @param {Node} node */
  const visit = (node) => {
    if (found) return;
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier) &&
        HARNESS_MODULES.has(node.moduleSpecifier.text)) {
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
 * @param {SourceFile} sf
 * @param {number} pos
 * @returns {number} the 1-based line
 */
function lineOf(sf, pos) {
  return sf.getLineAndCharacterOfPosition(pos).line + 1;
}

/**
 * Pass one: number every function-like in source order, decide eligibility, and
 * name every one of them (an excluded function still needs a name, because a
 * function nested inside it is named against it).
 * @param {TS} ts
 * @param {SourceFile} sf
 * @returns {{sites: Site[], indexOf: Map<Node, number>, excluded: Record<string, number>}}
 */
function planSites(ts, sf) {
  /** @type {Site[]} */
  const sites = [];
  /** @type {Map<Node, number>} */
  const indexOf = new Map();
  /** @type {Map<Node, string>} */
  const qualnames = new Map();
  /** @type {Record<string, number>} */
  const excluded = {};
  let hoistedDepth = 0;

  /** @param {string} reason */
  const exclude = (reason) => {
    excluded[reason] = (excluded[reason] ?? 0) + 1;
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
      if (hoistedDepth > 0) exclude('vitest-hoisted-factory');
      else if (!node.body) exclude(bodilessReason(ts, node));
      else {
        indexOf.set(node, sites.length);
        sites.push({
          qualname: /** @type {string} */ (qualnames.get(node)),
          line: lineOf(sf, node.getStart(sf)),
          kind: frameKind(ts, node),
        });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { sites, indexOf, excluded };
}

/**
 * The state pass two threads through every splice: the consumer's TypeScript,
 * the parsed file, the edit buffer, and which function-likes are recorded.
 * @typedef {{ts: TS, sf: SourceFile, s: MagicString, indexOf: Map<Node, number>, isTestFile: boolean}} Splicer
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
 * @param {Splicer} ctx
 * @param {FunctionLike} node a recorded function-like
 */
function spliceFunction(ctx, node) {
  const { ts, sf, s } = ctx;
  const index = ctx.indexOf.get(node);
  const body = /** @type {import('typescript').Block|import('typescript').Expression} */ (
    node.body
  );
  if (ts.isBlock(body)) {
    s.appendLeft(body.getStart(sf) + 1, `const __sf=__srt.call(__sfile,${index});try{`);
    s.prependRight(body.end - 1, CLOSE_BLOCK);
    return;
  }
  s.appendLeft(
    body.getStart(sf),
    `{const __sf=__srt.call(__sfile,${index});try{return __srt.ret(__sf,(`,
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
function terminatorFor(ctx, statement) {
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
 * binding is given one, and an empty block is a sink, not a silence.
 * @param {Splicer} ctx
 * @param {import('typescript').CatchClause} node
 */
function spliceCatch(ctx, node) {
  const { ts, sf, s } = ctx;
  const line = lineOf(sf, node.getStart(sf));
  const how = node.block.statements.length === 0 ? '"sink_empty_catch"' : '"catch"';
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
 * `.catch(() => {})` — a callback that swallows: the runtime records a HANDLED
 * for it, so an empty catch is a sink in the trace and not an absence.
 * @param {Splicer} ctx
 * @param {import('typescript').CallExpression} node
 * @returns {boolean} whether the call was an empty-catch callback
 */
function spliceEmptyCatchCallback(ctx, node) {
  const { ts, sf, s } = ctx;
  const callee = node.expression;
  if (!ts.isPropertyAccessExpression(callee) || callee.name.text !== 'catch') return false;
  if (node.arguments.length !== 1) return false;
  const callback = node.arguments[0];
  if (!ts.isArrowFunction(callback) || !ts.isBlock(callback.body)) return false;
  if (callback.body.statements.length !== 0) return false;
  const line = lineOf(sf, callee.name.getStart(sf));
  s.appendLeft(callback.getStart(sf), `__srt.emptyCatch(${frameVar(ctx, node)},${line},`);
  s.prependRight(callback.end, ')');
  return true;
}

/**
 * A test or a suite: the title and the function are handed to the runtime as
 * the call's own argument list, so options arguments after them survive.
 *
 * The rule is file-scoped (R8, `isTestFile`). Inside a test file the second
 * argument is wrapped whatever its shape — a bare identifier included, which the
 * runtime passes through unchanged — so no task boundary goes missing; outside
 * one, nothing is wrapped, so a consumer's own `describe` is never rewritten.
 * @param {Splicer} ctx
 * @param {import('typescript').CallExpression} node
 */
function spliceTaskBoundary(ctx, node) {
  const { ts, sf, s } = ctx;
  if (!ctx.isTestFile || node.arguments.length < 2) return;
  const chain = calleeChain(ts, node.expression);
  if (!chain) return;
  const isTask = TASK_CALLEES.has(chain[0]);
  if (!isTask && !SUITE_CALLEES.has(chain[0])) return;
  const [title, fn] = node.arguments;
  s.appendLeft(title.getStart(sf), `...__srt.${isTask ? 'task' : 'suite'}((`);
  s.prependRight(title.end, ')');
  if (!isTask) {
    s.prependRight(fn.end, ')');
    return;
  }
  const flags = (isLiteralTitle(ts, title) ? 1 : 0) | (chain.includes('each') ? 2 : 0);
  s.prependRight(fn.end, `,${flags})`);
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
    else if (ts.isCatchClause(node)) spliceCatch(ctx, node);
    else if (ts.isCallExpression(node) && !spliceEmptyCatchCallback(ctx, node)) {
      spliceTaskBoundary(ctx, node);
    }
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
  if (!diagnostics || diagnostics.length === 0) return [];
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
 * a directive prologue — `\'use client\'` stops being a directive the moment an
 * import precedes it, and demoting it would change what the program does.
 *
 * A directive written without its semicolon (prettier `--semi false`) needs one
 * supplied, or the header is glued to it: `\'use client\'import * as __srt` is a
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
 * Instrument one file.
 * @param {string} code the source as read
 * @param {string} filePath absolute path to the file
 * @param {{root: string, ts: TS, rtPath: string}} opts the invocation root, the
 *   consumer's own TypeScript, and the import specifier of the runtime module
 * @returns {{code: string|null, map: import('magic-string').SourceMap|null, manifest: Manifest}|null}
 *   null for a path this recorder does not transform — outside the root, under
 *   any `node_modules`, a declaration file, CommonJS, or an ineligible
 *   extension. A bare null carries no manifest and means \'not ours\'; `classify`
 *   says which it was. A manifest with `code: null` means \'ours, untouched,
 *   counted\': the file did not parse, and `excluded['parse-error']` says so.
 */
export function transformSource(code, filePath, opts) {
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

  const sha256 = crypto.createHash('sha256').update(code).digest('hex');
  const diagnostics = parseErrors(sf);
  if (diagnostics.length > 0) {
    return {
      code: null,
      map: null,
      manifest: {
        file: filePath,
        rel,
        sha256,
        instrumented: [],
        excluded: { 'parse-error': 1 },
        diagnostics,
      },
    };
  }

  const { sites, indexOf, excluded } = planSites(ts, sf);
  const s = new MagicString(code);
  splice({ ts, sf, s, indexOf, isTestFile: isTestFile(ts, sf, filePath) });

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
    manifest: { file: filePath, rel, sha256, instrumented: sites, excluded },
  };
}
