// Seeded bug: `startRefresh` kicks off an async refresh and returns without
// awaiting it, so when the refresh rejects there is no `await` and no
// `.catch` anywhere to receive it. The test asserts on the cache and PASSES;
// the harness reports a green run. The only record that anything went wrong
// is the one the container's own `unhandledRejection` listener kept.
const age = 0;

export async function refresh(): Promise<number> {
  throw new Error('stale token');
}

export function startRefresh(): void {
  void refresh();               // BUG: nothing ever receives this rejection
}

export function cacheAge(): number {
  return age;
}

export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
