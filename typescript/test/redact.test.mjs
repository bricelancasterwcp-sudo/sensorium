// Rule v1 as this runtime reads it, against the fixture all three
// implementations share (`docs/trace-format/redaction-v1.json`) and against
// two RFC vectors. Nothing here is a mock: the unit half drives the exported
// functions, and the child half spawns the real runtime under a spool
// directory it does not create, so the modes asserted are the ones the
// recorder actually asked the kernel for.
//
// A case belongs in the fixture, not here. Three implementations of one rule
// agree only on what all three are asked, and a name added to a test module
// is a name the other two were never asked about.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { dbg, exc } from '../src/dbg.mjs';
import {
  Key, KEY_VAR, PATTERNS, REDACTED, RULE, bootEnv, content, current, triggers,
  fires, knobsFromEnv, lastSegment, normalise, redactCaptures, redactEnv,
  redactReturn, redactionMeta, split,
} from '../src/redact.mjs';

/** The shared fixture, read the way the Rust suite reads it: off disk. */
const FIXTURE = JSON.parse(fs.readFileSync(
  new URL('../../docs/trace-format/redaction-v1.json', import.meta.url), 'utf8'));

const RT = new URL('../src/rt.mjs', import.meta.url).href;
/** The two modules the value rules live in, for the children below. */
const REDACT = new URL('../src/redact.mjs', import.meta.url).href;
const DBG = new URL('../src/dbg.mjs', import.meta.url).href;

/** 32 bytes nobody minted, in the form a driver hands over. */
const KEY_HEX = 'ab'.repeat(32);
const MATERIAL = Buffer.from(KEY_HEX, 'hex');

// What THIS process's own `current()` will read, stated here rather than
// inherited: the rule reads the environment once, lazily (B22), so a shell
// carrying a key or a knob would decide what every unit case below tests.
// The children have their own, deleted and restated in `record`/`inChild`.
process.env[KEY_VAR] = KEY_HEX;
delete process.env.SENSORIUM_NO_REDACT;
delete process.env.SENSORIUM_REDACT_NAMES;
delete process.env.SENSORIUM_REDACT_ALLOW;

/**
 * A capture read one key at a time. `Captured` is a union, and asking the
 * union for a `dbg` arm's own key is a type error, not a test failure.
 * @param {unknown} capture
 * @returns {any}
 */
const bag = (capture) => capture;

/** The knobs a recording with no knobs was made under. */
const NONE = knobsFromEnv({});

/**
 * The fixture's `knobs` object as `knobsFromEnv` would have read it, so the
 * cases run through the SAME comma parsing a real recording does.
 * @param {{names?: string[], allow?: string[]}} [knobs]
 */
const knobsOf = (knobs) => (knobs === undefined ? NONE : knobsFromEnv({
  SENSORIUM_REDACT_NAMES: (knobs.names ?? []).join(','),
  SENSORIUM_REDACT_ALLOW: (knobs.allow ?? []).join(','),
}));

// --- the name rule ---------------------------------------------------------

test('every split case in the shared fixture', () => {
  assert.ok(FIXTURE.split.length > 0, 'the fixture has split cases');
  for (const c of FIXTURE.split) {
    assert.deepEqual(split(c.name), c.segments, `split(${JSON.stringify(c.name)})`);
  }
});

test('every fires case in the shared fixture, knobs included', () => {
  assert.ok(FIXTURE.names.length > 0, 'the fixture has name cases');
  for (const c of FIXTURE.names) {
    assert.equal(fires(c.name, knobsOf(c.knobs)), c.fires,
      `fires(${JSON.stringify(c.name)}, ${JSON.stringify(c.knobs ?? {})})`);
  }
});

test('normalise is the segments joined, which is the knobs comparison form', () => {
  for (const c of FIXTURE.split) {
    assert.equal(normalise(c.name), c.segments.join(''));
  }
  // One name, three spellings, one comparison form.
  assert.equal(normalise('myco_dsn'), 'MYCODSN');
  assert.equal(normalise('MYCO_DSN'), 'MYCODSN');
  assert.equal(normalise('mycoDsn'), 'MYCODSN');
});

test('PWD fires only inside a longer name', () => {
  // The fixture says it; this says WHICH half of the condition carries it, so
  // dropping the two-segment gate cannot pass by accident.
  assert.equal(fires('PWD', NONE), false);
  assert.equal(fires('OLDPWD', NONE), false);
  assert.equal(fires('MYSQL_PWD', NONE), true);
  assert.equal(split('OLDPWD').length, 1);
});

