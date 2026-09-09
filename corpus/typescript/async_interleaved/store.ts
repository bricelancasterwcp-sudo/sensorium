// Seeded bug: two concurrent tests write the same key of a shared store, so
// the second writer silently overwrites the first. Nothing looks wrong -- a
// value is there -- it is just the wrong test's.
//
// The values carry no identity. Both writers write 1 and then 2, so the
// surviving 2 says nothing about who wrote it, and neither does a print of
// every write: `update` is handed a number, never a name.
const STORE: Record<string, number> = {};

export function update(key: string, value: number): number {
  STORE[key] = value;
  return STORE[key];
}

export function lastSeen(): number {
  return STORE.last_seen;
}
