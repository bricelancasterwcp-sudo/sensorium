// @vitest-environment node
// E8, shape 3: a rejection nobody handles. It lives alone because vitest reports
// an unhandled rejection as an error against the file it happened in — the run
// goes red, and that is the point: the spool must still carry the UNHANDLED
// record, written by the runtime's own `process.on('unhandledRejection')`
// listener, outside every frame and every task. `check.mjs`, not vitest's exit
// status, is this probe's gate.
import { test } from 'vitest';

export function shape3(): void {
  void Promise.reject(new Error('e3'));
}

test('shape3 a rejection nobody handles', async () => {
  shape3();
  await new Promise((resolve) => setTimeout(resolve, 5));
});
