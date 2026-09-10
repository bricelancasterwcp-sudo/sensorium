// @vitest-environment node
// E8, the escape rule's own specimens: one `catch` clause per mention position
// spec §2.1 names, recorded by the real recorder and read back by `check.mjs`.
// The unit tests in `typescript/test/escape.test.mjs` ask the rule directly;
// this file asks the RUN, so a rule that is right and a splice that puts the
// wrong word on the wire cannot both pass.
//
// Every `// ESCAPE <id> <how>` marker names the HANDLED expected on the NEXT
// line — the `catch` keyword's — and `<how>` is the word that record must
// carry. The line numbers live here and nowhere else.
import { expect, test } from 'vitest';

/** Where the escaping shapes put what they caught. */
const kept: unknown[] = [];
let last: unknown = null;

/** Two sinks that are not `console`: one call, one closure store. */
function notify(_reason: unknown): void {}
function report(_fields: Record<string, unknown>): void {}
function register(fn: () => void): void {
  kept.push(fn);
}

export function loggedBare(): string {
  try {
    throw new Error('logged_bare');
    // ESCAPE logged_bare catch
  } catch (e) {
    console.error(e);
  }
  return 'ok';
}

export function loggedTemplate(): string {
  try {
    throw new Error('logged_template');
    // ESCAPE logged_template catch
  } catch (e) {
    console.warn(`failed: ${e}`);
  }
  return 'ok';
}

export function loggedString(): string {
  try {
    throw new Error('logged_string');
    // ESCAPE logged_string catch
  } catch (e) {
    console.log(String(e));
  }
  return 'ok';
}

export function loggedProperty(): string {
  try {
    throw new Error('logged_property');
    // ESCAPE logged_property catch
  } catch (e) {
    console.debug((e as Error).message);
  }
  return 'ok';
}

export function noBinding(): string {
  try {
    throw new Error('no_binding');
    // ESCAPE no_binding catch
  } catch {
    notify('nothing to let out');
  }
  return 'ok';
}

export function escapedReturn(): string {
  try {
    throw new Error('escaped_return');
    // ESCAPE escaped_return catch_escaped
  } catch (e) {
    return (e as Error).message;
  }
}

export function escapedAssign(): string {
  try {
    throw new Error('escaped_assign');
    // ESCAPE escaped_assign catch_escaped
  } catch (e) {
    last = e;
  }
  return String(last);
}

export function escapedPush(): number {
  try {
    throw new Error('escaped_push');
    // ESCAPE escaped_push catch_escaped
  } catch (e) {
    kept.push(e);
  }
  return kept.length;
}

export function escapedCall(): string {
  try {
    throw new Error('escaped_call');
    // ESCAPE escaped_call catch_escaped
  } catch (e) {
    notify(e);
  }
  return 'ok';
}

export function escapedClosure(): string {
  try {
    throw new Error('escaped_closure');
    // ESCAPE escaped_closure catch_escaped
  } catch (e) {
    register(() => console.error(e));
  }
  return 'ok';
}

export function escapedShorthand(): string {
  try {
    throw new Error('escaped_shorthand');
    // ESCAPE escaped_shorthand catch_escaped
  } catch (e) {
    report({ e });
  }
  return 'ok';
}

export function escapedThrow(): string {
  try {
    throw new Error('escaped_throw');
    // ESCAPE escaped_throw catch_escaped
  } catch (e) {
    throw e;
  }
}

export function destructured(): string {
  try {
    throw new Error('destructured');
    // ESCAPE destructured catch_escaped
  } catch ({ message }) {
    return String(message);
  }
}

test('the four logged positions and the clause with nothing to let out', () => {
  expect(loggedBare()).toBe('ok');
  expect(loggedTemplate()).toBe('ok');
  expect(loggedString()).toBe('ok');
  expect(loggedProperty()).toBe('ok');
  expect(noBinding()).toBe('ok');
});

test('the eight positions the value escapes through', () => {
  expect(escapedReturn()).toBe('escaped_return');
  expect(escapedAssign()).toBe('Error: escaped_assign');
  expect(escapedPush()).toBe(1);
  expect(escapedCall()).toBe('ok');
  expect(escapedClosure()).toBe('ok');
  expect(escapedShorthand()).toBe('ok');
  expect(() => escapedThrow()).toThrow('escaped_throw');
  expect(destructured()).toBe('destructured');
});
