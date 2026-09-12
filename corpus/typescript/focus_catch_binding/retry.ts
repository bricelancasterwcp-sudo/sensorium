// Seeded bug: the `catch` bumps a counter and drops the reason, so the report
// says one key failed and nothing says why it did. The reason is alive for
// exactly one statement -- the catch block's own entry -- and the `try`
// statement's own row is where this recorder says it died again.
export function parseKey(key: string): number {
  if (!key.startsWith('k-')) {
    throw new Error(`bad key: ${key}`);
  }
  return Number(key.slice(2));
}

export function attempts(keys: string[]): number {
  let count = 0;
  for (const key of keys) {
    try {
      parseKey(key);
    } catch (e) {
      count += 1;               // BUG: `e` is counted and never recorded
    }
  }
  return count;
}
