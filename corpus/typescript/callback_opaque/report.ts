// Seeded bug, and one the recorder REFUSES to name: the rejection is handed
// to a handler defined elsewhere. The splice sees an identifier, not a body,
// so it cannot say what that function does with its parameter -- and
// `noteFailure` really does drop it. The recorder reports what it can see
// (a handler took the rejection, shape unknown) rather than what it guesses.
export function syncNow(): Promise<number> {
  return Promise.reject(new Error('sync conflict'));
}

export function noteFailure(e: unknown): void {
  console.warn(e);              // BUG: the failure reaches no caller
}

export function conflictCount(): number {
  return 0;
}
