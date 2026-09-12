// Seeded bug: a cell the parser could not read binds `null`, and the test
// below it is `(parsed ?? 0) > 0`, which is false for an unreadable cell and
// for a real zero alike -- so the row that could not be read is silently
// counted as an empty one. Every step of that chain is a value this recorder
// can be asked to follow, and the JS spellings are the ones it answers in:
// `null` is a value, `undefined` is a value, and a long string is not.
export function reading(row: string): number {
  const label = row.slice(0, 2);
  const digits = Number(row.slice(2));
  const parsed = Number.isNaN(digits) ? null : digits;
  let missing;                  // declared, never assigned
  const rate = 5;
  const trail = label.padEnd(150, '.');
  const counted = (parsed ?? 0) > 0 ? rate : 0;   // BUG: null read as zero
  return counted + trail.length - 150;
}
