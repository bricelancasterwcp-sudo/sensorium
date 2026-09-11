import { test } from 'vitest';

import { load } from './loader';

test('a disk failure is logged before it fails the suite', () => {
  try {
    load();
  } catch (e) {
    console.error(e);
    throw e;
  }
});
