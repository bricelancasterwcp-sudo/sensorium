import { expect, test } from 'vitest';

import { safeScan } from './scan';

test('an empty document scans to zero', () => {
  expect(safeScan('')).toBe(0);
});
