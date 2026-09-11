// Seeded bug: same `parse`/`FormulaError` as `untraced_catcher`, but the
// test writes a SECOND assertion after the `toThrow` line, and that second
// assertion is wrong. The first throw is caught the same untraced way --
// its caller (the arrow inside `expect`) returns -- but its GRANDcaller (the
// test callback itself) does not return: it goes on to throw a second,
// unrelated error. The untraced catcher's block reads the `later unwound`
// variant for exactly that reason, and the second throw is a plain
// PROPAGATED case like any other -- the two verdicts are the demonstration
// that a reader watching only the first raise cannot tell "the untraced
// catcher translated this" from "the caller went on to fail on its own".
export class FormulaError extends Error {}

export function parse(src: string): number {
  if (src.startsWith('sqrt')) {
    throw new FormulaError("Unknown function 'sqrt'");
  }
  return Number(src);
}
