export function fields(): void {
  try {
    risky();
  } catch ({ message }) {
    report(message);
  }
}
