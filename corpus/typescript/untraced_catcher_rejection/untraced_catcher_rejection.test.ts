import { expect, test } from 'vitest';

import { fetchThing } from './network';

test('a fetch reports the outage as a rejection', async () => {
  await expect(fetchThing()).rejects.toThrow('offline');
});
