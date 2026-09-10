export function collect(seen: unknown[]): Promise<void> {
  return risky().catch((err) => {
    seen.push(err);
  });
}
