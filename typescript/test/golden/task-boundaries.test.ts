import { test } from "vitest";

test(() => "c", { timeout: 1 }, fn2);

test("d", { timeout: 1 }, flag ? base : () => go());

async function register(): Promise<void> {
  test("e", { timeout: 1 }, await mk());
}

test(() => "f1", fn2);

test("f2", flag ? base : () => go());

async function registerTwo(): Promise<void> {
  test("f3", await mk());
}
