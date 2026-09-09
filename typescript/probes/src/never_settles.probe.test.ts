// @vitest-environment node
// A frame that never comes back. `parks` awaits a promise with no resolver, so
// its YIELD is the last thing it ever says: no RETURN, no UNWIND. vitest fails
// the test on its timeout and moves on, and the container still ends with an
// EXIT — a spool that stops mid-frame is a truthful spool, not a broken one.
// This file makes `vitest run` exit non-zero on purpose.
import { test } from 'vitest';

export async function parks(): Promise<never> {
  await new Promise<never>(() => {});
  throw new Error('unreachable');
}

test('parks forever', { timeout: 200 }, async () => {
  await parks();
});