// --- the knobs -------------------------------------------------------------

test('the off knob reads like every other sensorium off switch', () => {
  // Any non-empty value other than "0"; `=0`, empty and unset leave it on.
  assert.equal(knobsFromEnv({ SENSORIUM_NO_REDACT: '1' }).off, true);
  assert.equal(knobsFromEnv({ SENSORIUM_NO_REDACT: 'no' }).off, true);
  assert.equal(knobsFromEnv({ SENSORIUM_NO_REDACT: '0' }).off, false);
  assert.equal(knobsFromEnv({ SENSORIUM_NO_REDACT: '' }).off, false);
  assert.equal(knobsFromEnv({}).off, false);
});

test('the two lists are comma-split, trimmed, normalised, sorted, empties dropped', () => {
  const knobs = knobsFromEnv({
    SENSORIUM_REDACT_NAMES: ' myco_thing , ZEBRA ,, - ,mycoThing',
    SENSORIUM_REDACT_ALLOW: 'API_KEY',
  });
  // `myco_thing` and `mycoThing` are one name; `,` and `-` normalise to
  // nothing and are dropped, because an empty entry would match a nameless
  // value.
  assert.deepEqual(knobs.names, ['MYCOTHING', 'ZEBRA']);
  assert.deepEqual(knobs.allow, ['APIKEY']);
  assert.deepEqual(knobsFromEnv({ SENSORIUM_REDACT_NAMES: '' }).names, []);
});

// --- the key and the digest ------------------------------------------------

test('the digest is HMAC-SHA256, against RFC 4231 case 2', () => {
  // key = "Jefe", msg = "what do ya want for nothing?". The full vector is
  // 5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843; what a
  // trace carries is its first 16 hex characters -- an equality identity, not
  // a commitment.
  const jefe = new Key(Buffer.from('Jefe', 'utf8'));
  assert.equal(jefe.digest('what do ya want for nothing?'), '5bdcc146bf60754e');
  assert.equal(jefe.digest('x')?.length, 16);
});

test('a key is 64 hex characters and nothing else', () => {
  assert.equal(Key.fromHex(KEY_HEX).keyed, true);
  for (const bad of [undefined, '', 'ab', KEY_HEX + 'ab', `${'ab'.repeat(31)}zz`,
    ` ${'ab'.repeat(31)}a`]) {
    const key = Key.fromHex(bad);
    assert.equal(key.keyed, false, `${bad} is not a key`);
    assert.equal(key.keyId, null);
    assert.equal(key.digest('abc'), null);
  }
});

test('the key id is sha256 of the material, first 8 hex', () => {
  assert.equal(Key.fromHex(KEY_HEX).keyId,
    crypto.createHash('sha256').update(MATERIAL).digest('hex').slice(0, 8));
  assert.equal(Key.fromHex(KEY_HEX).keyId?.length, 8);
});

// --- the environment -------------------------------------------------------

test('redactEnv replaces the value, tables the digest and drops the key var', () => {
  const key = Key.fromHex(KEY_HEX);
  const { env, table } = redactEnv(
    { ZEBRA_TOKEN: 'z', MY_API_KEY: 'abc', PLAIN: 'x', [KEY_VAR]: KEY_HEX }, key, NONE);

  assert.equal(env.MY_API_KEY, REDACTED);
  assert.equal(env.PLAIN, 'x');
  // The key is DELETED, never redacted and never tabled: a digest of the key
  // under the key is a pointless row.
  assert.equal(KEY_VAR in env, false);
  assert.equal(KEY_VAR in table, false);
  assert.equal(table.MY_API_KEY,
    crypto.createHmac('sha256', MATERIAL).update('abc').digest('hex').slice(0, 16));
  // R13: one environment gives one table, byte for byte, in every language.
  assert.deepEqual(Object.keys(table), ['MY_API_KEY', 'ZEBRA_TOKEN']);
  // The stored environment keeps the order it arrived in; only the table is
  // ordered.
  assert.deepEqual(Object.keys(env), ['ZEBRA_TOKEN', 'MY_API_KEY', 'PLAIN']);
});

