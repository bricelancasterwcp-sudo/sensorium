// Seeded bug: `itemWeight` returns GRAMS and `shippingCost` expects
// KILOGRAMS, so shipping comes out about a thousand times too large. Only
// the order total is ever looked at, and it is a plausible-looking number.
export type Item = { name: string; price: number; grams: number };

export function shippingCost(weightKg: number): number {
  return 4 + 2.5 * weightKg;
}

export function itemWeight(item: Item): number {
  return item.grams;            // BUG: grams, not kilograms
}

export function orderTotal(items: Item[]): number {
  let goods = 0;
  let ship = 0;
  for (const item of items) {
    goods += item.price;
    ship += shippingCost(itemWeight(item));
  }
  return Math.round((goods + ship) * 100) / 100;
}
