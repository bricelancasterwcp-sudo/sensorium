// Per-run caps. 0 is unlimited. The driver resolves the command, the
// environment and the store config and exports integers; this module only
// reads those numbers. An unset variable is the built-in default.
//
// The first `maxCalls` activations of each function are stored. Further
// activations of that function, and every activation once the event or byte
// estimate is hit, are counted and not stored. A frame that is not stored is
// still pushed, so a child sees `parent.elided` and the whole subtree is
// counted rather than written under a parent id the spool never recorded.
// A throw materializes the raising frame and each elided ancestor,
// outermost first, as a skeleton CALL (no arguments). Each one spends an
// elided count, which is why a failure still answers.

/** @typedef {{elided: number, file: number, c: number, kept: number, reason: string}} Slot */
/** @typedef {{elided?: boolean, file?: number, c?: number, id?: number}} CapFrame */

export const DEFAULT_MAX_EVENTS = 100000;
export const DEFAULT_MAX_BYTES = 8 * 1024 * 1024;
export const DEFAULT_MAX_CALLS = 1024;

/** Kinds the converter turns into event rows. The cap counts those. */
const EVENT_KINDS = new Set(['CALL', 'RETURN', 'LINE', 'YIELD', 'RESUME', 'RAISE', 'HANDLED']);

/**
 * @param {string|undefined} text
 * @param {number} fallback
 * @returns {number}
 */
function readCap(text, fallback) {
  if (text === undefined || text === null || String(text).trim() === '') return fallback;
  const n = Number(String(text).trim());
  if (!Number.isFinite(n) || n < 0) return fallback;
  return Math.trunc(n);
}

/**
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {{maxEvents: number, maxBytes: number, maxCalls: number}}
 */
export function limitsFromEnv(env = process.env) {
  return {
    maxEvents: readCap(env.SENSORIUM_MAX_EVENTS, DEFAULT_MAX_EVENTS),
    maxBytes: readCap(env.SENSORIUM_MAX_BYTES, DEFAULT_MAX_BYTES),
    maxCalls: readCap(env.SENSORIUM_MAX_CALLS, DEFAULT_MAX_CALLS),
  };
}

/**
 * @param {{maxEvents: number, maxBytes: number, maxCalls: number}} limits
 */
