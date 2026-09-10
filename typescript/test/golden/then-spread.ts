export function forwarded(rest: [(e: unknown) => void]): Promise<string> {
  return risky().then((value) => String(value), ...rest);
}

export function leading(rest: [(v: string) => string]): Promise<string> {
  return risky().then(...rest, (err) => String(err));
}
