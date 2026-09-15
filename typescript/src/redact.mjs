// Rule v1: which NAMES hold a secret, the knobs that amend that judgement,
// and the key the digests are taken under.
//
// This recorder stored the whole process environment in plaintext until this
// slice, at 0644, so a trace of any suite launched from a developer's shell
// held whatever that shell was carrying. Rule v1 replaces such a value with
// `<redacted>` at the WRITER, before anything reaches disk, and keeps an
// HMAC-SHA256 of the plaintext beside it so a reader can still say "this
// changed" without being told what it changed to.
//
// WHAT THIS IS NOT
// ----------------
// **Not a secret scanner.** The rule fires on a name's SEGMENTS, so a secret
// in a variable called `x`, or one this set has never heard of, is stored as
// typed. Matching is segment-exact, never substring: substring `KEY` would
// fire on `MONKEY_PATCH` and substring `PASS` on `BYPASS_CACHE`.
// `SENSORIUM_REDACT_NAMES` is the remedy for a name this misses and
// `SENSORIUM_REDACT_ALLOW` for one it wrongly fires on, and both are recorded
// so a reader sees what the recording was made under.
//
// THE FIXTURE
// -----------
// `docs/trace-format/redaction-v1.json` holds every `split` and `fires` case,
// and the Python recorder's suite, `sensorium-rt`'s and `test/redact.test.mjs`
// read the SAME file. A case belongs there, not in a test module: three
// implementations of one rule agree only on what all three are asked.
//
// THE KEY
// -------
// This runtime only ever PARSES `SENSORIUM_REDACT_KEY`, which the driver hands
// it. It never creates a key, never writes one and never reads a key file:
// creating one means a directory, a temporary, a link and a race, and this
// module runs inside somebody else's test suite. An absent, short, long or
// non-hex value is simply unkeyed -- the names are still redacted, and the
// BOOT says `keyed: false` so nobody mistakes a missing digest for a value
// that did not change.
//
// This module imports `node:crypto` and nothing else of ours at RUNTIME:
// `rt.mjs` calls `bootEnv` once at boot and `redactCaptures`/`redactReturn`
// at every capture, and `dbg.mjs` calls `content` and `current` for the one
// text that has no name — a thrown message. The `Captured` type is read back
// from `dbg.mjs` through JSDoc, which is a type reference and not an import,
// so the two modules do not form a cycle.
import crypto from 'node:crypto';

/**
 * The rule's identity, stamped in every BOOT it touches. A later rule is v2;
 * v1 is never amended, because a trace that says `v1` has to mean one thing
 * forever.
 */
export const RULE = 'v1';

/** What a whole-redacted value reads as. */
export const REDACTED = '<redacted>';

/**
 * The hex key the driver hands a recorded process. DELETED from every recorded
 * environment rather than redacted: a digest of the key under the key is a
 * pointless row, and `keyed: true` already implies it was there.
 */
export const KEY_VAR = 'SENSORIUM_REDACT_KEY';

const OFF_VAR = 'SENSORIUM_NO_REDACT';
const NAMES_VAR = 'SENSORIUM_REDACT_NAMES';
const ALLOW_VAR = 'SENSORIUM_REDACT_ALLOW';

/**
 * A segment here fires the rule. Every one of them has a firing case in the
 * fixture. The four compounds (`APIKEY`, `ACCESSKEY`, `SECRETKEY`,
 * `AUTHTOKEN`) exist because a name written as one word — `apikey` — splits
 * into one segment that none of `API`, `KEY` matches.
 */
const SEGMENTS = [
  'KEY', 'APIKEY', 'TOKEN', 'SECRET', 'SECRETS', 'PASSWORD', 'PASSWD',
  'PASSPHRASE', 'PASS', 'AUTH', 'AUTHORIZATION', 'CREDENTIAL', 'CREDENTIALS',
  'CREDS', 'PRIVATE', 'COOKIE', 'COOKIES', 'SIGNATURE', 'BEARER', 'JWT', 'DSN',
  'ACCESSKEY', 'SECRETKEY', 'AUTHTOKEN', 'PWD',
];

