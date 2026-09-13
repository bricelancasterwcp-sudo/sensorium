// A deterministic program: no clock, no randomness, no file outside the process.
export function fill(): number {
  const a = 1;
  const b = a + 1;
  return b;
}
