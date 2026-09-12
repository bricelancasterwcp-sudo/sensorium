import { expect, test } from 'vitest';

import { accumulate } from './counter';

test('three readings are accumulated', () => {
  expect(accumulate([1, 2, 3])).toBe(5);
});
