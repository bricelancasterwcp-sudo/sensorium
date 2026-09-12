// Seeded bug: the discounted price is computed one link up the chain and the
// tail hands back the link before it, so the discount never leaves the
// function. Each `const` is its own statement and mints its own row; the
// `return` is the tail and mints none -- what it carried is the RETURN.
export function fill(price: number, qty: number): number {
  const gross = price * qty;
  const discount = gross > 100 ? 20 : 0;
  const net = gross - discount;
  return gross;                 // BUG: `net` is computed and then dropped
}
