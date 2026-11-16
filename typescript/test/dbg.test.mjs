// Promises and Node timers are summarized. `inspect` of a Timeout prints
// `_idleNext` and symbols, and `inspect` of a settled promise prints the
// value; neither text is what a capture carries. Ordinary values are unchanged.
import assert from 'node:assert/strict';
import test from 'node:test';

import { dbg } from '../src/dbg.mjs';

const FORBIDDEN = ['_idleNext', '_idlePrev', '_idleTimeout', 'Symbol('];

/**
 * @param {{k: string, v?: string, trunc?: boolean}} cap
 * @param {string} text
 */
function short(cap, text) {
  assert.equal(cap.k, 'dbg');
  assert.equal(cap.v, text);
  assert.equal(cap.trunc, false);
  assert.ok(text.length < 80, text);
  for (const word of FORBIDDEN) assert.equal(text.includes(word), false, text);
}

test('a promise or a timer is a short summary', () => {
  short(dbg(new Promise(() => {})), 'Promise { <pending> }');
  short(dbg(Promise.resolve(1)), 'Promise { <fulfilled> }');
  short(dbg(Promise.resolve('y'.repeat(5000))), 'Promise { <fulfilled> }');

  const rejected = Promise.reject(new Error('x'));
  // The handler is on this promise. `.catch` returns a different one.
  rejected.catch(() => {});
  short(dbg(rejected), 'Promise { <rejected> }');
  const long = Promise.reject(new Error('z'.repeat(500)));
  long.catch(() => {});
  short(dbg(long), 'Promise { <rejected> }');
  // The derived promise is still pending when `dbg` reads it.
  short(dbg(Promise.reject(new Error('x')).catch(() => {})), 'Promise { <pending> }');

  const timer = setTimeout(() => {}, 1000);
  const interval = setInterval(() => {}, 1000);
  try {
    short(dbg(timer), 'Timeout');
    short(dbg(interval), 'Timeout');
    short(dbg(Promise.resolve(timer)), 'Promise { <fulfilled> }');
  } finally {
    clearTimeout(timer);
    clearInterval(interval);
  }

  if (typeof setImmediate === 'function') {
    const immediate = setImmediate(() => {});
    try {
      short(dbg(immediate), 'Immediate');
    } finally {
      clearImmediate(immediate);
    }
  }
});

test('ordinary values are not summarized', () => {
  assert.deepEqual(dbg('hello'), { k: 'dbg', v: "'hello'", trunc: false });
  const obj = dbg({ a: 1 });
  assert.equal(obj.k, 'dbg');
  assert.equal(obj.v, '{ a: 1 }');
  assert.equal(obj.trunc, false);
  assert.equal(obj.type, 'Object');
  const plain = dbg({ _idleTimeout: 1, a: 2 });
  assert.equal(plain.k, 'dbg');
  assert.equal(plain.trunc, false);
  assert.equal(plain.v, '{ _idleTimeout: 1, a: 2 }');
  const thenable = dbg({ then() {}, a: 1 });
  assert.equal(thenable.k, 'dbg');
  assert.equal(thenable.v?.includes('a: 1'), true);
  assert.equal(thenable.v?.startsWith('Promise'), false);
});