/**
 * The segments that fire only as part of a LONGER name (ruling B28, for
 * `KEY`). `PWD`: `MYSQL_PWD` and `DB_PWD` are passwords, and `PWD` and
 * `OLDPWD` are the shell's working directory, on every machine that has ever
 * run a shell. `KEY`: a bare `key` is a cache key, a dict key, a lookup key
 * on almost every function that iterates a mapping, and redacting it by
 * default would blind `watch` on the commonest local in the language, while
 * every compound spelling (`api_key`, `apiKey`, `secret_key`, `build_key`,
 * `KEY_FILE`) still fires and `SENSORIUM_REDACT_NAMES=key` restores it per
 * run.
 */
const SOLO_EXEMPT = ['PWD', 'KEY'];

/**
 * Whole NORMALISED names that fire whatever their segments say. Segment-exact
 * matching cannot see inside a compound word: `PGPASSWORD` splits into the
 * single segment `PGPASSWORD`, which is neither `PG` nor `PASSWORD`. Short by
 * design: a name earns a place only when a census or a report shows it
 * matters, never on imagination.
 */
const EXACT = ['PGPASSWORD'];

/** How many bytes a key is, and how many hex characters that is on the wire. */
const KEY_BYTES = 32;

/**
 * The two camelCase boundaries, in this order: an uppercase RUN followed by
 * Upper+lower (`HTTPToken` -> `HTTP Token`), then lower-or-digit followed by
 * upper (`apiKey` -> `api Key`). Global, because the rule is SPECIFIED as
 * Python's `re.sub`, which rewrites every occurrence and not just the first.
 */
const CAMEL_RUN = /([A-Z]+)([A-Z][a-z])/g;
const CAMEL_STEP = /([a-z0-9])([A-Z])/g;
const SEPARATOR = /[^A-Za-z0-9]+/;

/**
 * `name`'s uppercased segments: `apiKey` -> `[API, KEY]`, `SSH_AUTH_SOCK` ->
 * `[SSH, AUTH, SOCK]`, `XAUTHORITY` -> `[XAUTHORITY]`. Empty segments are
 * dropped, so `__init__` is `[INIT]` and `''` is `[]`.
 * @param {string} name
 * @returns {string[]}
 */
export function split(name) {
  const spaced = name.replace(CAMEL_RUN, '$1 $2').replace(CAMEL_STEP, '$1 $2');
  return spaced.split(SEPARATOR).filter((part) => part !== '')
    .map((part) => part.toUpperCase());
}

/**
 * The comparison form the two knobs use: the segments, joined. So `myco_dsn`,
 * `MYCO_DSN` and `mycoDsn` are one name to a user's list.
 * @param {string} name
 * @returns {string}
 */
export function normalise(name) {
  return split(name).join('');
}

/** @typedef {{off: boolean, names: string[], allow: string[]}} Knobs */

/**
 * The three environment variables, as read once at boot.
 *
 * `names` and `allow` are held NORMALISED and SORTED, so a comparison against
 * a variable's own normalised form is exact and case-blind at once, and the
 * BOOT records one list for one set of knobs whatever order they were written
 * in.
 * @param {Record<string, string|undefined>} env
 * @returns {Knobs}
 */
export function knobsFromEnv(env) {
  const off = env[OFF_VAR];
  return {
    // Reads like `SENSORIUM_NO_INVOCATION_LOG`: any non-empty value other than
    // `"0"` turns the rule off, and `=0`, empty and unset all leave it on.
    off: off !== undefined && off !== '' && off !== '0',
    names: listed(env[NAMES_VAR]),
    allow: listed(env[ALLOW_VAR]),
  };
}

