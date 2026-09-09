// @vitest-environment node
// A continuation that runs when its scheduler has already yielded. `onTimer` is
// called from the timer queue with its task's stack empty, so its CALL opens a
// parentless frame — `p: null` — while still carrying the task's id. The
// converter writes `caller: "untraced"` for it; whether a scheduling frame
// should be recorded as a causal parent is a design question the spike left
// open, and this probe is the evidence it stays answerable.
import { expect, test } from 'vitest';

export function tick(): number {
  return 3;
}

export function schedule(): Promise<number> {
  return new Promise<number>((resolve) => {
    function onTimer(): void {
      resolve(tick());
    }
    setTimeout(onTimer, 0);
  });
}

test('a timer callback opens a parentless frame', async () => {
  expect(await schedule()).toBe(3);
});
