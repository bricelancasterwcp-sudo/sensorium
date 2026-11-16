// Seeded bug: the write lands on the object's field and the local the caller
// is handed back is never touched, so `bump` returns 0. The write is a
// statement this recorder records, and the delta is the member spelling
// `state.x`. The argument capture is still the object as it was on the way
// in, which is a different fact from the field write.
export function bump(state: { x: number }): number {
  let seen = 0;
  state.x = 5;                  // BUG: `seen` is what the caller reads
  return seen;
}
