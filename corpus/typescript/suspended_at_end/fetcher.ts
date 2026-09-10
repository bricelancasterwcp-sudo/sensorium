// Seeded bug: `awaitToken` waits on a promise nothing ever settles -- the
// resolver is dropped on the floor -- so the caller parks forever. The test
// carries its own timeout so the run ends; what the recording has to show is
// WHERE the program was parked when it ended.
export function awaitToken(): Promise<string> {
  return new Promise(() => {
    // BUG: the resolver is never called and never stored, so this promise
    // can never settle.
  });
}

export function tokenAge(): number {
  return 0;
}
