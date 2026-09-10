import { expect, test } from 'vitest';

import { syncNow } from './sync';

const seen: unknown[] = [];

test('a sync conflict is collected for the report', async () => {
  await syncNow().catch((e) => {
    seen.push(e);               // the reason leaves the callback
  });
  expect(seen).toHaveLength(1);
});
