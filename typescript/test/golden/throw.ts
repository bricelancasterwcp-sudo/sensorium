export function guard(n: number): number {
  if (n < 0) throw new RangeError("neg");
  return n;
}

if (typeof globalThis === "undefined") throw new Error("no global");
