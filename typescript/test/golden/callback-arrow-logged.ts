export function warned(): Promise<void> {
  return risky().catch((err) => {
    console.warn(err);
  });
}
