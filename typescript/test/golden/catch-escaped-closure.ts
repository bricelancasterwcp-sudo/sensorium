export function later(): void {
  try {
    risky();
  } catch (err) {
    queueMicrotask(() => console.error(err));
  }
}
