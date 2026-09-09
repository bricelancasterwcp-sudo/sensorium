import { expect, test } from 'vitest';

import { choose } from './counter';

test('a side is chosen', () => {
  expect(['L', 'R']).toContain(choose());
});
