// The same boundary bug as `wrong_branch`, reached from two test FILES so
// the passing input and the failing input are two containers of one
// invocation. 1001 points behaves; 1000 points, which the spec says must
// earn gold, silently takes silver -- and the test that asserts gold fails.
export function gold(total: number): number {
  return total * 0.8;
}

export function silver(total: number): number {
  return total * 0.95;
}

export function price(points: number, total: number): number {
  if (points > 1000) {          // BUG: the spec says >= 1000
    return gold(total);
  }
  return silver(total);
}
