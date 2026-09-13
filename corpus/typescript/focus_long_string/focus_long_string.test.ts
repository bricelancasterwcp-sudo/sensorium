import { expect, test } from 'vitest';

import { pad } from './long';

test('the 100-character string comes back when the lengths add up', () => {
  expect(pad(201)).toHaveLength(100);
});
