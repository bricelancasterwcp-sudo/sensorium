// One job: name a function-like node the way JavaScript's own tools would.
//
// Design §2.4. The name is file-local and carries no Python ceremony: a nested
// function is `outer.inner`, not `outer.<locals>.inner`; a function with no name
// and no binding is `<anonymous>` with NO ordinal, because an ordinal would move
// every later anonymous function's key when one is inserted above it — the very
// move-fragility `diff --ignore-moves` exists to absorb.
//
// A direct callback of `test`, `it`, `describe`, or `suite` is named from that
// call (`it("adds")`, nested as `describe("math").it("adds")`). The callee in
// the name is the root identifier, and only a string or no-substitution
// template title counts. Every other nameless function stays `<anonymous>`.

/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */

export const ANONYMOUS = '<anonymous>';

/** Roots of a test or suite call. The name keeps this root, never `skip` or `each`. */
const TEST_ROOTS = new Set(['test', 'it', 'describe', 'suite']);

/**
 * The dotted text of `a.b.c`, or null when a segment is not a plain name.
 * A leading `module.exports`, `exports` or `this` is dropped, so
 * `module.exports.x` is named `x` and `this.onTick` is named `onTick`.
 * @param {TS} ts
 * @param {import('typescript').Expression} expr
 * @returns {string|null}
 */
function dottedName(ts, expr) {
  /** @type {string[]} */
  const parts = [];
  let cur = expr;
  for (;;) {
    if (ts.isPropertyAccessExpression(cur)) {
      parts.unshift(cur.name.text);
      cur = cur.expression;
      continue;
    }
    if (ts.isIdentifier(cur)) {
      parts.unshift(cur.text);
      break;
    }
    if (cur.kind === ts.SyntaxKind.ThisKeyword) {
      parts.unshift('this');
      break;
    }
    return null;
  }
  if (parts.length > 2 && parts[0] === 'module' && parts[1] === 'exports') parts.splice(0, 2);
  while (parts.length > 1 && (parts[0] === 'this' || parts[0] === 'exports')) parts.shift();
  return parts.join('.');
}

/**
 * The text of a declaration name that is spelled, not computed.
 * @param {TS} ts
 * @param {Node|undefined} name
 * @returns {string|null}
 */
function spelledName(ts, name) {
  if (!name) return null;
  if (
    ts.isIdentifier(name) ||
    ts.isPrivateIdentifier(name) ||
    ts.isStringLiteral(name) ||
    ts.isNumericLiteral(name)
  ) {
    return name.text;
  }
  return null;
}

/**
 * The identifier chain of a call's callee, the same walk `tasks.mjs` uses for
 * a task boundary. `it.skip` is `['it', 'skip']` and `test.each(rows)` is
 * `['test', 'each']`. A tagged `test.each` is the same chain.
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
 * @returns {node is import('typescript').StringLiteral | import('typescript').NoSubstitutionTemplateLiteral}
 */
function isLiteralTitle(ts, node) {
  return ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node);
}

/**
 * `"` and `\` become escapes so the printed name stays one token.
 * @param {string} text
 * @returns {string}
 */
function escapeTitle(text) {
  return text.replace(/[\\"]/g, (ch) => `\\${ch}`);
}

/**
 * The name of a direct callback of `test`/`it`/`describe`/`suite`, or null.
 * The callback is argument 2 when argument 1 is an object literal
 * (`test(name, options, fn)`), otherwise argument 1. A computed title, a
 * parenthesized callback, or any other callee stays unnamed here.
 * @param {TS} ts
 * @param {Node} node
 * @returns {string|null}
 */
function testCallbackName(ts, node) {
  const parent = node.parent;
  if (!parent || !ts.isCallExpression(parent)) return null;
  const chain = calleeChain(ts, parent.expression);
  if (!chain || !TEST_ROOTS.has(chain[0])) return null;
  const args = parent.arguments;
  const title = args[0];
  if (!title || !isLiteralTitle(ts, title)) return null;
  const hasOptions = args.length > 1 && ts.isObjectLiteralExpression(args[1]);
  if (args[hasOptions ? 2 : 1] !== node) return null;
  // A dot inside a title is still a focus boundary.
  return `${chain[0]}("${escapeTitle(title.text)}")`;
}

/**
 * The name of the binding a nameless function is attached to: a variable, an
 * object property, a class field, an assignment target, a test or suite
 * callback, or `default` for an `export default` expression.
 * @param {TS} ts
 * @param {Node} node
 * @returns {string|null}
 */
function bindingName(ts, node) {
  const called = testCallbackName(ts, node);
  if (called !== null) return called;
  const parent = node.parent;
  if (!parent) return null;
  if (ts.isVariableDeclaration(parent) || ts.isPropertyAssignment(parent) ||
      ts.isPropertyDeclaration(parent)) {
    return spelledName(ts, parent.name);
  }
  if (ts.isBinaryExpression(parent) &&
      parent.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
      parent.right === node) {
    const assigned = dottedName(ts, parent.left);
    // `module.exports = fn` is the whole module's default export, named as
    // `export default` is; `module.exports.x = fn` keeps the property's name.
    return assigned === 'module.exports' ? 'default' : assigned;
  }
  if (ts.isExportAssignment(parent)) return 'default';
  return null;
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean} whether the node is an anonymous `export default` declaration
 */
function isDefaultExport(ts, node) {
  const modifiers = /** @type {{modifiers?: readonly import('typescript').ModifierLike[]}} */ (node)
    .modifiers;
  return !!modifiers && modifiers.some((m) => m.kind === ts.SyntaxKind.DefaultKeyword);
}

/**
 * The function's own name, before any container prefix.
 * @param {TS} ts
 * @param {Node} node a function-like node
 * @returns {string}
 */
function ownName(ts, node) {
  const spelled = spelledName(ts, /** @type {{name?: Node}} */ (node).name);
  if (spelled !== null) return spelled;
  if (ts.isConstructorDeclaration(node)) return 'constructor';
  if (isDefaultExport(ts, node)) return 'default';
  return bindingName(ts, node) ?? ANONYMOUS;
}

/**
 * The name a class or namespace contributes to the names inside it.
 * @param {TS} ts
 * @param {Node} node
 * @returns {string|null}
 */
function containerName(ts, node) {
  if (ts.isClassDeclaration(node) || ts.isClassExpression(node)) {
    return spelledName(ts, node.name) ?? bindingName(ts, node);
  }
  if (ts.isModuleDeclaration(node) && ts.isIdentifier(node.name)) return node.name.text;
  return null;
}

/**
 * The file-local qualified name of a function-like node.
 *
 * `qualnames` holds the already-computed name of every function-like node seen
 * so far; because the AST is walked outermost-first, every enclosing function of
 * `node` is already in it, and the walk stops at the nearest one — that is what
 * makes a nested function `outer.inner` rather than a full container path.
 * @param {TS} ts
 * @param {Node} node a function-like node
 * @param {Map<Node, string>} qualnames
 * @returns {string}
 */
export function qualnameFor(ts, node, qualnames) {
  /** @type {string[]} */
  const parts = [];
  let parent = node.parent;
  while (parent) {
    const enclosing = qualnames.get(parent);
    if (enclosing !== undefined) {
      parts.unshift(enclosing);
      break;
    }
    const container = containerName(ts, parent);
    if (container !== null) parts.unshift(container);
    parent = parent.parent;
  }
  parts.push(ownName(ts, node));
  return parts.join('.');
}
