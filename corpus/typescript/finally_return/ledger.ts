// Seeded bug: the `finally` block RETURNS, and a `return` in a `finally`
// discards whatever was travelling through the frame -- here, the write
// failure. There is no `catch` clause anywhere: the sink is the `finally`
// itself, which is why this shape is the one a reader scanning for `catch`
// never finds. The caller gets a row count and believes the write landed.
export function commit(rows: number): number {
  try {
    throw new Error('the write failed');
  } finally {
    return rows;                // BUG: the failure is discarded here
  }
}
