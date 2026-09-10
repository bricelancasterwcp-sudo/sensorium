export function forwarded(args: [(e: unknown) => void]): Promise<void> {
  return risky().catch(...args);
}

export function named(): Promise<void> {
  return risky().catch((err) => {
    console.error(err);
  });
}
