import { expect, test } from 'vitest';

import { handle, secret } from './secret';

test('the token length is measured, never printed', () => {
  expect(handle(secret())).toBe(40);
});
