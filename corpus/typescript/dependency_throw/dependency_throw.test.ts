import { expect, test } from 'vitest';

import { readSettings } from './settings';

test('a settings file is read', () => {
  expect(Object.keys(readSettings('{'))).toHaveLength(0);
});
