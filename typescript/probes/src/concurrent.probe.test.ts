// @vitest-environment node
// The documented hazard, recorded rather than gated: two `test.concurrent`
// bodies run interleaved, so `expect.getState().currentTestName` at the moment a
// task opens may name the OTHER test. The transform saw a plain string literal
// here, so the runtime can cross-check it — and when the two disagree it keeps
// the lexical title and says `conflict: true`. `check.mjs` prints how many
// conflicts this box produced; the number is a report, not a threshold.
import { expect, test } from 'vitest';

export async function slow(n: number): Promise<number> {
  await new Promise((resolve) => setTimeout(resolve, 10 * n));
  return n;
}

test.concurrent('concurrent one', async () => {
  expect(await slow(1)).toBe(1);
});

test.concurrent('concurrent two', async () => {
  expect(await slow(2)).toBe(2);
});