/**
 * A comma list, trimmed, empties dropped, each entry normalised, sorted and
 * deduplicated. An entry that normalises to nothing (`','`, `'-'`) is dropped
 * too — an empty string in the list would match a nameless value.
 * @param {string|undefined} raw
 * @returns {string[]}
 */
function listed(raw) {
  const names = (raw ?? '').split(',')
    .map((part) => normalise(part.trim()))
    .filter((name) => name !== '');
  return [...new Set(names)].sort();
}

/**
 * Whether the name rule fires on `name`.
 *
 * Allow first, and it WINS over `names` — a user's statement about their own
 * variable outranks their own list. Then `EXACT`, then the segments.
 * `knobs.off` is not read here: turning the whole rule off is `redactEnv`'s
 * business, one level up, so that this function stays the answer to "is this a
 * secret-shaped name".
 *
 * A LINEAR scan, not a binary search over the sorted lists (R24). `Knobs` is a
 * plain object any hand can build, and one built with an unsorted list would
 * make a binary search miss — silently, and the price of a miss here is a
 * plaintext secret on disk. The lists are two or three entries long.
 * @param {string} name
 * @param {Knobs} knobs
 * @returns {boolean}
 */
export function fires(name, knobs) {
  const segments = split(name);
  const normalised = segments.join('');
  if (knobs.allow.includes(normalised)) return false;
  if (knobs.names.includes(normalised)) return true;
  if (EXACT.includes(normalised)) return true;
  const multi = segments.length > 1;
  return segments.some((s) => SEGMENTS.includes(s) && (multi || !SOLO_EXEMPT.includes(s)));
}

/**
 * The store's redaction key: 32 bytes, or none of them.
 *
 * Never throws, on any path. `material === null` is the whole of the unkeyed
 * state — `keyed`, `keyId` and `digest` all read from it.
 */
export class Key {
  /**
   * Exactly 64 hex characters and nothing else: `Buffer.from(s, 'hex')` stops
   * silently at the first character that is not one and returns the short
   * buffer, so a key that arrived down a wire between two implementations is
   * checked for the shape it was promised in. Anything else is unkeyed rather
   * than an error — a recorder that refused to record over a malformed knob
   * would cost the whole run.
   * @param {string|undefined} text
   * @returns {Key}
   */
  static fromHex(text) {
    if (typeof text !== 'string' || text.length !== 2 * KEY_BYTES
      || !/^[0-9a-fA-F]+$/.test(text)) {
      return new Key(null);
    }
    return new Key(Buffer.from(text, 'hex'));
  }

  /** @param {Buffer|null} material */
  constructor(material) {
    /** @type {Buffer|null} */
    this.material = material;
  }

  /** @returns {boolean} */
  get keyed() {
    return this.material !== null;
  }

  /**
   * `SHA-256(key)`, first 8 hex: whether two traces' digests are comparable at
   * all.
   * @returns {string|null}
   */
  get keyId() {
    if (this.material === null) return null;
    return crypto.createHash('sha256').update(this.material).digest('hex').slice(0, 8);
  }

  /**
   * `HMAC-SHA256(key, text)`, first 16 hex — an equality identity, not a
   * commitment — or null when there is no key.
   *
   * The UTF-8 bytes of the value as this runtime holds it. A JavaScript string
   * CAN hold a lone surrogate, and node's UTF-8 encoder writes U+FFFD for one;
   * so does the Python recorder's `encode('utf-8', 'replace')` fallback, so
   * the two languages that can hold one agree on its digest. Nothing to do
   * here but say so (R14).
   * @param {string} text
   * @returns {string|null}
   */
  digest(text) {
    if (this.material === null) return null;
    return crypto.createHmac('sha256', this.material).update(text)
      .digest('hex').slice(0, 16);
  }
}

