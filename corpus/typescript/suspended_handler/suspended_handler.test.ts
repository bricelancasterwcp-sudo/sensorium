import { test } from 'vitest';

import { drain } from './queue';

test('a queue is drained', { timeout: 200 }, async () => {
  await drain();
});
