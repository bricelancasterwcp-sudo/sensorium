import { describe, expect, it, test } from "vitest";

it.concurrent("subtracts", async () => {
  expect(await sub(2, 1)).toBe(1);
});

test.each([1, 2])("doubles %i", (n: number) => {
  expect(n * 2).toBe(n + n);
});

test.each`
  a    | b
  ${1} | ${2}
`("adds $a", ({ a, b }: { a: number; b: number }) => {
  expect(a + b).toBe(3);
});

describe.each([["a"], ["b"]])("suite %s", (letter: string) => {
  it("is a letter", () => {
    expect(letter.length).toBe(1);
  });
});
