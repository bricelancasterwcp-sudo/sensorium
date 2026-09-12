// What a statement DID to the names around it, decided syntactically at
// transform time. `escape.mjs`'s sibling: pure functions over the consumer's
// own AST, no state, no I/O, and it lives in its own module because
// `transform.mjs` is at the repository's line ceiling (plan P2).
//
// Three questions, seven exports (spec §3.2, §3.4):
//   writesOf(ts, statement)      the names the statement wrote  → a row's deltas
//   headBindingsOf(ts, statement)  the names a guard binds       → the head row
//   declaredIn(ts, statement)    the block-scoped names that died → `unbound`
// with `boundNames`, `headDeclaredOf`, `isStatementPosition` and `paramNames`
// the parts the three are built out of and Task 4's splices ask for by name.
//
// Nothing here resolves scopes, types or aliases: a name is its spelling. Two
// rules the whole tier rests on, both plan decisions:
//   * P1 — a guarded statement's OWN row carries its head's assignment targets
//     minus what the head DECLARED. `while ((m = …))` reports `m`'s last write
//     (the one that ended the loop and entered no body); `for (let i …)` does
//     not report `i`, which is dead by then and is `unbound` instead.
//   * P4 — a nested function-like or class body is NEVER walked, and
//     `declaredIn` lists a block's DIRECT declarations only. One row owns each
//     name's write and each name's death; a nested statement has its own row.
/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').Statement} Statement */
/** @typedef {import('typescript').Expression} Expression */
/** @typedef {import('typescript').Block} Block */
/** @typedef {import('typescript').BindingName} BindingName */
/** @typedef {import('typescript').CatchClause} CatchClause */
/** @typedef {import('typescript').VariableDeclarationList} VariableDeclarationList */
/** @typedef {import('typescript').FunctionLikeDeclaration} FunctionLike */

/**
 * A node whose body is a new closure, plus a class body. The walk for
 * assignment targets stops at one: what a callback assigns happens when the
 * callback RUNS, which is not this statement's completion (plan P4). Under a
 * focus the nested function is its own frame with its own rows, so nothing is
 * lost — it is only attributed where it happened.
 *
 * `escape.mjs` keeps its own copy of this list for a different job (which
 * mentions leave a `catch` binding's reach) and `transform.mjs` a third (which
 * nodes become frames), so no file's answer moves another's.
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean}
 */
function opensBoundary(ts, node) {
  return (
    ts.isFunctionDeclaration(node) ||
    ts.isFunctionExpression(node) ||
    ts.isArrowFunction(node) ||
    ts.isMethodDeclaration(node) ||
    ts.isConstructorDeclaration(node) ||
    ts.isGetAccessorDeclaration(node) ||
    ts.isSetAccessorDeclaration(node) ||
    ts.isClassDeclaration(node) ||
    ts.isClassExpression(node)
  );
}

/**
 * Whether the token between the two halves of a `BinaryExpression` writes its
 * left side: `=` and the fifteen compound forms. Enumerated rather than taken
 * from a range, because the range is TypeScript's business and this list is the
 * rule (`ts.isAssignmentExpression` is not in the published typings).
 *
 * `&&=`, `||=` and `??=` are here although they may not write: the row reports
 * the binding's value after the statement either way, and the contract says so
 * (spec §3.2).
 * @param {TS} ts
 * @param {import('typescript').SyntaxKind} kind
 * @returns {boolean}
 */