/**
 * (the environment to STORE, the name -> digest table for the BOOT).
 *
 * A new object either way — the caller's is never touched — minus `KEY_VAR`.
 * With the rule off that deletion is the only thing that happens, and the
 * BOOT's `mode: "off"` says so, so a reader knows the plaintext was recorded
 * on purpose.
 *
 * The table's keys are SORTED (R13) so that one environment gives one table,
 * byte for byte, whichever language wrote it — Rust's caller sorts and
 * Python's `redact.env` sorts too. The stored environment keeps the order it
 * arrived in; only the table is ordered.
 * @param {Record<string, string|undefined>} env
 * @param {Key} key
 * @param {Knobs} knobs
 * @returns {{env: Record<string, string|undefined>,
 *            table: Record<string, string|null>}}
 */
export function redactEnv(env, key, knobs) {
  /** @type {Record<string, string|undefined>} */
  const stored = {};
  for (const [name, value] of Object.entries(env)) {
    if (name !== KEY_VAR) stored[name] = value;
  }
  /** @type {Record<string, string|null>} */
  const table = {};
  if (knobs.off) return { env: stored, table };
  for (const name of Object.keys(stored).sort()) {
    if (!fires(name, knobs)) continue;
    table[name] = key.digest(stored[name] ?? '');
    stored[name] = REDACTED;
  }
  return { env: stored, table };
}

/**
 * The BOOT's `redaction` object, in the format's key order.
 *
 * Off is TWO keys and no more: a record that named a key or a knob list while
 * claiming to have applied nothing would invite a reader to believe the
 * plaintext beside it had been considered. The converter adds `env` and `by`
 * to this object later; the runtime writes what the runtime knows.
 *
 * `key_id` and not `keyId`, alone among this module's names: the converter
 * passes this object into the trace's `redaction` meta unchanged, and that is
 * the format's spelling in all three languages.
 * @param {Key} key
 * @param {Knobs} knobs
 * @returns {Record<string, unknown>}
 */
export function redactionMeta(key, knobs) {
  if (knobs.off) return { rule: RULE, mode: 'off' };
  return {
    rule: RULE,
    mode: 'on',
    keyed: key.keyed,
    key_id: key.keyId,
    names: [...knobs.names],
    allow: [...knobs.allow],
  };
}

/**
 * The Rust recorder's recipe: sorted `k=v` lines, sha256, first 16 hex.
 * Comparable within one language, and the ledger says so.
 *
 * Here, beside `redactEnv`, because the hash is taken over what that function
 * RETURNS — the environment the trace will hold, not the one the process was
 * started with. `src/sensorium/ts/invocation.py::env_hash` is the same recipe
 * on the Python side, for the driver's own record and for the converter
 * applying the rule to a BOOT written before it existed.
 * @param {Record<string, string|undefined>} env
 * @returns {string}
 */
export function envHash(env) {
  const lines = Object.keys(env).sort().map((k) => `${k}=${env[k]}`).join('\n');
  return crypto.createHash('sha256').update(lines).digest('hex').slice(0, 16);
}

/**
 * Everything the BOOT record says about the environment it was started with:
 * what to store, its hash, the digest table and the rule it was all done
 * under.
 *
 * One call, because the four are one decision and `rt.mjs` spreading four
 * separate ones could get them out of step — the hash in particular is over
 * the REDACTED environment, and a hash of `process.env` beside a redacted
 * `env` would report a world change whose evidence the trace does not hold.
 * @param {Record<string, string|undefined>} processEnv
 * @returns {{env: Record<string, string|undefined>, envHash: string,
 *            envRedaction: Record<string, string|null>,
 *            redaction: Record<string, unknown>}}
 */
export function bootEnv(processEnv) {
  const knobs = knobsFromEnv(processEnv);
  const key = Key.fromHex(processEnv[KEY_VAR]);
  const { env, table } = redactEnv(processEnv, key, knobs);
  return {
    env,
    envHash: envHash(env),
    envRedaction: table,
    redaction: redactionMeta(key, knobs),
  };
}

