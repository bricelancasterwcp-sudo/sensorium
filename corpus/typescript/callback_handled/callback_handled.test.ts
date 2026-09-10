import { expect, test } from 'vitest';

import { refreshToken, tokenAge } from './token';

test('a token is refreshed in the background', async () => {
  await refreshToken().catch((e) => {
    console.warn(e);            // BUG: the log is all that is left
  });
  expect(tokenAge()).toBe(0);
});
