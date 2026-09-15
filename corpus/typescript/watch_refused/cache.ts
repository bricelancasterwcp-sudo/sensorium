// Seeded bug: `refresh` recomputes the value but writes it to a local that
// never reaches the cache, so `lookup` keeps answering with the stale entry.
// The per-line question -- what was `fresh` at the line after it was
// computed? -- is the natural one, and it is exactly the one this recorder
// declares it cannot answer.
const CACHE: Record<string, number> = { rate: 100 };

export function compute(slot: string): number {
  return CACHE[slot] * 2;
}

export function refresh(slot: string): number {
  const fresh = compute(slot);
  return CACHE[slot];           // BUG: the recomputed value is dropped
}

export function lookup(slot: string): number {
  return CACHE[slot];
}
