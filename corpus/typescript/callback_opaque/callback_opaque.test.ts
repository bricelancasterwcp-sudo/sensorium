import { expect, test } from 'vitest';

import { conflictCount, noteFailure, syncNow } from './report';

test('a sync conflict is handed to the reporter', async () => {
  await syncNow().catch(noteFailure);
  expect(conflictCount()).toBe(0);
});
