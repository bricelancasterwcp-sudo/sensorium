export function reason(): string {
  try {
    risky();
  } catch (err) {
    return String(err);
  }
  return "";
}
