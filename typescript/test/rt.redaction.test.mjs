// What rule v1 takes out of a recording, read back off real spools. The name
// half and the content half of §2.3 both land in the RUNTIME from 0.6.0 --
// before a byte reaches the disk — so what is asserted here is the wire and,
// once, the spool's own bytes: a secret the rule missed is a secret on disk,
// whatever the records say about it.
//
// `redact.test.mjs` drives the two rules as functions, against the fixture all
// three implementations share; this file is the runtime wearing them. Split
// from `rt.test.mjs` for the reason `rt.spool.test.mjs` was: both files stay
// under 800 lines.
import assert from 'node:assert/strict';
import test from 'node:test';

import { Key, REDACTED } from '../src/redact.mjs';
import { of, ok, one, run } from './helpers/rt-child.mjs';

/** 32 bytes nobody minted, in the form the driver hands the recorder. */
const KEY_HEX = 'cd'.repeat(32);
const KEY = Key.fromHex(KEY_HEX);

/**
 * A secret shaped like §2.2's `sk` row, and the variable a child is handed it
 * in. Never a literal in the script: BOOT records `argv`, so a secret spelled
 * in the source would be on disk before any rule had run — which would make
 * the bytes assertion below fail for a reason that is not the rule's.
 */
const SK = `sk-test-${'A'.repeat(24)}`;
const VAR = 'SENSORIUM_E16_TOKEN';

/**
 * A child started with the key and the secret this file works in.
 * @param {string} body module source, appended after the runtime import
 * @param {{focus?: string}} [opts]
 */
const child = (body, opts = {}) =>
  run(body, { ...opts, env: { SENSORIUM_REDACT_KEY: KEY_HEX, [VAR]: SK } });

/** What a value taken whole under its name reads as, digest included. */
const taken = {
  k: 'dbg', v: REDACTED, trunc: false,
  redacted: { by: 'name', digest: KEY.digest(`'${SK}'`) },
};
/** And what one the content rule found a span in reads as: no digest. */
const scanned = {
  k: 'dbg', v: `'${REDACTED}'`, trunc: false,
  redacted: { by: 'content', digest: null },
};

test('a focused run withholds the value under a firing name and the secret in every text', () => {
  // Three sites, and both operations: `handle`'s argument is taken WHOLE
  // because its name fires; the local it is copied into is not a firing name,
  // so only the matched SPAN of its text goes; and `secret`'s RETURN is taken
  // whole under the last segment of its own qualname (B7).
  const out = child(`
    const fid = __srt.file('t.ts', '/w/t.ts', [['handle', 3, 'function'],
      ['secret', 9, 'function']], 'sha');
    function secret() {
      const __sf = __srt.call(fid, 1);
      return __srt.ret(__sf, process.env.${VAR});
    }
    function handle(token) {
      const __sf = __srt.call(fid, 0, ['token', token]);
      const copy = token;
      __srt.line(__sf, 5, ['copy', copy]);
      return __srt.ret(__sf, secret());
    }
    handle(process.env.${VAR});
  `, { focus: 'handle' });
  ok(out);
  const [entered, inner] = of(out.recs, 'CALL');
  assert.deepEqual(entered.a.token, taken);
  // A span, and the sentence around it: the quotes inspect wrote are still
  // there, the secret is not, and a partial carries no digest.
  assert.deepEqual(one(out.recs, 'LINE').d.copy, scanned);
  // The RETURN rule reads the CALLEE's own name, so `secret` withholds its
  // value whole and `handle`, which fires on nothing, keeps a scanned text.
  const returns = of(out.recs, 'RETURN');
  const returned = (/** @type {any} */ frame) => returns.find((r) => r.f === frame.f).v;
  assert.deepEqual(returned(inner), taken);
  assert.deepEqual(returned(entered), scanned);
  // H1's shape, asked of the DISK rather than of the records: no byte of the
  // secret is in the file — not in a capture, and not in the environment it
  // was handed through, which the name rule took at BOOT.
  assert.equal(out.text.includes('sk-test-'), false, 'the spool holds the secret');
  assert.equal(out.recs[0].env[VAR], REDACTED);
});

test('a return the seal defers is withheld under the same name rule', () => {
  // A body that returns from inside a `try` with a `finally` is SEAL-DEFERRED
  // (design §4.2): its `return` PENDS the capture and the wrapper's own
  // `finally` writes it. The rule has to run at the pend — the seal has no
  // value of its own to judge — and the body is written the way the
  // transform splices one.
  const out = child(`
    const fid = __srt.file('t.ts', '/w/t.ts', [['getToken', 3, 'function']], 'sha');
    function getToken() {const __sf=__srt.call(fid,0);try{
      try { return __srt.pend(__sf, process.env.${VAR}); } finally { }
    ;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
    getToken();
  `);
  ok(out);
  assert.deepEqual(one(out.recs, 'RETURN').v, taken);
  assert.equal(out.text.includes('sk-test-'), false, 'the spool holds the secret');
});

test('a firing name that returned nothing says so (R19)', () => {
  // Off the wire, where it matters: `getToken` fires, and its RETURN is the
  // fact that it returned at all. Withholding `undefined` would take that
  // fact and hide nothing -- there was never a value.
  const out = child(`
    const fid = __srt.file('t.ts', '/w/t.ts', [['getToken', 3, 'function']], 'sha');
    const f = __srt.call(fid, 0);
    __srt.ret(f, undefined);
  `);
  ok(out);
  assert.deepEqual(one(out.recs, 'RETURN').v,
    { k: 'dbg', v: 'undefined', trunc: false });
});

test('a thrown message is scanned, and a name the rule does not know is not', () => {
  // The content rule is the only one an exception message meets (§2.3): a
  // message is a sentence the program wrote, not a value with an identity,
  // so the span goes and no digest is claimed for the whole. And the case
  // that says what the rule does NOT do: a value under a name in no set is
  // stored exactly as the program had it.
  const out = child(`
    const fid = __srt.file('t.ts', '/w/t.ts', [['rate', 3, 'function']], 'sha');
    const f = __srt.call(fid, 0, ['rate', 3]);
    __srt.thr(f, new Error('refused ' + process.env.${VAR}));
  `);
  ok(out);
  const unwound = one(out.recs, 'UNWIND');
  assert.equal(unwound.x.msg, `refused ${REDACTED}`);
  assert.deepEqual(unwound.x.redacted, { by: 'content', digest: null });
  assert.deepEqual(one(out.recs, 'CALL').a.rate, { k: 'dbg', v: '3', trunc: false });
  assert.equal(out.text.includes('sk-test-'), false, 'the spool holds the secret');
});
