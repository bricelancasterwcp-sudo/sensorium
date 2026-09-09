// @vitest-environment node
// The naming rule, `.each` branch (design §4, D4). The transform sees a title
// that is a template, not this row's name, so the cross-check is off and the
// harness's own name is taken as given: three TASK records named
// `adds 1 + 2 = 3`-style, `basis: "vitest"`, `conflict: false`. A recorder that
// wrote the template three times would name three different tests the same.
import { expect, test } from 'vitest';

export function add(a: number, b: number): number {
  return a + b;
}

test.each([
  { a: 1, b: 2, expected: 3 },
  { a: 2, b: 3, expected: 5 },
  { a: 4, b: 5, expected: 9 },
])('adds $a + $b = $expected', ({ a, b, expected }) => {
  expect(add(a, b)).toBe(expected);
});
