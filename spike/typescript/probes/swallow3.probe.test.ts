// @vitest-environment node
// THROWAWAY E8 probe, shape 3: a rejection nobody handles. Expected: vitest
// itself reports it as an unhandled error (the file may be marked failed);
// the runtime's unhandledRejection listener records a RAISE with
// basis "unhandledRejection".
import { test } from 'vitest';

export function shape3(): void {
  void Promise.reject(new Error('e3'));
}

test('shape3 unhandled rejection', async () => {
  shape3();
  await new Promise((r) => setTimeout(r, 5));
});
