export function parse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch (err) {
    return null;
  }
}

export function ignore(): void {
  try {
    risky();
  } catch {
  }
}

export function destructured(): void {
  try {
    risky();
  } catch ({ message }) {
    report(message);
  }
}

export function sink(): Promise<void> {
  return risky().catch(() => {});
}

try {
  risky();
} catch (err) {
  report(err);
}
