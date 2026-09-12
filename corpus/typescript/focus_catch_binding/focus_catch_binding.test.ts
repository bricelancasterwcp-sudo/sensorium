import { expect, test } from 'vitest';

import { attempts } from './retry';

test('a bad key is counted', () => {
  expect(attempts(['k-1', 'oops'])).toBe(1);
});
