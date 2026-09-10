// The escape rule: what a `catch` binding's own body DID with the value, decided
// syntactically at transform time and written on the record as a `how` word. It
// is Rust's `escape.rs` transferred (rung 3's R2) with JavaScript's logging
// family in place of the macro list, and it lives in its own module because
// `transform.mjs` is at the repository's line ceiling (plan P2).
//
// Three questions, three exports, no state:
//   catchHow(ts, clause)        a `catch (e) { … }` clause          (spec §2.1)
//   callbackHow(ts, arg)        the argument of `.catch(…)`/`.then(x, …)` (§2.2)
//   finallyCompletes(ts, block) a `finally` block that discards      (§2.3)
//
// Nothing here resolves scopes, types or aliases: an identifier that SPELLS the
// binding's name is a mention of it, shadowed or not. The rule errs towards
// `escaped` — the word that says "this recorder does not claim a swallow" — so
// an unresolved shadow costs a report, never a false accusation.
/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').CatchClause} CatchClause */
/** @typedef {import('typescript').Block} Block */
/** @typedef {import('typescript').Expression} Expression */

/**
 * The console members a mention may be an argument of and still count as
 * swallowed. Log-and-continue is the archetypal swallow: the failure never
 * reached the caller, and the log is where it went. `console.table` and friends
 * are NOT here — the rule names its family rather than matching `console.*`.
 */
export const LOGGING = new Set(['log', 'error', 'warn', 'info', 'debug', 'trace']);

/**
 * A node whose body is a new closure. The walk up from a mention stops at one:
 * a closure KEEPS the binding, so what it does with it is not this clause's
 * verdict to make (§2.1, "a mention inside a nested function body escapes").
 * Classes are here for the same reason a function is — a method body is a
 * closure — and `transform.mjs` keeps its own predicate for a different job
 * (which nodes become frames), so neither file's answer moves the other's.
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean}
 */
