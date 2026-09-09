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

/** @typedef {{k: 'dbg', v: string, trunc: boolean}|{k: 'unread'}} Captured */

/** Serials are per value, not per record: a rethrown OBJECT keeps its own. */
let nextSerial = 1;
/** @type {WeakMap<object, number>} */
const serials = new WeakMap();

/**
 * Capture a value for a RETURN record.
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
  if (Buffer.byteLength(text) <= CAP) return { k: 'dbg', v: text, trunc: false };
  return { k: 'dbg', v: cut(text), trunc: true };
}

/**
 * The longest prefix of `text` that fits the byte budget, cut between
 * characters and never through one.
 * @param {string} text
 * @returns {string}
 */
function cut(text) {
  let bytes = 0;
  let end = 0;
  for (const ch of text) {
    const width = Buffer.byteLength(ch);
    if (bytes + width > CAP) break;
    bytes += width;
    end += ch.length;
  }
  return text.slice(0, end);
}

/**
 * Describe a thrown or rejected value.
 * @param {*} e the value the program threw
 * @param {'throw'|'rejection'} kind how it arrived
 * @returns {{kind: string, type: string, msg: string, serial: number}}
 */
export function exc(e, kind) {
  return { kind, type: typeOf(e), msg: msgOf(e), serial: serialOf(e) };
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