// ---------------------------------------------------------------------------
// The content rule (§2.2)
// ---------------------------------------------------------------------------
//
// `redactEnv` above is the NAME half of rule v1: it decides whether a whole
// value is worth redacting at all. `content` below is the CONTENT half: a
// fixed list of patterns over a value's TEXT, whatever it was called. §2.3:
// a name hit redacts the WHOLE value; a content hit replaces the matched
// SPAN and keeps everything around it (`postgres://u:<redacted>@h/db`) — a
// repr or a log line is not a value with an identity, it is text that
// happened to contain one.
//
// NOT A SECRET SCANNER: the list is a floor, nineteen shapes each with a
// minimum length so a short benign string cannot fire. A secret that
// matches none of them is stored as typed.
//
// THE FIXTURE: `docs/trace-format/redaction-v1.json`'s `content` list holds
// every case, and `src/sensorium/redact_content.py`'s suite and
// `cargo-sensorium`'s `redact_content.rs` read the SAME file. The three
// implementations are the same nineteen patterns, textually, save for the
// one place the three engines cannot agree on a spelling: end-of-text in
// the PEM row's truncated form (`\Z` in Python, `\z` in Rust, plain `$`
// here under the `s` flag) and inline case/dotall flags — Python and Rust
// accept `(?i)`/`(?s)` inside the pattern text; JavaScript's `RegExp` does
// not, so the `i`/`s` flags stand in for them on the two patterns that need
// them. Three spellings, one pattern.

/**
 * Escapes a literal string for use inside a `RegExp` source — the handful
 * of characters that are regex metacharacters get a backslash. No engine
 * ships `RegExp.escape` yet; this is the whole of what {@link TRIGGER}
 * needs it for.
 * @param {string} s
 * @returns {string}
 */
function escapeLiteral(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * §2.2's table, verbatim, in the order the table gives it — table order
 * matters exactly once, for `sk-ant` before `sk`: both match an Anthropic
 * key, the whole match is replaced either way so the two rows' output never
 * differs, and the order is only for which row NAME a test or a report
 * attributes the hit to.
 *
 * `group` is which capture a match replaces (`0` is the whole match). The
 * three patterns whose group is not `0` carry the `d` (`hasIndices`) flag,
 * which is how {@link applyOne} recovers a group's own start and end
 * offsets — `String.prototype.replace`'s replacer callback is handed a
 * group's captured VALUE but never its position, so there is no way to
 * "replace only the group" through `replace` alone.
 * @type {{name: string, regex: RegExp, group: number}[]}
 */
export const PATTERNS = [
  { name: 'url-userinfo', regex: /:\/\/[^/\s:@]{1,64}:([^@\s/]{1,256})@/gd, group: 1 },
  // The PEM body, through the matching END line or to end of text when
  // truncated. `s` is inline DOTALL: the body spans real newlines.
  {
    name: 'pem',
    regex: /-----BEGIN [A-Z ]*PRIVATE KEY-----(.*?)(?:-----END [A-Z ]*PRIVATE KEY-----|$)/gsd,
    group: 1,
  },
  { name: 'authorization-header', regex: /\b(Bearer|Basic)\s+([A-Za-z0-9._~+/=-]{16,})/gid, group: 2 },
  { name: 'jwt', regex: /eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g, group: 0 },
  { name: 'sk-ant', regex: /\bsk-ant-[A-Za-z0-9_-]{20,}/g, group: 0 },
  { name: 'sk', regex: /\bsk-[A-Za-z0-9_-]{20,}/g, group: 0 },
  { name: 'stripe', regex: /\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}/g, group: 0 },
  { name: 'github', regex: /\bgh[pousr]_[A-Za-z0-9]{20,}/g, group: 0 },
  { name: 'github-pat', regex: /\bgithub_pat_[A-Za-z0-9_]{20,}/g, group: 0 },
  { name: 'gitlab', regex: /\bglpat-[A-Za-z0-9_-]{20,}/g, group: 0 },
  { name: 'slack', regex: /\bxox[abprs]-[A-Za-z0-9-]{10,}/g, group: 0 },
  { name: 'aws', regex: /\b(AKIA|ASIA)[0-9A-Z]{16}\b/g, group: 0 },
  { name: 'google', regex: /\bAIza[0-9A-Za-z_-]{35}\b/g, group: 0 },
  { name: 'huggingface', regex: /\bhf_[A-Za-z0-9]{20,}/g, group: 0 },
  { name: 'npm', regex: /\bnpm_[A-Za-z0-9]{20,}/g, group: 0 },
  { name: 'pypi', regex: /\bpypi-[A-Za-z0-9_-]{20,}/g, group: 0 },
  { name: 'digitalocean', regex: /\bdop_v1_[a-f0-9]{20,}/g, group: 0 },
  { name: 'shopify', regex: /\bshpat_[a-f0-9]{20,}/g, group: 0 },
  { name: 'sendgrid', regex: /\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}/g, group: 0 },
];

