// The `.mts` probe's library, typed on both sides of the import: a hook that
// erases nothing and lets NODE strip has to be right about the imported file
// as well as the importing one.
export type Pair = { a: number; b: number };

export function total(p: Pair): number {
  return p.a + p.b;
}
