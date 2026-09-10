// Seeded bug: the rejection is handed to a callback that logs it and returns,
// so the refresh failure goes to the console and nowhere else. It is the
// `logged_catch` shape written as a promise: the same swallow, reached
// through `.catch(fn)` instead of through a `catch` clause, and the `how`
// word on the row is what says which of the two the program wrote.
export function refreshToken(): Promise<string> {
  return Promise.reject(new Error('token expired'));
}

export function tokenAge(): number {
  return 0;
}