/**
 * B18's pre-check (§12's mitigation, built in rather than waited for): the
 * literal prefix every CASE-SENSITIVE pattern above starts with, as one
 * alternation. A string that matches neither this nor {@link TRIGGER_CI}
 * cannot match any of the nineteen patterns either, so {@link content} skips
 * the whole table rather than running twenty regexes over every string a
 * recording ever touches.
 */
export const TRIGGER = new RegExp([
  '://', '-----BEGIN', 'eyJ', 'sk-', 'sk_', 'rk_', 'gh', 'github_pat_',
  'glpat-', 'xox', 'AKIA', 'ASIA', 'AIza', 'hf_', 'npm_', 'pypi-',
  'dop_v1_', 'shpat_', 'SG.',
].map(escapeLiteral).join('|'));

/**
 * The same pre-check for the one pattern above that is itself case-blind.
 *
 * `authorization-header` accepts every case spelling of each word, and a
 * literal alternation of `Bearer|Basic|bearer|basic` stood in front of it
 * covering two of each: `Authorization: BEARER <token>` matched no literal,
 * skipped the table, and reached the spool in plaintext. A pre-check
 * NARROWER than the pattern it guards is a leak and not an optimisation
 * (ruling R21). Its own `RegExp` with the `i` flag, which is this engine's
 * only spelling of a scoped case fold, and the shape the Python and Rust
 * twins take too so the three agree in behaviour rather than in syntax.
 */
export const TRIGGER_CI = /Bearer|Basic/i;

/**
 * Whether any §2.2 pattern could match `text` at all: the union of the two
 * pre-checks, and the one thing {@link content} consults.
 *
 * The union is what a test may pin. Either half alone is a pre-check for
 * part of the table, and pinning one of them proves nothing about the shapes
 * the other stands in front of.
 * @param {string} text
 * @returns {boolean}
 */
export function triggers(text) {
  return TRIGGER.test(text) || TRIGGER_CI.test(text);
}

/**
 * One pattern's substitution over `text`: the whole match for group `0`
 * (a plain string replacement — `REDACTED` holds no `$` and needs no
 * replacer), or the match with only its group's span swapped for
 * `REDACTED` — never the whole match when a narrower group was asked for
 * (§2.3's span operation: everything around the secret is kept).
 * @param {string} text
 * @param {{regex: RegExp, group: number}} pattern
 * @returns {string}
 */
function applyOne(text, { regex, group }) {
  regex.lastIndex = 0;
  if (group === 0) return text.replace(regex, REDACTED);

  let out = '';
  let lastEnd = 0;
  let m = regex.exec(text);
  while (m !== null) {
    // `d` (`hasIndices`) is on every pattern whose group is not 0, so the
    // match HAS them; the cast is what says so to a checker that reads
    // `indices` as optional on every `RegExp` match.
    const [groupStart, groupEnd] = /** @type {[number, number]} */ (m.indices?.[group]);
    out += text.slice(lastEnd, groupStart) + REDACTED;
    lastEnd = groupEnd;
    // A pattern that could match empty would loop forever at the same
    // position; none of the three do, but a broken pattern must not hang.
    if (m[0].length === 0) regex.lastIndex += 1;
    m = regex.exec(text);
  }
  return out + text.slice(lastEnd);
}

