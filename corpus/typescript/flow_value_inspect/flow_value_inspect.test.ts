import { expect, test } from 'vitest';

import { reading } from './grid';

test('an unreadable cell is counted', () => {
  expect(reading('A1x')).toBe(0);
});
