// Reading values out of the program under test, without trusting them. Both
// exports take a value the consumer produced — a return value, a thrown thing —
// and hand back a small JSON object the wire can carry. Neither may ever throw:
// a recorder that dies on a hostile object has changed the program it was
// supposed to observe. What cannot be read is SAID to be unread; nothing here
// invents a value it did not obtain.
import util from 'node:util';

/** The byte budget one captured value gets on the wire (design §4). */
const CAP = 200;

/** The one inspection this recorder does, pinned by `rt.test.mjs` (`dbg caps`). */
const INSPECT = {
  depth: 2,
  maxArrayLength: 8,
  maxStringLength: 100,
  breakLength: Infinity,
  compact: true,
};

/**
 * What one captured value is on the wire. `oid` and `type` are on the capture
 * of an OBJECT or a function and on nothing else: a primitive has no identity
 * to carry and this recorder does not invent one for it, and a value it could
 * not read is `unread` whole — an oid there would say it knows WHICH object it
 * failed to read.
 * @typedef {{k: 'dbg', v: string, trunc: boolean, oid?: number, type?: string}
 *           |{k: 'unread'}} Captured
 */

/** Serials are per value, not per record: a rethrown OBJECT keeps its own. */
let nextSerial = 1;
/** @type {WeakMap<object, number>} */
const serials = new WeakMap();

/**
 * The identity a captured object carries, and the counter that mints it.
 *
 * Deliberately NOT the exception map above (P12). The two number different
 * populations — every object a capture reads, against every value a throw
 * carried — and one shared counter would put `oid` and `serial` in the same
 * sequence, which reads as a relation between two records that have none. Held
 * weakly, so remembering an identity never keeps an object alive; minted once
 * per object and never reused, so one number means one object for the life of
 * the container and the same object wherever it is seen again.
 */
let nextOid = 1;
/** @type {WeakMap<object, number>} */
const oids = new WeakMap();

/**
 * @param {object} o
 * @returns {number} minted once per object, never reused
 */
function oidOf(o) {
  let id = oids.get(o);
  if (id === undefined) {
    id = nextOid++;
    oids.set(o, id);
  }
  return id;
}

/**
 * Capture a value — a RETURN's, a focused CALL's argument, a statement's delta.
 * @param {unknown} v
 * @returns {Captured}
 */
export function dbg(v) {
  // The common case — an instrumented function that returns nothing — never
  // reaches the inspector.
  if (v === undefined) return { k: 'dbg', v: 'undefined', trunc: false };
  let text;
  try {
    text = util.inspect(v, INSPECT);
  } catch {
    return { k: 'unread' };
  }
  const { v: text_, trunc } = cap(text);
  /** @type {Captured} */
  const out = { k: 'dbg', v: text_, trunc };
  const t = typeof v;
  // `null` is `typeof "object"` and is a primitive all the same.
  if (v !== null && (t === 'object' || t === 'function')) {
    out.oid = oidOf(/** @type {object} */ (v));
    out.type = typeOf(v);
  }
  return out;
}

/**
 * The byte budget, applied to any string this recorder puts on the wire that
 * the CONSUMER supplied — an inspected value, a test name the harness handed
 * us (R14). The cut falls between characters and never through one, so a
 * truncated capture is still text; what was cut is always declared.
 * @param {string} text
 * @returns {{v: string, trunc: boolean}}
 */
export function cap(text) {
  if (Buffer.byteLength(text) <= CAP) return { v: text, trunc: false };
  let bytes = 0;
  let end = 0;
  for (const ch of text) {
    const width = Buffer.byteLength(ch);
    if (bytes + width > CAP) break;
    bytes += width;
    end += ch.length;
  }
  return { v: text.slice(0, end), trunc: true };
}

/**
 * Describe a thrown or rejected value. Both strings it reads came from the
 * consumer, so both are capped (R14a) and a cut is DECLARED in the contract's
 * own spelling (TRACE-FORMAT §5): `trunc` for a cut message, `type_trunc` for a
 * cut type name, each absent when nothing was cut — which is what tells a
 * reader that a text is a whole identity and may be compared as one.
 * @param {*} e the value the program threw
 * @param {'throw'|'rejection'} kind how it arrived
 * @returns {Record<string, unknown>} `{kind, type, msg, serial}` and the flags
 */
export function exc(e, kind) {
  const type = cap(typeOf(e));
  const msg = cap(msgOf(e));
  /** @type {Record<string, unknown>} */
  const out = { kind, type: type.v, msg: msg.v, serial: serialOf(e) };
  if (msg.trunc) out.trunc = true;
  if (type.trunc) out.type_trunc = true;
  return out;
}

/**
 * The constructor's name for an object or a function, `typeof` for a primitive
 * (`null` included, which is `object`), and `unread` when the object lies about
 * its own constructor.
 * @param {*} e
 * @returns {string}
 */
function typeOf(e) {
  const t = typeof e;
  if (e === null || (t !== 'object' && t !== 'function')) return t;
  try {
    const name = e.constructor?.name;
    return typeof name === 'string' ? name : 'unread';
  } catch {
    return 'unread';
  }
}

/**
 * `e.message` where there is one, the value's own string form otherwise, and
 * `<unread>` when either read throws — a getter that raises, an object with no
 * prototype, a Symbol.
 * @param {*} e
 * @returns {string}
 */
function msgOf(e) {
  try {
    const t = typeof e;
    if (e !== null && (t === 'object' || t === 'function') && 'message' in e) {
      return String(e.message);
    }
    return String(e);
  } catch {
    return '<unread>';
  }
}

/**
 * One serial per thrown OBJECT, minted once and remembered weakly, so a rethrow
 * is followable; a fresh one for every primitive, because two equal strings are
 * not the same throw and this recorder will not claim they are.
 * @param {*} e
 * @returns {number}
 */
function serialOf(e) {
  const t = typeof e;
  if (e === null || (t !== 'object' && t !== 'function')) return nextSerial++;
  let serial = serials.get(e);
  if (serial === undefined) {
    serial = nextSerial++;
    serials.set(e, serial);
  }
  return serial;
}
