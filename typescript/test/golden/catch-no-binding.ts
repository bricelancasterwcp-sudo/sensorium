export function quiet(): void {
  try {
    risky();
  } catch {
    report("failed");
  }
}
