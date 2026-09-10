import { expect, test } from 'vitest';

import { loadConfig } from './config';

test('a config file is loaded', () => {
  expect(loadConfig('nine').retries).toBe(3);
});
