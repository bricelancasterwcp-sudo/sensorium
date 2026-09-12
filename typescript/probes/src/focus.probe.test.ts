// @vitest-environment node
// The focus tier, recorded rather than argued about: eleven shapes out of spec
// §3.2's table, each called exactly once, and every row each one mints written
// down beside the statement that mints it.
//
//     // LINE <fn> <name>=<text> [<name>=<text> …] [unbound:<a,b>]
//     // LINE <fn> -                                 (the row wrote nothing)
//
// The markers above a line describe, IN ORDER, every LINE record recorded at
// that line for that function — so a `for` head that binds once per iteration
// is three markers and not one, and a shape that mints a row nobody wrote down
// fails the count. Values are compared with whitespace squashed, as a RETURN's
// are, so `{ z: 9 }` is written `{z:9}`. `// ARGS <fn> <name>=<text>` is the
// focused CALL's own argument map, which is not a LINE at all (spec §3.3).
//
// `probes/vitest.config.ts` names these eleven functions in `SENSORIUM_FOCUS`
// under `SENSORIUM_PROBE_DIRECT=1`; driven with no focus, this file records no
// such row at all, and `check.mjs` asserts THAT instead. Both readings are the
// contract, and a checker that skipped one would be a hole. (No comment here
// may begin with the marker word itself: the reader would take it for one.)
import { expect, test } from 'vitest';

// ARGS letChain n=2
export function letChain(n: number): number {
  // LINE letChain base=4
  const base = n * 2;
  // LINE letChain label='x'
  let label = 'x';
  // LINE letChain label='x2'
  label = label + n;
  return base + label.length;
}

export function loopCounter(xs: number[]): number {
  // LINE loopCounter total=0
  let total = 0;
  // LINE loopCounter v=1
  // LINE loopCounter v=2
  // LINE loopCounter - unbound:v
  for (const v of xs) {
    // LINE loopCounter total=1
    // LINE loopCounter total=3
    total += v;
  }
  return total;
}

export function blockScope(c: boolean): number {
  // LINE blockScope out=0
  let out = 0;
  // LINE blockScope - unbound:y
  if (c) {
    // LINE blockScope y=3
    const y = 3;
    // LINE blockScope out=3
    out = y;
  }
  return out;
}

export function bareGuard(n: number): number {
  // LINE bareGuard x=0
  let x = 0;
  // LINE bareGuard count=0
  let count = 0;
  // LINE bareGuard m=3
  let m = 3;
  // LINE bareGuard x=1
  // LINE bareGuard x=2
  if ((x = n))
    // LINE bareGuard x=2
    x = 2;
  // LINE bareGuard m=2
  // LINE bareGuard m=1
  // LINE bareGuard m=0
  while ((m = m - 1) > 0)
    // LINE bareGuard count=1
    // LINE bareGuard count=2
    count += 1;
  return x + count + m;
}

export function doWhile(n: number): number {
  // LINE doWhile count=0
  let count = 0;
  // LINE doWhile m=2
  let m = n;
  // LINE doWhile m=0
  do {
    // LINE doWhile count=1
    // LINE doWhile count=2
    count += 1;
  } while ((m = m - 1) > 0);
  return count;
}

export function forIn(o: Record<string, number>): number {
  // LINE forIn n=0
  let n = 0;
  // LINE forIn k='a'
  // LINE forIn k='b'
  // LINE forIn - unbound:k
  for (const k in o) {
    // LINE forIn n=1
    // LINE forIn n=3
    n += o[k];
  }
  return n;
}

export async function asyncRows(p: Promise<number>): Promise<number> {
  // LINE asyncRows a=7
  const a = await p;
  // LINE asyncRows -
  await Promise.resolve();
  // LINE asyncRows b=8
  const b = a + 1;
  return b;
}

export function catchBinding(): number {
  // LINE catchBinding count=0
  let count = 0;
  // LINE catchBinding - unbound:e
  try {
    throw 'boom';
  }
  // LINE catchBinding e='boom'
  catch (e) {
    // LINE catchBinding count=1
    count += 1;
  }
  return count;
}

export function destructure(o: { a: number; b: number[]; z: number }): number {
  // LINE destructure a=1 c=2 r={z:9}
  const { a, b: [c] = [0], ...r } = o;
  // LINE destructure x=undefined
  let x;
  // LINE destructure x=12
  x = a + c + r.z;
  return x;
}

export function placeWrite(o: { n: number }): number {
  // LINE placeWrite -
  o.n = 5;
  // LINE placeWrite total=5
  const total = o.n;
  return total;
}

export function nestedArrow(n: number): number {
  // LINE nestedArrow double=[Function:double]
  const double = (v: number): number => {
    // LINE double m=4
    const m = v * 2;
    return m;
  };
  // LINE nestedArrow out=4
  const out = double(n);
  return out;
}

test('letChain: three statements, three rows', () => {
  expect(letChain(2)).toBe(6);
});

test('loopCounter: a head row per iteration, then the loop own row', () => {
  expect(loopCounter([1, 2])).toBe(3);
});

test('blockScope: the block dies on the `if`s row', () => {
  expect(blockScope(true)).toBe(3);
});

test('bareGuard: a body written without braces still reports inside the guard', () => {
  expect(bareGuard(1)).toBe(4);
});

test('doWhile: the test runs after the body, so the body opens with no row', () => {
  expect(doWhile(2)).toBe(2);
});

test('forIn: a key bound per iteration, and dead when the loop ends', () => {
  expect(forIn({ a: 1, b: 2 })).toBe(3);
});

test('asyncRows: a statement holding an await completes after the resume', async () => {
  await expect(asyncRows(Promise.resolve(7))).resolves.toBe(8);
});

test('catchBinding: the binding is the clauses first row', () => {
  expect(catchBinding()).toBe(1);
});

test('destructure: every name the pattern binds', () => {
  expect(destructure({ a: 1, b: [2], z: 9 })).toBe(12);
});

test('placeWrite: a property write is nobodys delta', () => {
  expect(placeWrite({ n: 1 })).toBe(5);
});

test('nestedArrow: the container selects the callback it defines', () => {
  expect(nestedArrow(2)).toBe(4);
});