test('an unkeyed recording still redacts, and says the digest is absent', () => {
  const { env, table } = redactEnv({ MY_API_KEY: 'abc' }, Key.fromHex(undefined), NONE);
  assert.equal(env.MY_API_KEY, REDACTED);
  assert.equal(table.MY_API_KEY, null);
});

test('with the rule off the deletion is the only thing that happens', () => {
  const off = knobsFromEnv({ SENSORIUM_NO_REDACT: '1' });
  const { env, table } = redactEnv({ MY_API_KEY: 'abc', [KEY_VAR]: KEY_HEX },
    Key.fromHex(KEY_HEX), off);
  assert.deepEqual(env, { MY_API_KEY: 'abc' });
  assert.deepEqual(table, {});
});

test('the caller mapping is never touched', () => {
  const source = { MY_API_KEY: 'abc' };
  redactEnv(source, Key.fromHex(KEY_HEX), NONE);
  assert.deepEqual(source, { MY_API_KEY: 'abc' });
});

test('the redaction object is the format key order, and off is two keys', () => {
  assert.deepEqual(redactionMeta(Key.fromHex(KEY_HEX), NONE), {
    rule: RULE, mode: 'on', keyed: true,
    key_id: Key.fromHex(KEY_HEX).keyId, names: [], allow: [],
  });
  assert.deepEqual(Object.keys(redactionMeta(Key.fromHex(KEY_HEX), NONE)),
    ['rule', 'mode', 'keyed', 'key_id', 'names', 'allow']);
  assert.deepEqual(redactionMeta(Key.fromHex(undefined), NONE),
    { rule: RULE, mode: 'on', keyed: false, key_id: null, names: [], allow: [] });
  // Off is TWO keys and no more: naming a key or a knob list while claiming
  // to have applied nothing would invite a reader to believe the plaintext
  // beside it had been considered.
  assert.deepEqual(
    redactionMeta(Key.fromHex(KEY_HEX), knobsFromEnv({ SENSORIUM_NO_REDACT: '1' })),
    { rule: RULE, mode: 'off' });
});

test('bootEnv hashes what the trace will hold, and off holds the plaintext', () => {
  const on = bootEnv({ MY_API_KEY: 'abc', PLAIN: 'x', [KEY_VAR]: KEY_HEX });
  assert.equal(on.env.MY_API_KEY, REDACTED);
  assert.equal(KEY_VAR in on.env, false);
  assert.equal(on.redaction.keyed, true);
  const lines = Object.keys(on.env).sort().map((k) => `${k}=${on.env[k]}`).join('\n');
  assert.equal(on.envHash,
    crypto.createHash('sha256').update(lines).digest('hex').slice(0, 16));

  const off = bootEnv({ MY_API_KEY: 'abc', [KEY_VAR]: KEY_HEX, SENSORIUM_NO_REDACT: '1' });
  assert.deepEqual(off.redaction, { rule: RULE, mode: 'off' });
  assert.deepEqual(off.envRedaction, {});
  assert.equal(off.env.MY_API_KEY, 'abc');
  // The key variable is deleted whatever the mode: it is the one name never
  // written down, redacted or otherwise.
  assert.equal(KEY_VAR in off.env, false);
});

// --- the runtime, in a child process ---------------------------------------

/**
 * Run one statement against the runtime in a child and read the BOOT it
 * wrote, with the two file modes the recorder created.
 *
 * The spool directory does NOT exist when the child starts: the mode asserted
 * is the one `mkdirSync` asked for, and a pre-made directory would prove
 * nothing. Every variable the rule reads is decided HERE and never inherited,
 * for the reason `helpers/rt-child.mjs` gives about the focus.
 * @param {Record<string, string>} extra
 * @returns {{res: import('node:child_process').SpawnSyncReturns<string>,
 *            boot: any, dirMode: number, fileMode: number}}
 */
