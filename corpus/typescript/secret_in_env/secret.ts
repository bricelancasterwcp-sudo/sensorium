// Not a seeded bug: this case demonstrates rule v1's NAME rule, not a
// defect. `token`, `apiKey`, `authHeaders` (via its `authorization` member)
// and `secret` are all names the rule fires on; `handle` fires on nothing
// itself, and holds no plaintext once redaction runs.
export function secret(): string {
  return process.env.SENSORIUM_CORPUS_TOKEN ?? '';
}

export function handle(token: string): number {
  const apiKey = token;
  const authHeaders = { authorization: apiKey };
  return authHeaders.authorization.length;
}
