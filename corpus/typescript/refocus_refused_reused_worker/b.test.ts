import { expect, test } from 'vitest';
import { one } from './shared';

test('b > one is still one', () => {
  expect(one()).toBe(1);
});
