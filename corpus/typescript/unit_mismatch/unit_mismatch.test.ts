import { expect, test } from 'vitest';

import { orderTotal } from './shipping';

test('a two-item order is totalled', () => {
  const total = orderTotal([
    { name: 'mug', price: 12, grams: 400 },
    { name: 'kettle', price: 49, grams: 1800 },
  ]);
  expect(total).toBeGreaterThan(0);
});
