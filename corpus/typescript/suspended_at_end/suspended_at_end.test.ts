import { expect, test } from 'vitest';

import { awaitPayload, payloadAge } from './fetcher';

test('a payload is fetched', { timeout: 200 }, async () => {
  const payload = await awaitPayload();
  expect(payload).toBe('t');
  expect(payloadAge()).toBe(0);
});
