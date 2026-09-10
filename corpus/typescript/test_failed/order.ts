// Seeded bug: `total` refuses an empty order instead of reporting 0, and
// nothing in the test catches it. This is the one direction a failure can go
// that IS reported today -- out of the test's own frame and into the harness,
// which prints it and fails the file. The case is here so the corpus holds a
// recording of that direction too: a red suite by design, and the verdict is
// the one disposition a reader never needed a tool to learn.
export function total(items: number[]): number {
  if (items.length === 0) {
    throw new Error('an empty order has no total');
  }
  return items.reduce((a, b) => a + b, 0);
}
