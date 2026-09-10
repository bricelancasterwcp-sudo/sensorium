// Seeded bug: `boot` falls back to defaults when the disk is offline, and the
// failure passes through TWO clauses on its way there -- `reload` catches it
// and throws the very same object on, `boot` catches that and returns. One
// thrown object, two RAISE rows, and the verdict on the second is what
// happened to the failure; the first row's line is the journey.
export function load(): number {
  throw new Error('disk offline');
}

export function reload(): number {
  try {
    return load();
  } catch (e) {
    throw e;                    // the hop: the same object, raised again
  }
}

export function boot(): string {
  try {
    return String(reload());
  } catch {
    return 'defaults';          // BUG: the outage reaches nobody
  }
}
