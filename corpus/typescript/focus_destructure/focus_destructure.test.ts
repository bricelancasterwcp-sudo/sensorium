import { expect, test } from 'vitest';

import { unpack } from './unpack';

test('a payload is unpacked', () => {
  expect(unpack({ id: 'p-1', sizes: [2], tag: 'x' })).toBe(2);
});
