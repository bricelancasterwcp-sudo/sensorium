import { expect, test } from 'vitest';

import { quotaOrDefault } from './quota';

test('a quota is read from the settings string', () => {
  expect(quotaOrDefault('eleven')).toBe(10);
});
