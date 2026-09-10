import { expect, test } from 'vitest';

import { cacheAge, delay, startRefresh } from './refresh';

test('a background refresh is started', async () => {
  startRefresh();
  await delay(20);
  expect(cacheAge()).toBe(0);
});
