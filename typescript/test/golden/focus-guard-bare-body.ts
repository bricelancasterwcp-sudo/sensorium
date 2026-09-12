// focus: probe
export function probe(n: number): number {
  let x = 0;
  let count = 0;
  let m = n;
  if ((x = n)) x = 2;
  while ((m = m - 1) > 0) count += 1;
  return x + count;
}
