// Seeded bug: the write lands on the object's field and the local the caller
// is handed back is never touched, so `bump` reports nothing happened. The
// write IS a statement this recorder records -- there is a row at its line --
// and what it wrote is a name this recorder cannot see: the row carries no
// delta at all, and the 5 is followable nowhere. That is the blind spot said
// out loud, rather than left as a gap between two line numbers.
export function bump(state: { x: number }): number {
  let seen = 0;
  state.x = 5;                  // BUG: `seen` is what the caller reads
  return seen;
}