function record(extra) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sensorium-redact-'));
  const dir = path.join(home, 'spool');
  const env = { ...process.env };
  for (const name of ['SENSORIUM_MANIFEST_DIR', 'SENSORIUM_FOCUS', KEY_VAR,
    'SENSORIUM_NO_REDACT', 'SENSORIUM_REDACT_NAMES', 'SENSORIUM_REDACT_ALLOW']) {
    delete env[name];
  }
  Object.assign(env, {
    SENSORIUM_TIER: 'call', SENSORIUM_SPOOL: dir, SENSORIUM_INVOCATION: 'inv-1',
  }, extra);
  try {
    const res = spawnSync(process.execPath,
      ['--input-type=module', '-e',
        `import * as __srt from ${JSON.stringify(RT)};\n__srt.seen('a test');\n`],
      { encoding: 'utf8', env, timeout: 30_000 });
    assert.equal(res.status, 0, `child stderr: ${res.stderr}`);
    const files = fs.readdirSync(dir);
    assert.equal(files.length, 1, `one spool, saw ${files.join(', ')}`);
    const spool = path.join(dir, files[0]);
    return {
      res,
      boot: JSON.parse(fs.readFileSync(spool, 'utf8').split('\n')[0]),
      dirMode: fs.statSync(dir).mode & 0o777,
      fileMode: fs.statSync(spool).mode & 0o777,
    };
  } finally {
    fs.rmSync(home, { recursive: true, force: true });
  }
}

test('the recorded environment is redacted before it reaches the disk', () => {
  const out = record({ MY_API_KEY: 'abc', PLAIN: 'x', [KEY_VAR]: KEY_HEX });
  const boot = out.boot;
  assert.equal(boot.env.MY_API_KEY, REDACTED);
  assert.equal(boot.env.PLAIN, 'x');
  // The key the driver handed over is deleted from the record, never
  // redacted: `keyed: true` already implies it was there.
  assert.equal(KEY_VAR in boot.env, false);
  assert.equal(KEY_VAR in boot.envRedaction, false);
  assert.equal(boot.envRedaction.MY_API_KEY,
    crypto.createHmac('sha256', MATERIAL).update('abc').digest('hex').slice(0, 16));
  assert.equal(boot.redaction.rule, RULE);
  assert.equal(boot.redaction.mode, 'on');
  assert.equal(boot.redaction.keyed, true);
  assert.equal(boot.redaction.key_id, Key.fromHex(KEY_HEX).keyId);
  assert.deepEqual([boot.redaction.names, boot.redaction.allow], [[], []]);
  // The hash is over what the trace HOLDS, not over what the process was
  // started with: two runs of one unchanged shell hash alike whatever their
  // secrets were.
  const lines = Object.keys(boot.env).sort().map((k) => `${k}=${boot.env[k]}`).join('\n');
  assert.equal(boot.envHash,
    crypto.createHash('sha256').update(lines).digest('hex').slice(0, 16));
});

test('the spool and the directory it is in are the recorder\'s own to read', () => {
  const out = record({ MY_API_KEY: 'abc', [KEY_VAR]: KEY_HEX });
  assert.equal(out.fileMode, 0o600, `spool mode ${out.fileMode.toString(8)}`);
  assert.equal(out.dirMode, 0o700, `spool dir mode ${out.dirMode.toString(8)}`);
});

test('an unkeyed child still redacts and says the digest is absent', () => {
  const boot = record({ MY_API_KEY: 'abc' }).boot;
  assert.equal(boot.env.MY_API_KEY, REDACTED);
  assert.equal(boot.envRedaction.MY_API_KEY, null);
  assert.equal(boot.redaction.keyed, false);
  assert.equal(boot.redaction.key_id, null);
});

test('the knobs a recording was made under are recorded with it', () => {
  const boot = record({
    API_KEY: 'abc', MY_API_KEY: 'abc', MYCO_THING: 'y', [KEY_VAR]: KEY_HEX,
    SENSORIUM_REDACT_NAMES: 'myco_thing', SENSORIUM_REDACT_ALLOW: 'api_key',
  }).boot;
  assert.equal(boot.env.MYCO_THING, REDACTED);
  // Allow WINS over the rule: a user's statement about their own variable
  // outranks it. The match is on the WHOLE normalised name, so the exemption
  // covers `API_KEY` and not the differently named variable beside it.
  assert.equal(boot.env.API_KEY, 'abc');
  assert.equal(boot.env.MY_API_KEY, REDACTED);
  assert.deepEqual(boot.redaction.names, ['MYCOTHING']);
  assert.deepEqual(boot.redaction.allow, ['APIKEY']);
});

test('with the rule off the record says so and holds the plaintext', () => {
  const boot = record({
    MY_API_KEY: 'abc', [KEY_VAR]: KEY_HEX, SENSORIUM_NO_REDACT: '1',
  }).boot;
  assert.equal(boot.env.MY_API_KEY, 'abc');
  assert.deepEqual(boot.redaction, { rule: RULE, mode: 'off' });
  assert.deepEqual(boot.envRedaction, {});
  assert.equal(KEY_VAR in boot.env, false);
});

