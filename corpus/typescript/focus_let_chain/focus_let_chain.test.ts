import { expect, test } from 'vitest';

import { fill } from './chain';

test('a large order is priced', () => {
  expect(fill(60, 2)).toBe(120);
});
