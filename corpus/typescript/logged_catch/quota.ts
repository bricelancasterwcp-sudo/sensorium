// Seeded bug: `quotaOrDefault` writes the parse failure to `console.error`
// and returns a plausible number, so every caller downstream is working from
// a default it never asked for. The log is the ONLY trace of the failure the
// program leaves, and a log is not a return value: nothing above this frame
// can branch on it. The binding `e` is read only as an argument of a logging
// call, which is the one mention the escape rule still calls a swallow.
export function readQuota(text: string): number {
  const n = Number(text);
  if (Number.isNaN(n)) {
    throw new Error(`not a quota: ${text}`);
  }
  return n;
}

export function quotaOrDefault(text: string): number {
  try {
    return readQuota(text);
  } catch (e) {
    console.error(e);           // BUG: logged, and the caller learns nothing
    return 10;
  }
}
