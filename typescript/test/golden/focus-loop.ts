// focus: sum
export function sum(xs: number[]): number {
  let total = 0;
  for (const v of xs) {
    total += v;
  }
  return total;
}
