import { expect, test } from 'vitest';
import { fill } from './fill';

test('fill > returns two', () => {
  expect(fill()).toBe(2);
});
