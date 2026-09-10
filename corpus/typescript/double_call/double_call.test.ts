import { expect, test } from 'vitest';

import { submit } from './orders';

test('a slow order is submitted', () => {
  expect(submit({ id: 'A-1', amount: 40, slow: true })).toBe(80);
});
