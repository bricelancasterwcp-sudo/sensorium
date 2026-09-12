// Seeded bug: the payload spells the field `sizes` and the destructure reads
// `size`, so the DEFAULT binds and nothing says a default was taken. One
// statement binds three names here -- `id`, `first` and `rest` -- and the row
// for it carries all three, which is how the default is caught: `first=0`
// where the payload plainly says 2.
export type Payload = Record<string, unknown>;

export function unpack(obj: Payload): number {
  const { id, size: [first] = [0], ...rest } = obj as {
    id: string; size?: number[];
  } & Payload;
  let note;                     // declared and never assigned
  const kept = Object.keys(rest).length;
  return first + kept;          // BUG: `first` is the default, not the payload
}
