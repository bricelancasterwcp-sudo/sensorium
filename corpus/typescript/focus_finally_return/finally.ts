// Seeded bug: the `finally` is the last thing that runs, and it is the part a
// reader of the returned 1 never sees -- `cleanup` was set and `note` was
// called on the way out. Under sensorium-ts 0.3.0 the `return` closes the
// frame BEFORE the finally runs, so those two rows are dropped and `note`
// opens under whatever frame is on top: attributed outside its own caller
// (blind spot 38). The seal (design §4.2) is what makes this case green.
export function settle(flag: boolean): number {
  let cleanup = 0;
  try {
    if (flag) return 1;
    return 2;
  } finally {
    cleanup = 1;
    note(cleanup);
  }
}

export function note(n: number): number {
  return n;
}
