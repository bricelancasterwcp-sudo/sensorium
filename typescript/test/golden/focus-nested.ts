// focus: outer
export function outer(): number {
  const f = (n: number): number => {
    const m = n * 2;
    return m;
  };
  return f(1);
}
