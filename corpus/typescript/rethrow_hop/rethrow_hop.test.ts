import { expect, test } from 'vitest';

import { boot } from './disk';

test('a boot falls back when the disk is offline', () => {
  expect(boot()).toBe('defaults');
});
