// Seeded bug: the discount is computed inside the `if` and the code after it
// reads a stale total. The question a fold without `unbound` gets WRONG is
// whether `discount` was still bound at the statement after the block.
export function total(items: number[], member: boolean): number {
  let sum = 0;
  for (const price of items) {
    sum += price;
  }
  if (member) {
    const discount = Math.round(sum * 0.1);
    sum -= discount;
  }
  const rounded = Math.round(sum);
  return rounded;
}