export function createBudget(limits) {
  /** @type {Map<string, Slot>} */
  const hot = new Map();
  /** @type {Map<string, number>} */
  const keptN = new Map();
  /** @type {string[]} */
  const hits = [];
  const hitset = new Set();
  let failuresKept = 0;
  let events = 0;
  let bytes = 0;

  /** @param {number} file @param {number} c */
  const keyOf = (file, c) => `${file}:${c}`;

  /** @param {string} name */
  function mark(name) {
    if (!hitset.has(name)) {
      hitset.add(name);
      hits.push(name);
    }
  }

  /**
   * @param {number} file
   * @param {number} c
   * @param {string} reason
   * @returns {Slot}
   */
  function slotFor(file, c, reason) {
    const key = keyOf(file, c);
    let slot = hot.get(key);
    if (!slot) {
      slot = { elided: 0, file, c, kept: keptN.get(key) ?? 0, reason };
      hot.set(key, slot);
    }
    return slot;
  }

  /** @param {Slot} slot */
  function drop(slot) {
    slot.elided += 1;
    if (slot.elided === 1) mark(slot.reason);
  }

  return {
    limits,
    /**
     * @param {string} kind
     * @param {number} nbytes
     */
    note(kind, nbytes) {
      bytes += nbytes;
      if (EVENT_KINDS.has(kind)) events += 1;
    },
    /**
     * A reason string when this activation must not be stored, else null.
     * A hot function takes the fast path: the slot already says why.
     * @param {{elided?: boolean, reason?: string|null}|null} parent
     * @param {number} file
     * @param {number} c
     * @returns {string|null}
     */
    hiding(parent, file, c) {
      // A child of an elided frame is counted, not stored. That does not
      // use up the child's own quota: a later call with a recorded parent
      // is judged on its own caps.
      if (parent && parent.elided) {
        const reason = parent.reason || 'max_calls';
        drop(slotFor(file, c, reason));
        return reason;
      }
      const key = keyOf(file, c);
      const n = keptN.get(key) ?? 0;
      /** @type {string[]} */
      const reasons = [];
      if (limits.maxCalls && n >= limits.maxCalls) reasons.push('max_calls');
      if (limits.maxEvents && events >= limits.maxEvents) reasons.push('max_events');
      if (limits.maxBytes && bytes >= limits.maxBytes) reasons.push('max_bytes');
      if (!reasons.length) return null;
      for (const reason of reasons) mark(reason);
      const existing = hot.get(key);
      if (existing) {
        drop(existing);
        return existing.reason;
      }
      hot.set(key, { elided: 1, file, c, kept: n, reason: reasons[0] });
      return reasons[0];
    },
    /**
     * A call that was stored. Arms the per-function quota once it is full.
     * A slot opened earlier, because this function was under an elided
     * parent, keeps its elided count and gains this stored call.
     * @param {number} file
     * @param {number} c
     */
    kept(file, c) {
      const key = keyOf(file, c);
      const n = (keptN.get(key) ?? 0) + 1;
      keptN.set(key, n);
      const slot = hot.get(key);
      if (slot) slot.kept += 1;
      else if (limits.maxCalls && n >= limits.maxCalls) {
        hot.set(key, { elided: 0, file, c, kept: n, reason: 'max_calls' });
      }
    },
    /**
     * Spend one elided count so the skeleton CALL is written once.
     * @param {number} file
     * @param {number} c
     * @returns {boolean}
     */
    noteFailure(file, c) {
      const slot = hot.get(keyOf(file, c));
      if (!slot || slot.elided <= 0) return false;
      slot.elided -= 1;
      slot.kept += 1;
      failuresKept += 1;
      return true;
    },
    /**
     * Outermost elided ancestor first, then the throwing frame.
     * @param {CapFrame} frame
     * @param {CapFrame[]} stack
     * @param {(frame: CapFrame, parent: CapFrame|null) => void} emitCall
     */
    materialize(frame, stack, emitCall) {
      if (!frame) return;
      /** @type {CapFrame[]} */
      const chain = [];
      const idx = stack.lastIndexOf(frame);
      if (idx < 0) {
        if (frame.elided) chain.push(frame);
      } else {
        for (let i = idx; i >= 0 && stack[i].elided; i--) chain.push(stack[i]);
      }
      for (let i = chain.length - 1; i >= 0; i--) {
        const cur = chain[i];
        if (!cur.elided || cur.file === undefined || cur.c === undefined) continue;
        if (!this.noteFailure(cur.file, cur.c)) continue;
        const at = stack.lastIndexOf(cur);
        const below = at > 0 ? stack[at - 1] : null;
        const parent = below && !below.elided ? below : null;
        cur.elided = false;
        emitCall(cur, parent);
      }
    },
    /** @returns {Record<string, unknown>|null} */
    report() {
      let callsElided = 0;
      /** @type {{file: number, c: number, elided: number, kept: number}[]} */
      const elisions = [];
      for (const slot of hot.values()) {
        callsElided += slot.elided;
        if (slot.elided > 0) {
          elisions.push({ file: slot.file, c: slot.c, elided: slot.elided, kept: slot.kept });
        }
      }
      if (callsElided <= 0) return null;
      /** @type {Record<string, unknown>} */
      const rec = {
        e: 'ELISION',
        hit: hits.slice(),
        maxEvents: limits.maxEvents,
        maxBytes: limits.maxBytes,
        maxCalls: limits.maxCalls,
        eventsRecorded: events,
        callsElided,
        elisions,
      };
      if (failuresKept) rec.failuresKept = failuresKept;
      return rec;
    },
  };
}

export const budget = createBudget(limitsFromEnv());
