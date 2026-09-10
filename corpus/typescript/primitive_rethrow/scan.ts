// Seeded bug, and one the recorder cannot follow: the thrown value is a
// STRING. A thrown object gets an identity the recorder can carry between
// rows; a primitive gets nothing to hang one on, so every row of it carries a
// fresh number and two records of `'boom'` may be one throw rethrown or two
// unrelated throws. `safeScan` really does drop it -- and the recorder says
// the record cannot tell, which is the honest answer and not the useful one.
export function scan(text: string): number {
  if (!text) {
    throw 'boom';               // a primitive: no identity to carry
  }
  return text.length;
}

export function rescan(text: string): number {
  try {
    return scan(text);
  } catch (e) {
    throw e;                    // the same value, and an unprovable claim
  }
}

export function safeScan(text: string): number {
  try {
    return rescan(text);
  } catch {
    return 0;                   // BUG: the failure reaches nobody
  }
}
