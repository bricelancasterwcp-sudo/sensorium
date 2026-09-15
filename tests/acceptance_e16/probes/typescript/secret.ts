// E16 part B's TypeScript probe -- not a seeded bug and not a corpus case:
// the four places §1's amendment counts, and nothing else.
//
// `handle` is the focused function (`--focus handle`). `token` fires rule
// v1's NAME rule on the CALL argument and `secret` on its own RETURN;
// `copy` and `headers` fire no name at all, so the only thing that can
// reach those two deltas is the CONTENT rule -- which is why the token is
// minted as `sk-e16-` plus 33 characters, inside the `sk-` pattern.
export function secret(): string {
  return process.env.SENSORIUM_E16_TOKEN ?? '';
}

export function handle(token: string): number {
  const copy = token;
  const headers = { authorization: copy };
  return headers.authorization.length;
}
