export function both(): Promise<string> {
  return risky().then(
    (value) => String(value),
    (err) => String(err),
  );
}

export function onlyFulfilled(): Promise<string> {
  return risky().then((value) => String(value));
}
