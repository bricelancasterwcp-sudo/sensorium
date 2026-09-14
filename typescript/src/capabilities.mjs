// What this recorder declares it produces, and nothing else.
//
// Its own module because `rt.mjs` is at the repo's 800-line ceiling and this
// is the one block in it that answers a question of its own: what a READER
// may ask of a trace this runtime wrote. The declaration is the runtime's
// word — a spool whose BOOT lacks a key reads `false` for every one of them,
// so what is missing is a record and not a permission — and it belongs to
// the recorder rather than to the converter for that reason (§2.4).

/**
 * What this recorder DECLARES it produces, written into every BOOT record and
 * passed through by the converter (§2.4). A spool whose BOOT lacks a key reads
 * `false`, so a trace this recorder did not write is still refused — what it
 * lacks is a record, not a permission.
 *
 * `err_flow` says the throw-flow rows are complete enough to be judged: every
 * `throw` statement, every `catch` clause with the transform's verdict about
 * its binding, every rejection handler and every `finally` that discards a
 * throw in flight.
 *
 * `object_identity` says every captured object carries an `oid` that is the
 * same number wherever that object is seen again and is never given to a
 * second one. It does not depend on a focus: a RETURN's value is captured at
 * every tier this recorder records at, so the identity is there to follow
 * whether or not any statement was.
 *
 * `line` and `locals` say the LINE rows exist — one per completed statement of
 * a focused function, carrying the names it wrote and the names out of scope
 * at it. Both are declared exactly when `SENSORIUM_FOCUS` is non-empty: with
 * no focus nothing was instrumented for statements and there are no such rows,
 * and a reader told otherwise would report "no hits" for a search that never
 * had anything to search.
 * @param {string} focus the run's `SENSORIUM_FOCUS`, empty when there was none
 * @returns {Record<string, boolean>}
 */
export function capabilities(focus) {
  return focus === ''
    ? { err_flow: true, object_identity: true }
    : { err_flow: true, object_identity: true, line: true, locals: true };
}
