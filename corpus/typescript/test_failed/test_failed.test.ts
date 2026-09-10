import { expect, test } from 'vitest';

import { total } from './order';

test('an empty order totals zero', () => {
  expect(total([])).toBe(0);    // the throw reaches the harness
});
