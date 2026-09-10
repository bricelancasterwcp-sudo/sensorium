import { expect, test } from 'vitest';

import { commit } from './ledger';

test('a commit reports the rows it wrote', () => {
  expect(commit(3)).toBe(3);
});
