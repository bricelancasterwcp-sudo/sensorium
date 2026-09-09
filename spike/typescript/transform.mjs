// THROWAWAY spike transform (S5 rung 0): TypeScript AST for positions,
// magic-string for edits. No edit inserts a newline, so every line number
// in the output equals the source's (E4 rests on this). Returns the edited
// TypeScript/TSX plus a source map; the harness's own pipeline strips types
// afterwards (vitest: esbuild; node --test: ts.transpileModule in hook.mjs).
import { createRequire } from 'node:module';
import path from 'node:path';
import crypto from 'node:crypto';

const TS_ROOT = process.env.SENSORIUM_TS_ROOT;
if (!TS_ROOT) throw new Error('SENSORIUM_TS_ROOT (the frontend dir whose node_modules hold typescript + magic-string) is required');
const require = createRequire(path.join(TS_ROOT, 'package.json'));
const ts = require('typescript');
const MagicString = require('magic-string');

export const RT_IMPORT = process.env.SENSORIUM_RT || new URL('./rt.mjs', import.meta.url).pathname;

const FN_KINDS = new Map([
  [ts.SyntaxKind.FunctionDeclaration, 'FunctionDeclaration'],
  [ts.SyntaxKind.FunctionExpression, 'FunctionExpression'],
  [ts.SyntaxKind.ArrowFunction, 'ArrowFunction'],
  [ts.SyntaxKind.MethodDeclaration, 'MethodDeclaration'],
  [ts.SyntaxKind.Constructor, 'Constructor'],
  [ts.SyntaxKind.GetAccessor, 'GetAccessor'],
  [ts.SyntaxKind.SetAccessor, 'SetAccessor'],
]);

function isFnLike(n) { return FN_KINDS.has(n.kind); }

function nearestFn(n) {
  let p = n.parent;
  while (p) { if (isFnLike(p)) return p; p = p.parent; }
  return null;
}

