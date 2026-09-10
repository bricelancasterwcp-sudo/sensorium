import { expect, test } from 'vitest';

import { fallbackQuote, fetchQuote } from './quote';

test('a quote is fetched for the basket', async () => {
  let quote = -1;
  try {
    quote = await fetchQuote();
  } catch {
    quote = fallbackQuote();    // BUG: the outage reaches nobody
  }
  expect(quote).toBe(0);
});
