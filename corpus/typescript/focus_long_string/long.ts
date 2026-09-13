// Not a seeded bug but a MEASUREMENT of the 100/101 boundary. `util.inspect`
// is given `maxStringLength: 100` (`typescript/src/dbg.mjs`), so the
// 100-character string is spelled WHOLE and the 101-character one is spelled
// as a 100-character PREFIX with `... 1 more character` after the closing
// quote. That tail is the only evidence of the cut: the wire's own `trunc`
// flag is false, because inspect cut the string long before the 200-byte cap
// looked at the rendering -- which is why `info`'s `truncated values:`
// counter could not see it (blind spot 36). And `flow --value` of the whole
// 101-character literal sights NOTHING: a prefix is read as TRUNCATED and is
// never compared as a value.
export function pad(n: number): string {
  const s100 = 'a'.repeat(100);
  const s101 = 'b'.repeat(101);
  return s100.length + s101.length === n ? s100 : s101;
}
