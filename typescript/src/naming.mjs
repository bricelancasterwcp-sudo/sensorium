// What a task is CALLED. Four branches and nothing else: the harness's own name
// for the test now running, the lexical chain the transform read off the source,
// which of the two wins, and whether they disagreed (spec §4, D4).
//
// Split out of `rt.mjs` 2026-09-12 (S5 rung 4's debts) — a pure move, no rule
// changed. The runtime keeps the tier gate: `rt.nameProvider` is still the only
// way a consumer registers a provider, and it refuses when the recorder is off.
// This module holds the provider itself and the rule that reads it, so the name
// question can be answered — and read — without the spool, the frame stack and
// the signal handlers around it.

/** @typedef {{name: string, basis: 'vitest'|'title', conflict: boolean}} Named */

/** The name a task gets when its title is not a string at all. */
export const UNNAMED = '<unnamed: title not a string>';

/** @type {(() => unknown)|null} */
let provider = null;

/**
 * Register the harness's own name for the test now running. The vitest setup
 * file supplies `() => expect.getState().currentTestName ?? null`; under
 * `node --test` there is no provider and the lexical name is the name.
 * @param {unknown} fn
 * @returns {void}
 */
export function setProvider(fn) {
  provider = typeof fn === 'function' ? /** @type {() => unknown} */ (fn) : null;
}

/** @param {unknown} title @returns {string} */
export const titleOf = (title) => (typeof title === 'string' ? title : UNNAMED);

/**
 * The four branches of the naming rule (spec §4, D4).
 * @param {string} title
 * @param {string} lexical
 * @param {number} flags
 * @returns {Named}
 */
export function nameFor(title, lexical, flags) {
  const provided = ask();
  if (typeof provided !== 'string') return { name: lexical, basis: 'title', conflict: false };
  // The cross-check is only possible where the transform saw a plain string
  // literal that is not a `.each` template. A `.concurrent` task's provider
  // name is uncheckable for a different reason, and the ledger says so.
  const checkable = (flags & 1) !== 0 && (flags & 2) === 0;
  if (checkable && !provided.endsWith(title)) {
    return { name: lexical, basis: 'title', conflict: true };
  }
  return { name: provided, basis: 'vitest', conflict: false };
}

/** @returns {unknown} the provider's name, or null when there is none to ask */
export function ask() {
  if (!provider) return null;
  try {
    return provider();
  } catch {
    // `expect.getState()` outside a test throws; that is not this run's news.
    return null;
  }
}
