// Seeded bug: the `catch` clause absorbs the failure and the frame holding it
// then PARKS on a promise nothing settles, so the recording ends with that
// handler's frame still open. An absorbing clause is only half of a swallow;
// the other half is the frame afterwards returning, and this recording never
// got to see whether it would. The test carries its own timeout so the run
// ends -- and the verdict says the frame is still suspended, not that it
// swallowed anything.
export async function drain(): Promise<number> {
  try {
    throw new Error('the queue is gone');
  } catch {
  }
  await new Promise(() => {});  // BUG: nothing ever settles this
  return 0;
}
