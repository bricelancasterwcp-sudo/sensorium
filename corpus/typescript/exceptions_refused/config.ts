// Seeded bug: `loadConfig` swallows the parse failure and returns a
// healthy-looking default, so every caller downstream believes the file was
// read. The `throw` and the `catch` ARE recorded -- one RAISE row and one
// HANDLED row -- and this recorder still declines to judge what happened to
// the error, because no TypeScript disposition rules exist yet.
export type Config = { retries: number };

export function parse(text: string): Config {
  const n = Number(text);
  if (Number.isNaN(n)) {
    throw new Error(`not a number: ${text}`);
  }
  return { retries: n };
}

export function loadConfig(text: string): Config {
  try {
    return parse(text);
  } catch (e) {
    return { retries: 3 };      // BUG: the failure reaches nobody
  }
}
