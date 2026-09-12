import { expect, test } from 'vitest';

import { total } from './invoice';

test('a member order is totalled', () => {
  expect(total([1, 2], { member: true })).toBe(3);
});
