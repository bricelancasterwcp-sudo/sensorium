// @vitest-environment node
// The lexical chain. Two synchronous `describe`s stand while their callbacks
// run, so the task registered inside them knows its chain at registration time
// and the TASK is named `outer > inner > leaf` — which is also what vitest's own
// provider says, so the two agree and `basis` is `vitest`.
//
// The describes are synchronous on purpose (P11): an `async` describe callback
// registers its tests after the lexical chain has popped, and the runtime's
// ledger says so. That is a property of the harness, not a defect to paper over.
import { expect, describe, test } from 'vitest';

export function leafWork(): number {
  return 42;
}

describe('outer', () => {
  describe('inner', () => {
    test('leaf', () => {
      expect(leafWork()).toBe(42);
    });
  });
});
