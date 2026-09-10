import { describe, expect, it, suite, test } from "vitest";

describe("math", () => {
  test("adds", () => {
    expect(1 + 1).toBe(2);
  });

  test.todo("multiplies");

  test("retries", () => {}, { retry: 2 });

  test(name, () => {});
});

suite("edges", () => {});
