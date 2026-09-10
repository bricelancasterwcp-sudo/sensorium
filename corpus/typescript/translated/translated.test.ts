import { expect, test } from 'vitest';

import { Wrapped, decodeOrWrap } from './decode';

test('a decode failure reaches the caller as a wrapper', () => {
  expect(() => decodeOrWrap('{')).toThrow(Wrapped);
});