function ownName(node, counters) {
  if (node.name && ts.isIdentifier(node.name)) return node.name.text;
  if (node.name && (ts.isStringLiteral(node.name) || ts.isNumericLiteral(node.name))) return node.name.text;
  if (ts.isConstructorDeclaration(node)) return 'constructor';
  const p = node.parent;
  if (p) {
    if (ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
    if (ts.isPropertyAssignment(p) && (ts.isIdentifier(p.name) || ts.isStringLiteral(p.name))) return p.name.text;
    if (ts.isPropertyDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
    if (ts.isBinaryExpression(p) && p.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      if (ts.isPropertyAccessExpression(p.left)) return p.left.name.text;
      if (ts.isIdentifier(p.left)) return p.left.text;
    }
    if (ts.isExportAssignment(p)) return 'default';
  }
  return `<anonymous>#${++counters.anon}`;
}

function containerNames(node) {
  const names = [];
  let p = node.parent;
  while (p) {
    if (isFnLike(p) && p.__qual) { names.unshift(p.__qual); return names; }
    if ((ts.isClassDeclaration(p) || ts.isClassExpression(p)) && p.name) names.unshift(p.name.text);
    else if (ts.isModuleDeclaration(p) && p.name) names.unshift(p.name.text);
    p = p.parent;
  }
  return names;
}

function lineOf(sf, pos) { return sf.getLineAndCharacterOfPosition(pos).line + 1; }

/**
 * @returns {{code: string, map: object, manifest: object}|null} null when the
 * file is not transformed (not under the root, a .d.ts, unsupported ext).
 */
export function transformSource(code, filePath, opts) {
  const root = opts.root;
  const rel = path.relative(opts.relBase || root, filePath);
  if (rel.startsWith('..') || filePath.endsWith('.d.ts')) return null;
  const ext = path.extname(filePath);
  const kind = ext === '.tsx' ? ts.ScriptKind.TSX : ext === '.jsx' ? ts.ScriptKind.JSX : ext === '.js' || ext === '.mjs' ? ts.ScriptKind.JS : ts.ScriptKind.TS;
  if (![ts.ScriptKind.TS, ts.ScriptKind.TSX, ts.ScriptKind.JS, ts.ScriptKind.JSX].includes(kind)) return null;

  const sf = ts.createSourceFile(filePath, code, ts.ScriptTarget.Latest, true, kind);
  const s = new MagicString(code);
  const counters = { anon: 0 };
  const codes = [];           // [qualname, line] per instrumented function, index = code idx
  const excluded = {};        // kind -> count, for E2
  const fnIdx = new Map();    // node -> idx

  // Pass 1: number every function-like in source order and decide eligibility.
  let hoistedDepth = 0;
  const isVitestHoisted = (n) => ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression)
    && ts.isIdentifier(n.expression.expression) && n.expression.expression.text === 'vi'
    && ['mock', 'doMock', 'hoisted', 'unmock'].includes(n.expression.name.text);
  function visit1(n) {
    if (isVitestHoisted(n)) {
      hoistedDepth += 1;
      ts.forEachChild(n, visit1);
      hoistedDepth -= 1;
      return;
    }
    if (isFnLike(n) && hoistedDepth > 0) {
      const why = 'vitest-hoisted factory (vi.mock/vi.hoisted)';
      excluded[why] = (excluded[why] || 0) + 1;
      n.__qual = ownName(n, counters);
      ts.forEachChild(n, visit1);
      return;
    }
    if (isFnLike(n)) {
      const own = ownName(n, counters);
      const qual = [...containerNames(n), own].join('.');
      n.__qual = qual;
      const hasBody = !!n.body;
      const isAmbient = !!(ts.getCombinedModifierFlags(n) & ts.ModifierFlags.Ambient);
      const isAbstract = !!(ts.getCombinedModifierFlags(n) & ts.ModifierFlags.Abstract);
      if (!hasBody) {
        const why = isAmbient ? 'ambient (declare)' : isAbstract ? 'abstract' : 'overload signature (no body)';
        excluded[why] = (excluded[why] || 0) + 1;
      } else {
        fnIdx.set(n, codes.length);
        codes.push([qual, lineOf(sf, n.getStart(sf)), FN_KINDS.get(n.kind)]);
      }
    }
    ts.forEachChild(n, visit1);
  }
  visit1(sf);

  const sfRef = (n) => { const f = nearestFn(n); return f && fnIdx.has(f) ? '__sf' : 'null'; };

  // Pass 2: edits.
  function visit2(n) {
    if (isFnLike(n) && fnIdx.has(n)) {
      const idx = fnIdx.get(n);
      const body = n.body;
      if (ts.isBlock(body)) {
        const open = body.getStart(sf) + 1;           // just after `{`
        const close = body.end - 1;                    // the `}`
        s.appendLeft(open, `const __sf=__srt.call(__sfile,${idx});try{`);
        s.appendLeft(close, `;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}`);
      } else {
        const bs = body.getStart(sf);
        const be = body.end;
        s.appendLeft(bs, `{const __sf=__srt.call(__sfile,${idx});try{return __srt.ret(__sf,(`);
        s.prependRight(be, `))}catch(__se){__srt.thr(__sf,__se);throw __se}}`);
      }
    }
    if (ts.isReturnStatement(n)) {
      const f = nearestFn(n);
      if (f && fnIdx.has(f)) {
        const kwEnd = n.getStart(sf) + 'return'.length;
        if (n.expression) {
          s.appendLeft(kwEnd, ' __srt.ret(__sf,(');
          s.prependRight(n.expression.end, '))');
        } else {
          s.appendLeft(kwEnd, ' __srt.ret(__sf,undefined)');
        }
      }
    }
    if (ts.isAwaitExpression(n)) {
      const f = nearestFn(n);
      if (f && fnIdx.has(f)) {
        const st = n.getStart(sf);
        const kwEnd = st + 'await'.length;
        s.appendLeft(st, '__srt.r(__sf,');
        s.appendLeft(kwEnd, ' __srt.y(__sf,(');
        s.prependRight(n.expression.end, ')))');
      }
    }
    if (ts.isThrowStatement(n) && n.expression) {
      const kwEnd = n.getStart(sf) + 'throw'.length;
      const line = lineOf(sf, n.getStart(sf));
      s.appendLeft(kwEnd, ` __srt.raise(${sfRef(n)},(`);
      s.prependRight(n.expression.end, `),${line})`);
    }
    if (ts.isCatchClause(n)) {
      const line = lineOf(sf, n.getStart(sf));
      const blockOpen = n.block.getStart(sf) + 1;
      const sink = n.block.statements.length === 0 ? ',"empty_catch"' : '';
      if (n.variableDeclaration) {
        const nm = n.variableDeclaration.name;
        const ref = ts.isIdentifier(nm) ? nm.text : 'undefined';
        s.appendLeft(blockOpen, `__srt.handled(${sfRef(n)},${ref},${line}${sink});`);
      } else {
        s.appendLeft(n.getStart(sf) + 'catch'.length, '(__sce)');
        s.appendLeft(blockOpen, `__srt.handled(${sfRef(n)},__sce,${line}${sink});`);
      }
    }
    if (ts.isCallExpression(n)) {
      const callee = n.expression;
      // `.catch(() => {})` with an empty block body
      if (ts.isPropertyAccessExpression(callee) && callee.name.text === 'catch' && n.arguments.length === 1) {
        const a = n.arguments[0];
        if (ts.isArrowFunction(a) && ts.isBlock(a.body) && a.body.statements.length === 0) {
          const line = lineOf(sf, n.getStart(sf));
          s.appendLeft(a.getStart(sf), `__srt.emptyCatch(${sfRef(n)},${line},`);
          s.prependRight(a.end, ')');
        }
      }
      // test("title", fn) / it("title", fn): the task boundary
      if (ts.isIdentifier(callee) && (callee.text === 'test' || callee.text === 'it') && n.arguments.length >= 2) {
        const last = n.arguments[n.arguments.length - 1];
        if (ts.isArrowFunction(last) || ts.isFunctionExpression(last)) {
          const t0 = n.arguments[0];
          const title = ts.isStringLiteral(t0) || ts.isNoSubstitutionTemplateLiteral(t0) ? JSON.stringify(t0.text) : '"test"';
          s.appendLeft(last.getStart(sf), `__srt.task(${title},`);
          s.prependRight(last.end, ')');
        }
      }
    }
    ts.forEachChild(n, visit2);
  }
  visit2(sf);

  const sha = crypto.createHash('sha256').update(code).digest('hex');
  const header = `import * as __srt from ${JSON.stringify(RT_IMPORT)};const __sfile=__srt.file(${JSON.stringify(rel)},${JSON.stringify(codes.map(([q, l]) => [q, l]))},${JSON.stringify(sha)});`;
  s.prepend(header);

  const manifest = { file: rel, sha, instrumented: codes.map(([q, l, k]) => ({ qualname: q, line: l, kind: k })), excluded };
  return { code: s.toString(), map: s.generateMap({ hires: true, source: filePath, includeContent: true }), manifest };
}
