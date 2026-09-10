// Not a bug at all: this is the shape a test suite writes on purpose, and on
// the lens it is the commonest `catch` there is. The clause reads the binding
// to assert on it, so the escape rule writes `catch_escaped` and the verdict
// is AMBIGUOUS -- the recorder cannot tell a deliberate assertion from a
// swallow that happens to touch the value, and says so rather than accusing
// every test in the suite of hiding a failure.
export function validate(amount: number): number {
  if (amount <= 0) {
    throw new Error('amount must be positive');
  }
  return amount;
}
