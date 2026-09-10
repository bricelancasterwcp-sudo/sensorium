// Seeded bug: the caller hands the rejection to an EMPTY rejection callback,
// so the request that failed leaves no mark of any kind. There is no `throw`
// statement anywhere in this program: the failure is born as a rejection, and
// the only row about it is the handler that took it -- which is why the
// verdict says where it came from as well as where it went.
export function fetchQuote(): Promise<number> {
  return Promise.reject(new Error('upstream is down'));
}

export function lastQuote(): number {
  return 0;
}