// --- the content rule (§2.2) ------------------------------------------------
//
// Two operations exist in rule v1 (§2.3): a NAME hit redacts the whole
// value (above); a CONTENT hit replaces the matched SPAN and keeps
// everything around it. `docs/trace-format/redaction-v1.json`'s `content`
// list is what `src/sensorium/redact_content.py`'s suite and
// `redact_content.rs`'s `#[cfg(test)]` read too.

test('every content case in the shared fixture', () => {
  assert.ok(FIXTURE.content.length > 0, 'the fixture has content cases');
  for (const c of FIXTURE.content) {
    const { text, hit } = content(c.text);
    assert.equal(text, c.after, `pattern ${JSON.stringify(c.pattern)}`);
    assert.equal(hit, c.after !== c.text, `pattern ${JSON.stringify(c.pattern)}`);
  }
});

test('every pattern has a positive and a negative row', () => {
  // A pattern with no positive is a pattern nothing here proves fires; a
  // pattern with no negative is a pattern nothing here proves has a floor.
  const byPattern = new Map();
  for (const c of FIXTURE.content) {
    const hits = byPattern.get(c.pattern) ?? [];
    hits.push(c.after !== c.text);
    byPattern.set(c.pattern, hits);
  }
  for (const { name } of PATTERNS) {
    const hits = byPattern.get(name) ?? [];
    assert.ok(hits.some(Boolean), `${name} has no positive row`);
    assert.ok(hits.some((/** @type {boolean} */ h) => !h), `${name} has no negative row`);
  }
});

test('every positive passes the trigger', () => {
  // B18's pre-check: a positive case the trigger misses is a secret the
  // content rule would silently never look at. `triggers`, never one of its
  // two halves: the case-sensitive alternation alone answered false on
  // `Authorization: BEARER <token>` and the table never ran (ruling R21),
  // which is exactly what this test exists to catch.
  for (const c of FIXTURE.content) {
    if (c.after !== c.text) {
      assert.ok(triggers(c.text),
        `${JSON.stringify(c.pattern)}'s positive does not pass the trigger: ${JSON.stringify(c.text)}`);
    }
  }
});

test('the rule is a fixed point', () => {
  // A text that has been through the rule once holds no trigger the rule
  // would act on again -- the marker itself contains none of §2.2's shapes.
  for (const c of FIXTURE.content) {
    assert.equal(content(c.after).text, c.after, `pattern ${JSON.stringify(c.pattern)}`);
  }
});

test('a marker is never re-redacted', () => {
  assert.deepEqual(content(REDACTED), { text: REDACTED, hit: false });
});

test('a url-userinfo marker in context is a no-op', () => {
  // §2.3's boundary case: `hit` means the TEXT CHANGED, not that a pattern
  // matched. `url-userinfo` matches `postgres://u:<redacted>@h/db` (its
  // group is already the marker), and the converter (Task 6/7) counts on
  // this staying a no-op.
  const text = `postgres://u:${REDACTED}@h/db`;
  assert.deepEqual(content(text), { text, hit: false });
});

test('the empty string is a no-op', () => {
  assert.deepEqual(content(''), { text: '', hit: false });
});

// --- the value rules: a name over a capture, a pattern over its text -------
//
// §2.3's two operations, where this runtime applies them. `redactCaptures`
// and `redactReturn` are the NAME half, over a capture `dbg()` has already
// built; `dbg()` and `exc()` are the CONTENT half, over the text they are
// about to write. Both read `current()`, which reads `process.env` ONCE --
// so the key this file runs under is set at the top, before the first call,
// and the two knob cases below are children, because a process cannot change
// what it was started with (B22).

/** A secret shaped like §2.2's `sk` row, long enough to clear its floor. */
const SK = `sk-test-${'A'.repeat(24)}`;

/**
 * Evaluate `body` against `redact.mjs` and `dbg.mjs` in a child started with
 * `extra`, and parse the JSON it printed. The four variables the rule reads
 * are deleted first, for the reason `record` above gives.
 * @param {string} body a function body, returning the value to print
 * @param {Record<string, string>} [extra]
 * @returns {any}
 */
