// NOT A BUG: `parse` intentionally rejects `sqrt`, and the test proves it by
// TYPE. `expect(() => parse('sqrt(4)')).toThrow(FormulaError)` wraps the call
// in an arrow that vitest calls and catches inside its own matcher, and that
// matcher is not traced code: the throw unwinds `parse`, unwinds the arrow,
// and the frame that decides whether the test passed is one this recorder
// never sees. Rung 2 folded this into the catch-all with every other shape
// nobody could name; rung 3 names it -- AMBIGUOUS, untraced catcher, `its
// caller returned` -- because the caller (the arrow) DID return, and what
// the untraced matcher did with the error in between is exactly the part
// this recorder still cannot follow.
export class FormulaError extends Error {}

export function parse(src: string): number {
  if (src.startsWith('sqrt')) {
    throw new FormulaError("Unknown function 'sqrt'");
  }
  return Number(src);
}
