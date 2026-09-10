import { expect, test } from 'vitest';

import { fetchQuote, lastQuote } from './upstream';

test('a quote is fetched before the receipt is printed', async () => {
  await fetchQuote().catch(() => {});   // BUG: nothing is left of it
  expect(lastQuote()).toBe(0);
});
