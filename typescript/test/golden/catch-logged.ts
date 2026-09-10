export function load(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch (err) {
    console.error("load failed", err);
  }
  return null;
}

export function rendered(): void {
  try {
    risky();
  } catch (err) {
    console.warn(`risky failed: ${String(err)}`);
  }
}
