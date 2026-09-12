// Seeded bug: this order was billed no handling fee, and the two candidate
// explanations -- a call site that asked for the member price, or a `total`
// that ignored what it was asked -- are told apart only by the ARGUMENTS.
// `total` is focused and records its own; `helper`, the fee table, is not,
// and which tier it was asked about is not in this recording at all.
export type Opts = { member?: boolean };

export function helper(tier: string): number {
  return tier === 'gold' ? 0 : 1;
}

export function total(items: number[], { member = false }: Opts = {}): number {
  let sum = 0;
  for (const price of items) {
    sum += price;
  }
  const fee = helper('bronze');
  if (!member) {
    sum += fee;                 // the fee this order never paid
  }
  return sum;
}
