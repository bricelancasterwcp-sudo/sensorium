// Seeded bug: the placeholder is published to the cache BEFORE the await and
// the real value only after it, so anything that reads the cache during the
// suspension gets a zero that looks like an answer. Which side of the
// suspension a write happened on is the whole question, and it is the one an
// ordered list of writes cannot answer -- the timeline's `~ YIELD` and
// `~ RESUME` are where the two sides part.
const CACHE = new Map<string, number>();

async function fetchRate(key: string): Promise<number> {
  await Promise.resolve();
  return key.length * 100;
}

export function peek(key: string): number | undefined {
  return CACHE.get(key);
}

export async function load(key: string): Promise<number> {
  const placeholder = 0;
  CACHE.set(key, placeholder);  // BUG: published before the value exists
  const fetched = await fetchRate(key);
  CACHE.set(key, fetched);
  return fetched;
}
