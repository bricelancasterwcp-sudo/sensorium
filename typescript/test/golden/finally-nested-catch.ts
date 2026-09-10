export function nested(): number {
  try {
    try {
      throw new Error("a");
    } catch {}
    work();
  } finally {
    return 1;
  }
}
