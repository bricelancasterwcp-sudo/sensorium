// Seeded bug: the sweep is SCHEDULED rather than awaited, so it runs after
// the code that scheduled it has already returned. It empties the queue
// under the test's feet, and nothing of the program's is on the call stack
// at that moment -- Node's timer machinery is what called it.
const queue: number[] = [];

export function enqueue(n: number): number {
  queue.push(n);
  return queue.length;
}

export function sweep(): number {
  const swept = queue.length;
  queue.length = 0;             // BUG: nobody is waiting for this to happen
  return swept;
}

export function pending(): number {
  return queue.length;
}

export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
