// focus: settle
export function settle(flag: boolean): number {
  let cleanup = 0;
  try {
    if (flag) return 1;
    return 2;
  } finally {
    cleanup = 1;
    note(cleanup);
  }
}

export function note(n: number): number {
  return n;
}
