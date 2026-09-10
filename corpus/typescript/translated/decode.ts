// Seeded bug: `decodeOrWrap` catches the decode failure and throws a WRAPPER
// carrying a rendering of it, so the original object stops here and a new one
// continues. Two thrown objects, two serials, two verdicts: the original's
// clause read the binding, so what became of the original is AMBIGUOUS, and
// the wrapper's own raise is judged on its own evidence rather than being
// folded into the story of the error it replaced.
export class Wrapped extends Error {}

export function decode(raw: string): number {
  throw new Error(`bad payload: ${raw}`);
}

export function decodeOrWrap(raw: string): number {
  try {
    return decode(raw);
  } catch (e) {
    throw new Wrapped(String(e));   // the original stops being the failure
  }
}
