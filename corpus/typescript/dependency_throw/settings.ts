// Seeded bug: the failure is born in a DEPENDENCY -- `JSON.parse`, which this
// recorder never instrumented -- and dies in an empty `catch` here, so the
// only row about it is the handler. There is no RAISE to pair it with and no
// site to name as the throw, and the verdict says exactly that: the failure
// was born outside traced code, and this clause is where it stopped.
export function readSettings(raw: string): Record<string, unknown> {
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return {};                  // BUG: a malformed file reads as empty
  }
}
