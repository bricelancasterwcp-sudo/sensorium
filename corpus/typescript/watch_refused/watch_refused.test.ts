import { expect, test } from 'vitest';

import { lookup, refresh } from './cache';

test('a refreshed rate is read back', () => {
  refresh('rate');
  expect(lookup('rate')).toBe(100);
});
