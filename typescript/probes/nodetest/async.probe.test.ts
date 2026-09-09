// E3 again, under `node --test` through `register.mjs` — the harness with no
// Vite in it. The scenarios are the ones in `src/async.probe.test.ts` and the
// expected rows are the same §1.1 rows; what differs is the naming basis. There
// is no provider here, so a task is named by the lexical title the transform
// saw: `basis: "title"`.
//
// This directory is outside vitest's `include` on purpose. Run it from
// `typescript/probes/` with `npm run probe:nodetest`, which needs
// `SENSORIUM_TIER`, `SENSORIUM_SPOOL`, `SENSORIUM_TS_ROOT` and
// `SENSORIUM_TS_PKG` in the environment — see `README.md` for the recipe.
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { test } from 'node:test';

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
  return new Promise((resolve) => setTimeout(resolve, ms));
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
  assert.equal(await a(), 4);
});

test('S2 fanout', async () => {
  assert.deepEqual(await fanout(), [10, 20]);
});

test('S3 timer', async () => {
  assert.equal(await viaTimer(), 7);
});

test('S4 emitter', async () => {
  assert.equal(await viaEmitter(), 2);
});

test('T1 control', async () => {
  assert.equal(await a(), 4);
});

test('T2 control', async () => {
  assert.equal(await a(), 4);
});
