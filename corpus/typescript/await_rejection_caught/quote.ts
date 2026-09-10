// Seeded bug: the quote service throws, the caller AWAITS it inside a `try`
// and its `catch` quietly substitutes a fallback. The throw and the catch are
// in two different frames with an `await` between them -- the failure crossed
// a suspension -- and the recorder carries one identity across that gap, so
// the verdict names the `catch` in the awaiter and the `throw` inside the
// service as one story rather than two unrelated rows.
export async function fetchQuote(): Promise<number> {
  throw new Error('quote service down');
}

export function fallbackQuote(): number {
  return 0;
}
