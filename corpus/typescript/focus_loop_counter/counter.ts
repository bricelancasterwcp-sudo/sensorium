// Seeded bug: the loop runs over `xs.slice(1)`, so the first reading is never
// counted and the total is short by exactly one of them. The per-iteration
// head row is what shows it: `v` takes only the values the loop actually saw.
export function accumulate(xs: number[]): number {
  let total = 0;
  for (const v of xs.slice(1)) {   // BUG: the first reading is skipped
    total += v;
  }
  return total;
}
