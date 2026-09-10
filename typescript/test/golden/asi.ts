export function* gen(): Generator<void> {
  yield
  (g)()
}

export function early(flag: boolean): void {
  if (flag) return
  (g)()
}
