import { beforeEach, expect, test } from 'vitest';

import { reset, square } from './squares';

beforeEach(() => {
  reset();
});

test.each([
  [2, 4],
  [3, 9],
  [4, 16],
])('squares %i', (n, want) => {
  expect(square(n)).toBe(want);
});