/**
 * `text` with every matched span replaced by `REDACTED`, and whether the
 * text CHANGED — never whether some pattern merely matched.
 *
 * That distinction is the whole of the contract: `url-userinfo` matches
 * `postgres://u:<redacted>@h/db` (its group already reads as the marker),
 * and replacing it with itself is not a hit. Comparing the WHOLE result to
 * the input, once, at the end, is what makes that true without a special
 * case for it — the converters that count `values` from this flag rely on
 * it (Task 6/7).
 *
 * Applied left to right, pattern by pattern in table order, over the
 * CURRENT text — so a later pattern sees an earlier pattern's markers,
 * never the original secret twice.
 * @param {string} text
 * @returns {{text: string, hit: boolean}}
 */
export function content(text) {
  if (!text || !triggers(text)) return { text, hit: false };
  let out = text;
  for (const pattern of PATTERNS) out = applyOne(out, pattern);
  return { text: out, hit: out !== text };
}

// ---------------------------------------------------------------------------
// The value rules (§2.3, at the capture)
// ---------------------------------------------------------------------------
//
// `redactEnv` applies the two halves above to the ENVIRONMENT, once, at boot.
// These apply them to every value a recording captures, at the writer: a
// CALL's arguments, a statement's deltas and a RETURN's value. From 0.6.0
// this runtime does it ITSELF rather than leaving it to the converter, so a
// secret is never on the disk to be retrofitted — which is the only place
// the promise can actually be kept (§5.1).
//
// A capture meets ONE of the two halves, never both, and which one is the
// name's to decide: a value the name rule takes has no text left to scan, and
// one it leaves is offered to the content rule here. That ORDER is the whole
// reason both live in this function rather than in `dbg.mjs` where the text
// is made — a digest taken after a span had been replaced would be an HMAC of
// the marker, which is a CONSTANT, and two different secrets would then carry
// one identity and read as the same value. `redact_values.named` (Python) and
// the Rust runtime's tag-4 delta take the same order for the same reason:
// three implementations of one rule, digesting one text.

/** @typedef {import('./dbg.mjs').Captured} Captured */

/** @type {{key: Key, knobs: Knobs}|null} */
let state = null;

/**
 * The key and the knobs this PROCESS records under, read once.
 *
 * Lazily, and never re-read (B22): a recording is made under one set of
 * rules, and a program that edits `process.env` half way through its own test
 * run must not be able to change what the rest of the recording was made
 * under — or to turn the rule off after the first secret has been withheld.
 * `bootEnv` above keeps its own reads: it is called once, at boot, before
 * anything else, and its answer goes into the BOOT record for a reader.
 * @returns {{key: Key, knobs: Knobs}}
 */
export function current() {
  if (state === null) {
    state = { key: Key.fromHex(process.env[KEY_VAR]), knobs: knobsFromEnv(process.env) };
  }
  return state;
}

/**
 * The name a returned value was asked for by (B7): `Store.getApiKey` ->
 * `getApiKey`, `fetch.<anonymous>` -> `<anonymous>`.
 *
 * `<anonymous>` and the other bracketed spellings come through unchanged and
 * fire on nothing — their segments are words in no set — which is the
 * answer, not a special case.
 * @param {string} qualname
 * @returns {string}
 */
export function lastSegment(qualname) {
  const tail = qualname.slice(qualname.lastIndexOf('.') + 1);
  return tail === '' ? qualname : tail;
}

