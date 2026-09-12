// focus: shapes
export function shapes(n: number): number {
  interface Point { x: number }
  type Pair = [number, number];
  enum Colour { Red = 1 }
  declare const later: number;
  const p: Point = { x: n };
  const q: Pair = [n, later];
  return p.x + q[0] + Colour.Red;
}
