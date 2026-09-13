// Two questions about where a node SITS in its source file, asked by both the
// rewriter and the focus tier's probes: which line a position is on, and
// whether a statement ended with a `;` of its own.
//
// Split out of `transform.mjs` 2026-09-12 (S5 rung 4's debts) to break the
// `transform.mjs ⇄ probe.mjs` import cycle — a pure move, both functions
// unchanged. The cycle was safe (hoisted declarations, called only during a
// transform, never while either module was being evaluated) and it was still a
// cycle: a reader tracing `probe.mjs` was sent back into the file that had just
// called it. Neither function touches the splice plan or the manifest, so
// neither owed the rewriter anything; they belong to the source file.

/** @typedef {import('typescript').SourceFile} SourceFile */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('./transform.mjs').Splicer} Splicer */

/**
 * @param {SourceFile} sf
 * @param {number} pos
 * @returns {number} the 1-based line
 */
export function lineOf(sf, pos) {
  return sf.getLineAndCharacterOfPosition(pos).line + 1;
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
