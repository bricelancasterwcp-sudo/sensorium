import { expect, test } from 'vitest';

import { settle } from './finally';

test('a finally runs after the return has chosen its value', () => {
  expect(settle(true)).toBe(1);
});
