// Seeded bug: the loyalty spec says a 1000-point order earns the gold
// discount, but the boundary test is `points > 1000`, so an order sitting
// exactly on the boundary silently takes the silver path. Nothing is logged
// about which tier was applied, and both paths return a plausible number.
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
