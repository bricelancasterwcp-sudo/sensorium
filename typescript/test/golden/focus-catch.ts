// focus: guarded
export function guarded(): number {
  let count = 0;
  try {
    throw new Error('x');
  } catch (e) {
    count += 1;
  }
  return count;
}