function inChild(body, extra = {}) {
  const env = { ...process.env };
  for (const name of [KEY_VAR, 'SENSORIUM_NO_REDACT', 'SENSORIUM_REDACT_NAMES',
    'SENSORIUM_REDACT_ALLOW']) {
    delete env[name];
  }
  Object.assign(env, extra);
  const script = `import * as __r from ${JSON.stringify(REDACT)};\n`
    + `import * as __d from ${JSON.stringify(DBG)};\n`
    + `console.log(JSON.stringify((() => {${body}})()));\n`;
  const res = spawnSync(process.execPath, ['--input-type=module', '-e', script],
    { encoding: 'utf8', env, timeout: 30_000 });
  assert.equal(res.status, 0, `child stderr: ${res.stderr}`);
  return JSON.parse(res.stdout);
}

test('lastSegment is the name a value was asked for by', () => {
  assert.equal(lastSegment('Store.getApiKey'), 'getApiKey');
  assert.equal(lastSegment('outer.<anonymous>.inner'), 'inner');
  assert.equal(lastSegment('refreshToken'), 'refreshToken');
  // A callback with no name of its own fires on nothing, which is the answer
  // and not a special case: `<anonymous>` splits to `[ANONYMOUS]`.
  assert.equal(lastSegment('<anonymous>'), '<anonymous>');
  assert.equal(fires(lastSegment('<anonymous>'), NONE), false);
  assert.equal(lastSegment(''), '');
  assert.equal(fires(lastSegment(''), NONE), false);
});

test('a capture under a firing name is taken whole, and its neighbour is not', () => {
  const taken = dbg('abc');
  // The digest is over the text `dbg` produced — inspect's rendering, quotes
  // included — because that is the text the trace would otherwise have held.
  assert.equal(bag(taken).v, "'abc'");
  const plain = dbg(1);
  const out = redactCaptures({ token: taken, plain });
  assert.deepEqual(out.token, {
    k: 'dbg',
    v: REDACTED,
    trunc: false,
    redacted: { by: 'name', digest: Key.fromHex(KEY_HEX).digest("'abc'") },
  });
  assert.equal(out.plain, plain, 'a name that does not fire is not copied');
});

test('a taken object keeps the identity it was captured with', () => {
  // B4: the type and the address are facts about the PROGRAM; the text is the
  // value. `flow --object` follows the first two and must still work.
  const out = bag(redactCaptures({ apiKey: dbg({ a: 1 }) }).apiKey);
  assert.equal(out.v, REDACTED);
  assert.equal(out.type, 'Object');
  assert.ok(out.oid > 0);
  assert.equal(out.redacted.by, 'name');
});

test('a value that could not be read is left exactly as it is', () => {
  // Taking it would cost a reader the fact that the value was unreadable and
  // hide no secret: there was never a text.
  /** @type {import('../src/dbg.mjs').Captured} */
  const unread = { k: 'unread' };
  assert.equal(redactCaptures({ token: unread }).token, unread);
  assert.equal(redactReturn('getToken', unread), unread);
});

test('a value that is undefined or null withholds nothing (R19)', () => {
  // A function that returned NOTHING withheld nothing, and a name is not a
  // reason to hide that it returned. The same exemption Python's `none` kind
  // has and Rust's `()` (R17): the marker would cost a reader a fact and hide
  // no secret, and the digest would be an HMAC of a constant.
  const nothing = dbg(undefined);
  assert.equal(redactReturn('secret', nothing), nothing);
  const out = redactCaptures({ token: dbg(undefined), other: dbg(null) });
  assert.deepEqual(out.token, { k: 'dbg', v: 'undefined', trunc: false });
  assert.deepEqual(out.other, { k: 'dbg', v: 'null', trunc: false });
  assert.equal('redacted' in out.token, false);
  assert.equal('redacted' in out.other, false);
  // The boundary is the WHOLE text and nothing near it: every other value a
  // firing name holds is still taken, `NaN` included.
  assert.equal(bag(redactCaptures({ token: dbg(NaN) }).token).v, REDACTED);
  assert.equal(bag(redactReturn('getToken', dbg('undefined'))).v, REDACTED);
});

test('a taken capture says nothing was clipped', () => {
  // `trunc` is written FALSE rather than dropped: a reader that met it
  // missing would have to guess whether the formatter had been cut short.
  // Nothing was cut here — the whole of it was taken.
  // A long STRING is cut by inspect's own 100-character cap long before the
  // wire cap sees it, so the value here is one whose RENDERING is over 200
  // bytes: eight sampled strings, which is what the wire cap is for.
  const long = dbg(Array.from({ length: 8 }, () => 'y'.repeat(60)));
  assert.equal(bag(long).trunc, true);
  assert.equal(bag(redactCaptures({ secret: long }).secret).trunc, false);
});

