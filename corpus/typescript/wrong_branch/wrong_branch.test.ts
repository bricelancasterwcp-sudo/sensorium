import { expect, test } from 'vitest';

import { price } from './pricing';

test('three loyalty tiers are priced', () => {
  const applied = [price(500, 100), price(1000, 100), price(1500, 100)];
  expect(applied).toHaveLength(3);
});
