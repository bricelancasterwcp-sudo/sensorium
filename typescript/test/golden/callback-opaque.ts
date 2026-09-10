export function delegated(handler: (e: unknown) => void): Promise<void> {
  return risky().catch(handler);
}
