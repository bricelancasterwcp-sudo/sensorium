import { describe, expect, test } from "vitest";

describe("options", { concurrent: true }, () => {
  test("times out", { timeout: 100 }, () => {
    expect(1).toBe(1);
  }, 5000);
}, 1000);

test("multi-line options are left alone", {
  timeout: 100,
}, () => {
  expect(2).toBe(2);
});

test("a concise body with options is left alone", { timeout: 1 }, () => expect(3).toBe(3));