/**
 * `map` with every capture whose NAME fires taken whole.
 *
 * The arguments of a focused CALL and the deltas of a LINE, which are the two
 * places this runtime holds a value under a name the program chose. A name
 * that does not fire is left with the capture it arrived with — the same
 * object, not a copy of it.
 * @param {Record<string, Captured>} map
 * @returns {Record<string, Captured>}
 */
export function redactCaptures(map) {
  const { key, knobs } = current();
  if (knobs.off) return map;
  /** @type {Record<string, Captured>} */
  const out = {};
  for (const [name, captured] of Object.entries(map)) {
    out[name] = fires(name, knobs) ? taken(captured, key) : scanned(captured);
  }
  return out;
}

/**
 * A RETURN's capture, taken whole when the CALLEE's own name fires (B7).
 *
 * The value a function hands back has no name of its own, so the rule reads
 * the one it was asked for by: `getApiKey()`'s answer is an API key whatever
 * the caller stores it in.
 * @param {string} qualname the callee's, as the FILE record declared it
 * @param {Captured} captured
 * @returns {Captured}
 */
export function redactReturn(qualname, captured) {
  const { key, knobs } = current();
  if (knobs.off) return captured;
  return fires(lastSegment(qualname), knobs)
    ? taken(captured, key) : scanned(captured);
}

/**
 * The texts that withhold NOTHING, so the name rule leaves them alone (ruling
 * R19). A function that returned nothing is a fact about the program, and a
 * name is not a reason to hide that it returned: the marker would cost a
 * reader that fact, hide no secret, and publish a digest of a constant. The
 * same exemption Python gives its `none` kind and Rust its `()` (R17),
 * written over the TEXT because `dbg` has no type of its own. Two spellings
 * and nothing near them: `NaN` is a value the program had, and a text that
 * merely contains one of these is taken like any other.
 */
const WITHHOLDS_NOTHING = new Set(['undefined', 'null']);

/**
 * B4: the whole value, gone, and an HMAC of it in its place.
 *
 * `oid` and `type` STAY — the address and the constructor are facts about
 * the program, not about the value, and `flow --object` follows them. `trunc`
 * is written FALSE rather than dropped: nothing was clipped, because the
 * whole of it was taken, and a reader that met the key missing would have to
 * guess whether the formatter had been cut short.
 *
 * Two captures are left exactly as they are, for one reason: there is nothing
 * to take. An `unread` never held a text, and a `dbg` whose text is one of
 * {@link WITHHOLDS_NOTHING} holds one that says the program produced no value
 * — and a reader told `<redacted>` there would have lost a fact and been
 * shown no secret.
 * @param {Captured} captured
 * @param {Key} key
 * @returns {Captured}
 */
function taken(captured, key) {
  if (captured.k !== 'dbg' || WITHHOLDS_NOTHING.has(captured.v)) return captured;
  return {
    ...captured,
    v: REDACTED,
    trunc: false,
    redacted: { by: 'name', digest: key.digest(captured.v) },
  };
}

/**
 * The CONTENT half over one capture's own text: every matched span replaced,
 * and a `redacted` object saying so — with no digest, because a partial
 * cannot honestly commit to the whole.
 *
 * Over the CAPPED text, which is what the trace would otherwise have held: a
 * secret the 200-byte cap already cut in half is not there to match, and a
 * rule run over the whole rendering would mark a capture for a span the
 * record does not carry. `trunc` STAYS: the text was clipped, and a span
 * inside it was replaced.
 *
 * The mark is written on a CHANGE, never on a match — `<redacted>` inside a
 * URL's userinfo matches the pattern that put it there, and replacing it with
 * itself is not a hit. `content` above is where that distinction lives.
 * @param {Captured} captured
 * @returns {Captured}
 */
function scanned(captured) {
  if (captured.k !== 'dbg') return captured;
  const { text, hit } = content(captured.v);
  if (!hit) return captured;
  return { ...captured, v: text, redacted: { by: 'content', digest: null } };
}
