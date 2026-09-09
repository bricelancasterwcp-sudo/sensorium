// No bug here: this case is about the NAMES the recorder gives its tasks,
// and about which frames are not in a task at all. `reset` is called from a
// `beforeEach` hook, which is not a test and therefore not a task.
let calls = 0;

export function reset(): number {
  calls = 0;
  return calls;
}

export function square(n: number): number {
  calls += 1;
  return n * n;
}
