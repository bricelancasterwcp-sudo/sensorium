// @vitest-environment node
// E8, four of the five swallow shapes. Shape 3 — a rejection nobody handles —
// lives in `swallow3.probe.test.ts`, because vitest reports it as an error on
// the file that raises it and would drag these four down with it.
//
// Every `// SWALLOW <shape> <kind> <how>` marker names a record expected on the
// NEXT line: `raise` is a RAISE at the `throw` keyword's line, `handled` a
// HANDLED at the `catch` keyword's — or, for the callback sink, at the `.catch`
// property's. `check.mjs` reads the markers, so the line numbers live in one
// place only.
import { expect, test } from 'vitest';

export function shape1(): string {
  try {
    // SWALLOW shape1 raise throw
    throw new Error('e1');
    // SWALLOW shape1 handled sink_empty_catch
  } catch {}
  return 'ok';
}

export async function shape2(): Promise<string> {
  // SWALLOW shape2 handled sink_empty_catch_callback
  await Promise.reject(new Error('e2')).catch(() => {});
  return 'ok';
}

export function shape4(): string {
  try {
    // SWALLOW shape4 raise throw
    throw 'not-an-error';
    // SWALLOW shape4 handled catch
  } catch (e) {
    return String(e);
  }
}

export function shape5(): string {
  try {
    try {
      // SWALLOW shape5 raise throw
      throw new Error('e5');
      // SWALLOW shape5 handled catch
    } catch (e) {
      // SWALLOW shape5 raise throw
      throw e;
    }
    // SWALLOW shape5 handled catch
  } catch (e2) {
    return (e2 as Error).message;
  }
}

test('shape1 an empty catch clause', () => {
  expect(shape1()).toBe('ok');
});

test('shape2 an empty catch callback', async () => {
  expect(await shape2()).toBe('ok');
});

test('shape4 a thrown string', () => {
  expect(shape4()).toBe('not-an-error');
});

test('shape5 a rethrow keeps the serial', () => {
  expect(shape5()).toBe('e5');
});
