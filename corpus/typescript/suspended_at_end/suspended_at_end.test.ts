import { expect, test } from 'vitest';

import { awaitToken, tokenAge } from './fetcher';

test('a token is fetched', { timeout: 200 }, async () => {
  const token = await awaitToken();
  expect(token).toBe('t');
  expect(tokenAge()).toBe(0);
});
