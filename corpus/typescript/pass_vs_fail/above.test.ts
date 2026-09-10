import { expect, test } from 'vitest';

import { price } from './pricing';

test('an order at the tier boundary earns gold', () => {
  expect(price(1001, 100)).toBe(80);
});