test('redactReturn reads the last segment of the callee qualname', () => {
  const capture = dbg('abc');
  assert.equal(bag(redactReturn('Store.getApiKey', capture)).v, REDACTED);
  assert.equal(bag(redactReturn('tokenAge', capture)).v, REDACTED);
  // `nestedArrow.double` and `<anonymous>` fire on nothing, and a capture the
  // rule leaves alone is the SAME object, never a copy of it.
  assert.equal(redactReturn('nestedArrow.double', capture), capture);
  assert.equal(redactReturn('<anonymous>', capture), capture);
});

test('current is read once, from the environment this process was started with', () => {
  const first = current();
  assert.equal(current(), first, 'one read, one answer, for the life of the process');
  assert.equal(first.key.keyId, Key.fromHex(KEY_HEX).keyId);
  assert.deepEqual(first.knobs, knobsFromEnv(process.env));
});

test('with the rule off nothing is taken and no text is scanned', () => {
  const out = inChild(`
    const taken = __r.redactCaptures({ token: __d.dbg('abc') });
    const text = __r.redactCaptures({ note: __d.dbg(${JSON.stringify(SK)}) });
    return { off: __r.current().knobs.off, taken, text };
  `, { SENSORIUM_NO_REDACT: '1' });
  assert.equal(out.off, true);
  assert.deepEqual(out.taken.token, { k: 'dbg', v: "'abc'", trunc: false });
  // The content half is off with it: `SENSORIUM_NO_REDACT` is one switch over
  // rule v1, not over its name half alone.
  assert.deepEqual(out.text.note, { k: 'dbg', v: `'${SK}'`, trunc: false });
});

test('an unkeyed recorder still takes the value and says the digest is absent', () => {
  // "No key" must mean "redacted, with no digest to compare", never
  // "plaintext": the failure direction of this control is a lost fact.
  const out = inChild("return __r.redactCaptures({ token: __d.dbg('abc') });");
  assert.deepEqual(out.token,
    { k: 'dbg', v: REDACTED, trunc: false, redacted: { by: 'name', digest: null } });
});

test('an inspected text holding a secret is replaced span by span', () => {
  // The CONTENT half, where a name fires on nothing: the span goes, the
  // sentence around it stays, and there is no digest — a partial cannot
  // honestly commit to the whole.
  const capture = bag(redactCaptures({ note: dbg(`key=${SK} rest`) }).note);
  assert.equal(capture.v, `'key=${REDACTED} rest'`);
  assert.deepEqual(capture.redacted, { by: 'content', digest: null });
  assert.equal(capture.trunc, false);
});

test('a message holding a secret is replaced the same way', () => {
  const out = exc(new Error(`bad ${SK}`), 'throw');
  assert.equal(out.msg, `bad ${REDACTED}`);
  assert.deepEqual(out.redacted, { by: 'content', digest: null });
  assert.equal(out.type, 'Error');
});

test('a capture with nothing in it to find carries no redacted key', () => {
  // The flag is written on a CHANGE, never on a match: an absent key is what
  // tells a reader the text is the program's own, whole.
  assert.equal('redacted' in redactCaptures({ rate: dbg('7') }).rate, false);
  assert.equal('redacted' in exc(new Error('plain'), 'throw'), false);
});

test('a value whose text also holds a secret is digested as the program had it', () => {
  // The two operations never stand together on one capture (§2.3), and the
  // NAME rule decides which: a value it takes has no text left to scan. The
  // order is load-bearing — a digest taken after the content rule had
  // replaced the span would be an HMAC of the marker, which is a CONSTANT,
  // and two different secrets would then carry one identity and read as the
  // same value. `redact_values.named` and the Rust runtime's tag-4 delta
  // take the same order, for the same reason.
  const out = bag(redactCaptures({ apiKey: dbg(SK) }).apiKey);
  assert.equal(out.v, REDACTED);
  assert.equal(out.redacted.by, 'name');
  assert.equal(out.redacted.digest, Key.fromHex(KEY_HEX).digest(`'${SK}'`));
  assert.notEqual(out.redacted.digest, Key.fromHex(KEY_HEX).digest(`'${REDACTED}'`));
});
