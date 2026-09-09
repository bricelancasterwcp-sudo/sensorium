// @vitest-environment node
// THROWAWAY E8 probe, shapes 1, 2, 4, 5 (shape 3 lives in swallow3.probe.test.ts
// because an unhandled rejection makes vitest report the file as errored).
import { test, expect } from 'vitest';

export function shape1(): string {
  try {
    throw new Error('e1');
  } catch {}
  return 'ok';
}

export async function shape2(): Promise<string> {
  await Promise.reject(new Error('e2')).catch(() => {});
  return 'ok';
}

export function shape4(): string {
  try {
    throw 'not-an-error';
  } catch (e) {
    return String(e);
  }
}

export function shape5(): string {
  try {
    try {
      throw new Error('e5');
    } catch (e) {
      throw e;
    }
  } catch (e2) {
    return (e2 as Error).message;
  }
}

test('shape1 empty catch clause', () => {
  expect(shape1()).toBe('ok');
});
test('shape2 empty catch callback', async () => {
  expect(await shape2()).toBe('ok');
});
test('shape4 throw a string', () => {
  expect(shape4()).toBe('not-an-error');
});
test('shape5 rethrow keeps the serial', () => {
  expect(shape5()).toBe('e5');
});
