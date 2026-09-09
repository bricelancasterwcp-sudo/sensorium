// @vitest-environment node
// THROWAWAY E3 probe. Expected rows: spike doc §1.1. Rows of functions not
// named there (sleep, the promise executors, timer callbacks) are ignored by
// the checker; `handler` is nested, so its qualname ends in `.handler`.
import { test, expect } from 'vitest';
import { EventEmitter } from 'node:events';

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

function sleep(ms: number): Promise<void> {
  return new Promise((res) => setTimeout(res, ms));
}
async function p(n: number): Promise<number> {
  await sleep(1);
  return n * 10;
}
async function fanout(): Promise<number[]> {
  return await Promise.all([p(1), p(2)]);
}

function work(): number {
  return 7;
}
async function viaTimer(): Promise<number> {
  return await new Promise<number>((resolve) => {
    setTimeout(() => resolve(work()), 0);
  });
}

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
test('T1 control', async () => {
  expect(await a()).toBe(4);
});
test('T2 control', async () => {
  expect(await a()).toBe(4);
});
