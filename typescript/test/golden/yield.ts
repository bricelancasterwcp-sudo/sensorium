export function* counter(): Generator<number> {
  yield 1;
  yield;
  yield* inner();
}

export async function* stream(): AsyncGenerator<number> {
  yield await next();
}
