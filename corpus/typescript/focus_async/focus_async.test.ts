import { expect, test } from 'vitest';

import { load, peek } from './cache';

test('a rate is loaded and cached', async () => {
  const pending = load('rate');
  expect(peek('rate')).toBe(0);
  expect(await pending).toBe(400);
});
