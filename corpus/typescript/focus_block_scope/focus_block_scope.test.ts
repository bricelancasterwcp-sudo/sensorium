import { expect, test } from 'vitest';

import { total } from './scope';

test('a member order is discounted', () => {
  expect(total([40, 50], true)).toBe(81);
});
