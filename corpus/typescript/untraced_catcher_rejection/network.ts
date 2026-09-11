// NOT A BUG: the same shape as `untraced_catcher`, on a rejection instead
// of a synchronous throw. `await expect(fetchThing()).rejects.toThrow(…)`
// awaits the rejection and hands it to vitest's own matcher, which is not
// traced code -- the rejection unwinds `fetchThing`, unwinds the `await`,
// and the frame that decides whether the assertion passed is the same
// untraced machinery `untraced_catcher` names, this time reached across a
// suspension instead of a synchronous call.
export async function fetchThing(): Promise<never> {
  throw new Error('offline');
}
