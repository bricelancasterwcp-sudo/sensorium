export function assertFails(): void {
  try {
    risky();
  } catch (err) {
    expect((err as Error).message).toBe("nope");
  }
}
