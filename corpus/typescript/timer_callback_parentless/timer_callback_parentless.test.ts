import { expect, test } from 'vitest';

import { delay, enqueue, pending, sweep } from './sweeper';

test('a sweep is scheduled and not awaited', async () => {
  enqueue(1);
  setTimeout(sweep, 5);
  await delay(40);
  expect(pending()).toBe(1);
});
