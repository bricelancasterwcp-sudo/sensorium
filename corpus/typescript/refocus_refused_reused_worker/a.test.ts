import { expect, test } from 'vitest';
import { one } from './shared';

test('a > one is one', () => {
  expect(one()).toBe(1);
});
