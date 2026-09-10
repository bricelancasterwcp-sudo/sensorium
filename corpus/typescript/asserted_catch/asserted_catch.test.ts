import { expect, test } from 'vitest';

import { validate } from './validate';

test('a negative amount is rejected', () => {
  let reached = false;
  try {
    validate(-1);
  } catch (e) {
    reached = true;
    expect((e as Error).message).toBe('amount must be positive');
  }
  expect(reached).toBe(true);
});