function opensClosure(ts, node) {
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
 * Whether an identifier spelled like the binding is a READ of it. Two spellings
 * name something else entirely: the property in `other.e`, and the key in
 * `{ e: 1 }`. A shorthand `{ e }` is a read — it is the value, not a key.
 * @param {TS} ts
 * @param {import('typescript').Identifier} node
 * @returns {boolean}
 */
function isRead(ts, node) {
  const parent = node.parent;
  if (!parent) return true;
  if (ts.isPropertyAccessExpression(parent) && parent.name === node) return false;
  if (ts.isPropertyAssignment(parent) && parent.name === node) return false;
  return true;
}

/**
 * `console.log`, `console.error`, … — the callee of a logging call.
 * @param {TS} ts
 * @param {Expression} callee
 * @returns {boolean}
 */
function isLoggingCallee(ts, callee) {
  return (
    ts.isPropertyAccessExpression(callee) &&
    ts.isIdentifier(callee.expression) &&
    callee.expression.text === 'console' &&
    LOGGING.has(callee.name.text)
  );
}

/**
 * Whether a mention went to a log and nowhere else: walking UP from it, a
 * logging call whose ARGUMENTS the mention lies inside (a bare `e`, a template
 * literal, `String(e)`, `e.message` — anything the argument is built out of).
 *
 * The walk stops at `root` and at a closure boundary above the mention, and
 * finding nothing is an escape. It climbs THROUGH intermediate calls on
 * purpose: `console.error(String(e))` is the spec's own example of a log, and
 * the value of a call that is itself a logging argument goes to the log with it.
 * @param {TS} ts
 * @param {Node} mention
 * @param {Node} root the clause block or callback body the walk may not leave
 * @returns {boolean}
 */
function isLogged(ts, mention, root) {
  let prev = mention;
  let node = mention.parent;
  while (node) {
    if (opensClosure(ts, node)) return false;
    if (
      ts.isCallExpression(node) &&
      node.arguments.indexOf(/** @type {any} */ (prev)) !== -1 &&
      isLoggingCallee(ts, node.expression)
    ) {
      return true;
    }
    if (node === root) return false;
    prev = node;
    node = node.parent;
  }
  return false;
}

/**
 * Whether anything under `node` reads the binding at all, at any depth.
 * @param {TS} ts
 * @param {Node} node
 * @param {string} name
 * @returns {boolean}
 */
function hasMention(ts, node, name) {
  if (ts.isIdentifier(node) && node.text === name && isRead(ts, node)) return true;
  let found = false;
  ts.forEachChild(node, (child) => {
    found = found || hasMention(ts, child, name);
  });
  return found;
}

/**
 * `throw e;` — a throw whose operand, after any parentheses, is the binding
 * ITSELF. A traced exit and not an escape (ruled 2026-09-10 at Task 6): the
 * value does not reach anything, it leaves the same way it arrived, and the
 * RAISE the throw writes carries the same serial, so the rule module reads the
 * pair as a hop (spec §3.3 rule 2) and judges the rethrow on its own block.
 * Counting this mention made rule 3's escaping conjunct bar EVERY `throw e`
 * from a swallow, which contradicts §6.1's `rethrow_hop` row and R4.
 *
 * ONE rule, TWO syntaxes: it holds for a `catch` clause's binding (§2.1) and
 * for a rejection callback's parameter (§2.2) alike, because §2.2 defines the
 * callback word as §2.1's rule applied to that parameter, and a rethrow from a
 * handler carries the serial exactly as a clause's does. Both `catchHow` and
 * `callbackHow` therefore ask for it (ruled 2026-09-10, fix round 2).
 *
 * `throw e.cause`, `throw wrap(e)` and `throw new Wrapped(e)` are NOT this:
 * their operand is something built out of the binding, so the binding reached a
 * property access or a call and the escape stands.
 * @param {TS} ts
 * @param {Node} node
 * @param {string} name
 * @returns {boolean}
 */
function isBareRethrow(ts, node, name) {
  if (!ts.isThrowStatement(node) || !node.expression) return false;
  let operand = node.expression;
  while (ts.isParenthesizedExpression(operand)) operand = operand.expression;
  return ts.isIdentifier(operand) && operand.text === name;
}

/**
 * Whether the binding escapes the body: any mention of it that is not logged
 * and is not a bare rethrow.
 *
 * A closure is not descended into and is not judged by what it does with the
 * value — it KEEPS it, so a mention anywhere inside one is an escape however
 * that closure logs it. An expression body that is itself a closure is read the
 * same way, which is why the check comes before the walk rather than inside it.
 * The bare-rethrow exclusion is at closure depth 0 ONLY, for the same reason:
 * `retry(() => { throw e; })` hands the binding to a closure that may run
 * later, elsewhere, or never, and that is an escape whatever it then throws.
 *
 * Both callers pass `rethrowExits`, so the exclusion is written once and asked
 * for twice rather than duplicated per syntax; the parameter stays explicit so
 * a third caller has to say which rule it wants rather than inherit one.
 * @param {TS} ts
 * @param {Node} root
 * @param {string} name
 * @param {boolean} rethrowExits whether `throw <name>;` is a traced exit
 * @returns {boolean}
 */
function escapes(ts, root, name, rethrowExits = false) {
  if (opensClosure(ts, root)) return hasMention(ts, root, name);
  let escaped = false;
  /** @param {Node} node */
  const visit = (node) => {
    if (escaped) return;
    if (opensClosure(ts, node)) {
      escaped = hasMention(ts, node, name);
      return;
    }
    // Neither a mention nor a subtree to walk: the operand IS the binding, and
    // descending would find that identifier and call it an escape.
    if (rethrowExits && isBareRethrow(ts, node, name)) return;
    if (ts.isIdentifier(node) && node.text === name && isRead(ts, node)) {
      escaped = !isLogged(ts, node, root);
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(root);
  return escaped;
}

/**
 * A `catch` clause's `how` (§2.1). An empty block is the sink it always was,
 * whatever it bound; a clause with no binding can let nothing out; a
 * destructuring binding is an escape, because the runtime never sees what it
 * bound and this rule will not guess. A bare `throw e;` at closure depth 0 is
 * a traced exit and not a mention, so the clause is decided by whatever ELSE
 * its body does with the binding (`isBareRethrow`, ruled 2026-09-10).
 * @param {TS} ts
 * @param {CatchClause} clause
 * @returns {'catch'|'catch_escaped'|'sink_empty_catch'}
 */
export function catchHow(ts, clause) {
  if (clause.block.statements.length === 0) return 'sink_empty_catch';
  const declared = clause.variableDeclaration;
  if (!declared) return 'catch';
  if (!ts.isIdentifier(declared.name)) return 'catch_escaped';
  return escapes(ts, clause.block, declared.name.text, true) ? 'catch_escaped' : 'catch';
}

/**
 * A rejection handler's `how` (§2.2), from the SHAPE of the argument alone.
 * Anything that is not an inline function is opaque: a handler defined
 * elsewhere has its own frame, and whether it swallows is not this splice's to
 * say. An empty body is a sink whichever spelling wrote it. The parameter is
 * read by §2.1's rule, the bare-rethrow exclusion included: a handler that
 * rethrows what it was given is a hop, in either spelling (`isBareRethrow`).
 * @param {TS} ts
 * @param {Node} arg
 * @returns {'sink_empty_catch_callback'|'catch_callback'|'catch_callback_escaped'|'catch_callback_opaque'}
 */
export function callbackHow(ts, arg) {
  if (!ts.isArrowFunction(arg) && !ts.isFunctionExpression(arg)) return 'catch_callback_opaque';
  const body = arg.body;
  if (ts.isBlock(body) && body.statements.length === 0) return 'sink_empty_catch_callback';
  const param = arg.parameters[0];
  if (!param) return 'catch_callback';
  if (!ts.isIdentifier(param.name)) return 'catch_callback_escaped';
  return escapes(ts, body, param.name.text, true) ? 'catch_callback_escaped' : 'catch_callback';
}

/**
 * A loop or a `switch` written INSIDE the `finally` block: a `break` or
 * `continue` it encloses stays in the block and discards nothing.
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean}
 */
function catchesJump(ts, node) {
  return (
    ts.isForStatement(node) ||
    ts.isForInStatement(node) ||
    ts.isForOfStatement(node) ||
    ts.isWhileStatement(node) ||
    ts.isDoStatement(node) ||
    ts.isSwitchStatement(node)
  );
}

/**
 * Whether a `finally` block COMPLETES — leaves by `return`, `break` or
 * `continue` — and so discards whatever was travelling through the frame
 * (§2.3). A `return` counts anywhere at closure depth 0; a `break` or
 * `continue` only where nothing inside the block catches it, because a `break`
 * that stays inside the `finally` discards nothing.
 *
 * Two shapes this reads as NOT completing that do complete: a `continue` inside
 * a `switch` in the block (a `switch` catches `break`, not `continue`), and a
 * LABELLED jump to a loop outside the block. Both under-count — the sink goes
 * unrecorded rather than claimed — and both are named in HONESTY.
 * @param {TS} ts
 * @param {Block} block
 * @returns {boolean}
 */
export function finallyCompletes(ts, block) {
  let found = false;
  /** @param {Node} node @param {boolean} caught */
  const visit = (node, caught) => {
    if (found || opensClosure(ts, node)) return;
    if (ts.isReturnStatement(node)) {
      found = true;
      return;
    }
    if (!caught && (ts.isBreakStatement(node) || ts.isContinueStatement(node))) {
      found = true;
      return;
    }
    const inside = caught || catchesJump(ts, node);
    ts.forEachChild(node, (child) => visit(child, inside));
  };
  ts.forEachChild(block, (child) => visit(child, false));
  return found;
}
