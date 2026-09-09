import { expect, test } from 'vitest';

import { loadSettings, retriesOf, tune } from './settings';

test('two callers load their own settings', () => {
  const mine = loadSettings();
  const theirs = loadSettings();
  tune(mine);
  expect(retriesOf(theirs)).toBe(9);
});
