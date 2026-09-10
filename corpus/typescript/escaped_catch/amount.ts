// Seeded bug: `describeAmount` turns the failure into a STRING and returns
// it, so a caller that renders the result shows an error message where it
// meant to show money. This is the line the rules refuse to cross: the same
// two rows -- one RAISE, one HANDLED -- as a swallow, and a `how` word that
// says the value left the clause. Where it went afterwards is not followed,
// so the verdict is AMBIGUOUS and never SWALLOWED.
export function parseAmount(text: string): number {
  const n = Number(text);
  if (Number.isNaN(n)) {
    throw new Error(`not an amount: ${text}`);
  }
  return n;
}

export function describeAmount(text: string): string {
  try {
    return `amount: ${parseAmount(text)}`;
  } catch (e) {
    return String(e);           // the error leaves, as a rendering of itself
  }
}
