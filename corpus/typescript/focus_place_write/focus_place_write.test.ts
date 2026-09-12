import { expect, test } from 'vitest';

import { bump } from './state';

test('a bumped state is read back', () => {
  const state = { x: 0 };
  expect(bump(state)).toBe(0);
  expect(state.x).toBe(5);
});
