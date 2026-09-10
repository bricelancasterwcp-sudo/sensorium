// @vitest-environment node
// E3, the rung-0 question: is every row attributed to the task that started it?
// Four scenarios and a negative control, expected rows in the spike's §1.1.
// Functions this file needs but §1.1 does not name — `sleep`, the promise
// executors, the timer callbacks, the test callbacks themselves — are ignored by
// `check.mjs`; `handler` is nested, so its qualname ends in `.handler` and the
// checker matches on the last segment.
import { EventEmitter } from 'node:events';
import { expect, test } from 'vitest';

// S1: an await chain. c parks on a resolved promise, so all three frames are
// parked before any of them resumes.
async function c(): Promise<number> {
  await Promise.resolve();
  return 2;
}

async function b(): Promise<number> {
  const v = await c();
  return v + 1;
}

async function a(): Promise<number> {
  const v = await b();
  return v + 1;
}

// S2: a fan-out. The two `p` frames must not nest under one another — that is
// what the pop-on-YIELD rule buys.
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function p(n: number): Promise<number> {
  await sleep(1);
  return n * 10;
}

async function fanout(): Promise<number[]> {
  return await Promise.all([p(1), p(2)]);
}

// S3: a timer continuation. `CALL work` runs from the timer queue and must
// still carry this scenario's task.
function work(): number {
  return 7;
}

async function viaTimer(): Promise<number> {
  return await new Promise<number>((resolve) => {
    setTimeout(() => resolve(work()), 0);
  });
}

// S4: an emitter callback, once synchronously and once from a timer.
async function viaEmitter(): Promise<number> {
  const em = new EventEmitter();
  let n = 0;
  function handler(): void {
    n += 1;
  }
  em.on('x', handler);
  em.emit('x');
  await new Promise<void>((resolve) => {
    setTimeout(() => {
      em.emit('x');
      resolve();
    }, 0);
  });
  return n;
}

test('S1 chain', async () => {
  expect(await a()).toBe(4);
});

test('S2 fanout', async () => {
  expect(await fanout()).toEqual([10, 20]);
});

test('S3 timer', async () => {
  expect(await viaTimer()).toBe(7);
});

test('S4 emitter', async () => {
  expect(await viaEmitter()).toBe(2);
});

// The negative control: two consecutive tests running the same scenario. A
// runtime keyed on "the first store ever created" passes S1-S4 and fails here.
test('T1 control', async () => {
  expect(await a()).toBe(4);
});

test('T2 control', async () => {
  expect(await a()).toBe(4);
});