function isAssignmentToken(ts, kind) {
  const k = ts.SyntaxKind;
  switch (kind) {
    case k.EqualsToken:
    case k.PlusEqualsToken:
    case k.MinusEqualsToken:
    case k.AsteriskEqualsToken:
    case k.SlashEqualsToken:
    case k.PercentEqualsToken:
    case k.AsteriskAsteriskEqualsToken:
    case k.LessThanLessThanEqualsToken:
    case k.GreaterThanGreaterThanEqualsToken:
    case k.GreaterThanGreaterThanGreaterThanEqualsToken:
    case k.AmpersandEqualsToken:
    case k.BarEqualsToken:
    case k.CaretEqualsToken:
    case k.AmpersandAmpersandEqualsToken:
    case k.BarBarEqualsToken:
    case k.QuestionQuestionEqualsToken:
      return true;
    default:
      return false;
  }
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {Node} the node inside however many parentheses
 */
function unwrap(ts, node) {
  let inner = node;
  while (ts.isParenthesizedExpression(inner)) inner = inner.expression;
  return inner;
}

/**
 * The names an assignment TARGET binds — the left of an `=`, a `for…of` head's
 * existing binding, an element of either.
 *
 * A `PropertyAccessExpression` or `ElementAccessExpression` contributes
 * nothing: `a.b = 1` writes a property of an object this recorder is not
 * tracking, and calling it a write of `a` would be a lie (spec §3.9, a place
 * write). Everything else is a destructuring shape, and its identifiers are
 * read out of it.
 * @param {TS} ts
 * @param {Node} target
 * @returns {string[]} in source order, duplicates kept for the caller to fold
 */
function targetNames(ts, target) {
  /** @type {string[]} */
  const out = [];
  /** @param {Node} node */
  const visit = (node) => {
    const inner = unwrap(ts, node);
    if (ts.isIdentifier(inner)) {
      out.push(inner.text);
      return;
    }
    if (ts.isArrayLiteralExpression(inner)) {
      for (const element of inner.elements) visit(element);
      return;
    }
    if (ts.isObjectLiteralExpression(inner)) {
      for (const property of inner.properties) {
        if (ts.isPropertyAssignment(property)) visit(property.initializer);
        else if (ts.isShorthandPropertyAssignment(property)) out.push(property.name.text);
        else if (ts.isSpreadAssignment(property)) visit(property.expression);
      }
      return;
    }
    if (ts.isSpreadElement(inner)) {
      visit(inner.expression);
      return;
    }
    // `[a = 1] = xs` and `({b: c = 1} = o)`: the default's LEFT is the target.
    if (ts.isBinaryExpression(inner) && inner.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      visit(inner.left);
    }
  };
  visit(target);
  return out;
}

/**
 * Every name assigned or updated anywhere under `node`, at any depth of the
 * statement's OWN expressions — a nested function or class body is not this
 * statement's (plan P4).
 * @param {TS} ts
 * @param {Node} node
 * @param {string[]} out appended to in source order
 * @returns {void}
 */
function collectTargets(ts, node, out) {
  if (opensBoundary(ts, node)) return;
  if (ts.isBinaryExpression(node) && isAssignmentToken(ts, node.operatorToken.kind)) {
    out.push(...targetNames(ts, node.left));
  } else if (ts.isPrefixUnaryExpression(node) || ts.isPostfixUnaryExpression(node)) {
    const updates =
      node.operator === ts.SyntaxKind.PlusPlusToken ||
      node.operator === ts.SyntaxKind.MinusMinusToken;
    const operand = unwrap(ts, node.operand);
    if (updates && ts.isIdentifier(operand)) out.push(operand.text);
  }
  // Both halves are still walked: `arr[i++] = 0` writes no name the target
  // names, and `i` all the same.
  ts.forEachChild(node, (child) => collectTargets(ts, child, out));
}

/**
 * @param {string[]} names
 * @returns {string[]} the same order, each name once
 */
function unique(names) {
  return [...new Set(names)];
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @param {string[]} [into]
 * @returns {string[]} every name assigned under the node, once each
 */
function targetsIn(ts, node, into = []) {
  collectTargets(ts, node, into);
  return unique(into);
}

/**
 * Every identifier a binding name binds: a plain name, a nested object or array
 * pattern, a default's binding (not the default's own expression), a rest
 * element. A `_`-prefixed name is one of them — nothing here judges a spelling.
 * @param {TS} ts
 * @param {BindingName} name
 * @returns {string[]} in source order
 */
export function boundNames(ts, name) {
  /** @type {string[]} */
  const out = [];
  /** @param {BindingName} node */
  const visit = (node) => {
    if (ts.isIdentifier(node)) {
      out.push(node.text);
      return;
    }
    for (const element of node.elements) {
      if (ts.isBindingElement(element)) visit(element.name);
    }
  };
  visit(name);
  return out;
}

/**
 * @param {TS} ts
 * @param {VariableDeclarationList} list
 * @returns {string[]} every name the list declares
 */
function listNames(ts, list) {
  return list.declarations.flatMap((declaration) => boundNames(ts, declaration.name));
}

/**
 * Whether a declaration list dies with its block. `var` does not (spec §3.4:
 * function-scoped, never `unbound`); nor does a `using` declaration, which is
 * block-scoped in the language and is a declared gap here rather than a rule
 * this rung invented (`NodeFlags.Using` is neither `Let` nor `Const`).
 * @param {TS} ts
 * @param {VariableDeclarationList} list
 * @returns {boolean}
 */
function isBlockScoped(ts, list) {
  return (list.flags & (ts.NodeFlags.Let | ts.NodeFlags.Const)) !== 0;
}

/**
 * Whether a node stands where a statement of a focused body stands, and so gets
 * a row of its own: a statement of a block, of a `case` or `default` clause, or
 * the single body of a guard written without braces (which Task 4 wraps).
 *
 * Module level is not one: module code is never a frame (spec §3.9).
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean}
 */
export function isStatementPosition(ts, node) {
  const parent = node.parent;
  if (!parent || !ts.isStatement(node)) return false;
  if (ts.isBlock(parent) || ts.isCaseClause(parent) || ts.isDefaultClause(parent)) return true;
  if (ts.isIfStatement(parent)) {
    return parent.thenStatement === node || parent.elseStatement === node;
  }
  if (
    ts.isForStatement(parent) ||
    ts.isForInStatement(parent) ||
    ts.isForOfStatement(parent) ||
    ts.isWhileStatement(parent) ||
    ts.isDoStatement(parent) ||
    ts.isLabeledStatement(parent)
  ) {
    return parent.statement === node;
  }
  return false;
}

/**
 * The names a statement WROTE when it completed — the `deltas` of its row.
 *
 * A guarded statement's own row carries its head's writes minus the head's
 * declarations (plan P1): the declarations are dead and are `unbound` instead,
 * and what is left is the write no head row ever reported, because the
 * evaluation that made it entered no body (`m = null` ends the `while`; a falsy
 * `if ((x = f()))` runs no branch).
 * @param {TS} ts
 * @param {Node} statement a node in statement position
 * @returns {string[]} in source order, each name once
 */
export function writesOf(ts, statement) {
  /** @type {string[]} */
  const out = [];
  if (ts.isVariableStatement(statement)) {
    for (const declaration of statement.declarationList.declarations) {
      out.push(...boundNames(ts, declaration.name));
      if (declaration.initializer) collectTargets(ts, declaration.initializer, out);
    }
  } else if (ts.isExpressionStatement(statement)) {
    collectTargets(ts, statement.expression, out);
  } else if (ts.isClassDeclaration(statement)) {
    // It executes where it stands (spec §3.1). An anonymous `export default
    // class` binds no local name and writes nothing.
    if (statement.name) out.push(statement.name.text);
  } else if (
    ts.isIfStatement(statement) ||
    ts.isWhileStatement(statement) ||
    ts.isDoStatement(statement) ||
    ts.isSwitchStatement(statement)
  ) {
    collectTargets(ts, statement.expression, out);
  } else if (ts.isForStatement(statement)) {
    const { initializer, condition, incrementor } = statement;
    if (initializer && !ts.isVariableDeclarationList(initializer)) {
      collectTargets(ts, initializer, out);
    }
    if (condition) collectTargets(ts, condition, out);
    if (incrementor) collectTargets(ts, incrementor, out);
  } else if (ts.isForInStatement(statement) || ts.isForOfStatement(statement)) {
    // The head's own binding is not read here: its last value IS the last head
    // row's, because the assignment that ends the loop is the iterator's, not
    // the head's. `xs` in `for (const v of (xs = list()))` is read.
    const { initializer } = statement;
    if (!ts.isVariableDeclarationList(initializer)) collectTargets(ts, initializer, out);
    collectTargets(ts, statement.expression, out);
  }
  const declared = headDeclaredOf(ts, statement);
  return unique(out).filter((name) => !declared.includes(name));
}

/**
 * The names a guard BINDS OR ASSIGNS as it enters its body — the synthetic
 * first row inside the body, once per entry or iteration (spec §3.2).
 *
 * A `switch` discriminant is not one: its assignment mints nothing, declared
 * (§3.9). A `for…of` head over an existing binding IS one — the head assigns to
 * it each iteration, which is what the loop is for.
 * @param {TS} ts
 * @param {Node} statement a guard, or a `CatchClause`
 * @returns {string[]} in source order, each name once
 */
export function headBindingsOf(ts, statement) {
  if (ts.isForOfStatement(statement) || ts.isForInStatement(statement)) {
    const { initializer } = statement;
    return ts.isVariableDeclarationList(initializer)
      ? listNames(ts, initializer)
      : unique(targetNames(ts, initializer));
  }
  if (ts.isForStatement(statement)) {
    const { initializer } = statement;
    if (!initializer) return [];
    // A C-style head is an ordinary expression evaluated once, so its
    // ASSIGNMENTS are the bindings — unlike a `for…of` head, which IS a target.
    return ts.isVariableDeclarationList(initializer)
      ? listNames(ts, initializer)
      : targetsIn(ts, initializer);
  }
  if (ts.isWhileStatement(statement) || ts.isDoStatement(statement) ||
      ts.isIfStatement(statement)) {
    return targetsIn(ts, statement.expression);
  }
  if (ts.isCatchClause(statement)) {
    const declaration = statement.variableDeclaration;
    return declaration ? boundNames(ts, declaration.name) : [];
  }
  return [];
}

/**
 * The subset of `headBindingsOf` that DECLARES its names, and so kills them
 * when the guard completes: a `let`/`const` in a loop head, a `catch` binding.
 * A `var` head declares a name that outlives the loop, so it is not one — its
 * final value is the guard's row's delta instead (`writesOf`).
 * @param {TS} ts
 * @param {Node} statement a guard, or a `CatchClause`
 * @returns {string[]}
 */
export function headDeclaredOf(ts, statement) {
  if (ts.isCatchClause(statement)) return headBindingsOf(ts, statement);
  if (
    ts.isForStatement(statement) ||
    ts.isForInStatement(statement) ||
    ts.isForOfStatement(statement)
  ) {
    const { initializer } = statement;
    if (initializer && ts.isVariableDeclarationList(initializer) &&
        isBlockScoped(ts, initializer)) {
      return listNames(ts, initializer);
    }
  }
  return [];
}

/**
 * The block-scoped names a list of statements declares DIRECTLY — not those of
 * a block-like statement among them, which owns its own row and its own deaths
 * (plan P4). A `FunctionDeclaration` is one of them: an ES module is strict, so
 * its binding is the block's.
 * @param {TS} ts
 * @param {readonly Statement[]} statements
 * @param {string[]} out
 * @returns {void}
 */
function collectDeclared(ts, statements, out) {
  for (const statement of statements) {
    if (ts.isVariableStatement(statement)) {
      if (isBlockScoped(ts, statement.declarationList)) {
        out.push(...listNames(ts, statement.declarationList));
      }
    } else if (ts.isClassDeclaration(statement) || ts.isFunctionDeclaration(statement)) {
      if (statement.name) out.push(statement.name.text);
    }
  }
}

/**
 * @param {TS} ts
 * @param {Node|undefined} body
 * @param {string[]} out
 * @returns {void}
 */
function collectBlock(ts, body, out) {
  if (body && ts.isBlock(body)) collectDeclared(ts, body.statements, out);
}

/**
 * The block-scoped names that DIE when this statement completes — its row's
 * `unbound` (spec §3.4). Its own direct blocks' declarations, plus whatever its
 * head declared.
 *
 * A statement that is not block-like declares nothing at its own completion:
 * `const y = 1;` writes `y`, and `y` dies with the block that HOLDS it, on that
 * block's row.
 * @param {TS} ts
 * @param {Node} statement a node in statement position
 * @returns {string[]} in source order, each name once
 */
export function declaredIn(ts, statement) {
  // A label is not a scope: the statement it labels is the one that declares.
  if (ts.isLabeledStatement(statement)) return declaredIn(ts, statement.statement);
  /** @type {string[]} */
  const out = [];
  if (ts.isBlock(statement)) {
    collectDeclared(ts, statement.statements, out);
  } else if (ts.isIfStatement(statement)) {
    collectBlock(ts, statement.thenStatement, out);
    collectBlock(ts, statement.elseStatement, out);
  } else if (
    ts.isForStatement(statement) ||
    ts.isForInStatement(statement) ||
    ts.isForOfStatement(statement) ||
    ts.isWhileStatement(statement) ||
    ts.isDoStatement(statement)
  ) {
    collectBlock(ts, statement.statement, out);
  } else if (ts.isTryStatement(statement)) {
    collectBlock(ts, statement.tryBlock, out);
    if (statement.catchClause) {
      out.push(...headDeclaredOf(ts, statement.catchClause));
      collectBlock(ts, statement.catchClause.block, out);
    }
    collectBlock(ts, statement.finallyBlock, out);
  } else if (ts.isSwitchStatement(statement)) {
    for (const clause of statement.caseBlock.clauses) {
      collectDeclared(ts, clause.statements, out);
    }
  }
  out.push(...headDeclaredOf(ts, statement));
  return unique(out);
}

/**
 * Every name a function's parameters bind, in order — what a focused CALL
 * carries as its `args` (spec §3.3). A TypeScript `this` parameter is not a
 * parameter and is not read.
 * @param {TS} ts
 * @param {FunctionLike} fn
 * @returns {string[]}
 */
export function paramNames(ts, fn) {
  /** @type {string[]} */
  const out = [];
  for (const parameter of fn.parameters) {
    if (ts.isIdentifier(parameter.name) && parameter.name.text === 'this') continue;
    out.push(...boundNames(ts, parameter.name));
  }
  return out;
}
