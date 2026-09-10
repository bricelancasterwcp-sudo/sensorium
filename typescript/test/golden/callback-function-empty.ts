export function dropped(): Promise<void> {
  return risky().catch(function () {});
}
