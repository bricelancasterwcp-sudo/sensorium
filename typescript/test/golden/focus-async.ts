// focus: load
export async function load(p: Promise<number>, q: Promise<void>): Promise<number> {
  const a = await p;
  await q
  const b = a + 1;
  return b;
}
