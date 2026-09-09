import { expect, test } from 'vitest';

import { lastSeen, update } from './store';

// Two writers, one for each concurrent test, so a question can name the
// activation it means without depending on which of them ran first.
async function writerA(): Promise<number> {
  update('last_seen', 1);
  await Promise.resolve();
  return update('last_seen', 2);   // BUG: both writers own this one key
}

async function writerB(): Promise<number> {
  update('last_seen', 1);
  await Promise.resolve();
  return update('last_seen', 2);   // BUG: both writers own this one key
}

test.concurrent('writer A writes twice', async () => {
  expect(await writerA()).toBe(2);
});

test.concurrent('writer B writes twice', async () => {
  expect(await writerB()).toBe(2);
  expect(lastSeen()).toBe(2);
});
