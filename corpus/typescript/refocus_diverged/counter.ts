// Seeded property, not a bug: this program's branch depends on state OUTSIDE
// the process -- a counter file it reads and increments in the working
// directory -- so no re-run ever reproduces the previous execution.
//
// Ground truth: `diff` between the two recordings must report DIVERGED,
// never MATCH. That is the CORRECT answer: sensorium does not replay state
// outside the process, so the second invocation genuinely was a different
// execution.
//
// Do NOT "fix" this into a `Math.random()` coin flip. A coin flip is the
// honest illustration and a flaky corpus case: the diff would land on MATCH
// roughly half the time, and a suite that fails half the time teaches nobody
// anything. Here the verdict is guaranteed while the REASON stays the real
// one. The harness copies the whole project into a fresh temp dir per case,
// so the counter starts clean every time the suite runs.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';

const COUNTER = 'run_count.txt';

export function pick(): boolean {
  const n = existsSync(COUNTER) ? Number(readFileSync(COUNTER, 'utf8')) : 0;
  writeFileSync(COUNTER, String(n + 1));
  return n % 2 === 0;
}

export function left(): string {
  return 'L';
}

export function right(): string {
  return 'R';
}

export function choose(): string {
  return pick() ? left() : right();
}
