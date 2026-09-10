// @vitest-environment node
// E8's swallow shapes, 1-12 but for shape 3 — a rejection nobody handles —
// which lives in `swallow3.probe.test.ts`, because vitest reports it as an
// error on the file that raises it and would drag the rest down with it.
//
// Shapes 6-12 are rung 2's: the words a `how` can now carry once the escape
// rule, the rejection-callback wrapper and the `finally` sink are spliced
// (spec §2.1-§2.3). Shapes 4 and 5 are rung 1's, and their markers moved with
// the rule: `return String(e)` is an escape now and not a swallow, and shape 5's
// OUTER clause is one for the same reason. Its inner `throw e` is not -- ruled
// 2026-09-10 (Task 6): a bare rethrow is a traced exit, the clause reads
// `catch`, and the rule module reads the same-serial pair as a hop.
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
    // SWALLOW shape4 handled catch_escaped
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
    // SWALLOW shape5 handled catch_escaped
  } catch (e2) {
    return (e2 as Error).message;
  }
}

/** Where shape 10's handler puts the reason it was given, so it escapes. */
const seen: unknown[] = [];

/** Shape 11's handler: defined elsewhere, so the splice says nothing about it. */
function handler(): void {}

export function shape6(): string {
  try {
    // SWALLOW shape6 raise throw
    throw new Error('e6');
    // SWALLOW shape6 handled catch
  } catch (e) {
    console.error(e);
  }
  return 'ok';
}

export function shape7(): string {
  try {
    // SWALLOW shape7 raise throw
    throw new Error('e7');
    // SWALLOW shape7 handled catch_escaped
  } catch (e) {
    return String(e);
  }
}

export async function shape8(): Promise<string> {
  // SWALLOW shape8 handled sink_empty_catch_callback
  await Promise.reject(new Error('e8')).catch(function () {});
  return 'ok';
}

export async function shape9(): Promise<string> {
  // SWALLOW shape9 handled catch_callback
  await Promise.reject(new Error('e9')).catch((e) => {
    console.warn(e);
  });
  return 'ok';
}

export async function shape10(): Promise<number> {
  // SWALLOW shape10 handled catch_callback_escaped
  await Promise.reject(new Error('e10')).catch((e) => {
    seen.push(e);
  });
  return seen.length;
}

export async function shape11(): Promise<string> {
  // SWALLOW shape11 handled catch_callback_opaque
  await Promise.reject(new Error('e11')).catch(handler);
  return 'ok';
}

export function shape12(): string {
  try {
    // SWALLOW shape12 raise throw
    throw new Error('e12');
    // SWALLOW shape12 handled sink_finally_return
  } finally {
    return 'ok';
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

test('shape6 a logged catch swallowed it', () => {
  expect(shape6()).toBe('ok');
});

test('shape7 a rendering of it reached the caller', () => {
  expect(shape7()).toBe('Error: e7');
});

test('shape8 an empty function-expression callback', async () => {
  expect(await shape8()).toBe('ok');
});

test('shape9 a callback that logs its reason', async () => {
  expect(await shape9()).toBe('ok');
});

test('shape10 a callback that keeps its reason', async () => {
  expect(await shape10()).toBe(1);
});

test('shape11 a handler defined elsewhere', async () => {
  expect(await shape11()).toBe('ok');
});

test('shape12 a finally that returns discards the throw', () => {
  expect(shape12()).toBe('ok');
});
