// focus: take
export function take(o: any, ...rest: number[]): number {
  const { a, b: [c] = [0], ...r } = o;
  let x;
  x = a + c + rest.length;
  return x + Object.keys(r).length;
}
