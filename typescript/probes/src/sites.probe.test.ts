// E4, the site probe: twenty syntactic shapes, nineteen here and the TSX
// component in the sibling. The line AFTER each `// SITE <name>` marker is the
// expected `firstlineno` of the function whose qualname ends in `<name>`.
// `check.mjs` reads the markers out of this file, so nothing here is a number
// written down twice — move a function and the expectation moves with it.
import { expect, test } from 'vitest';

import { S19Component } from './sites.component';

// SITE s01_decl
export function s01_decl(x: number): number {
  return x + 1;
}

// SITE s02_expr
export const s02_expr = function (x: number): number {
  return x + 2;
};

// SITE s03_arrow_one_line
export const s03_arrow_one_line = (x: number): number => x + 3;

// SITE s04_arrow_multiline
export const s04_arrow_multiline = (
  x: number,
  y: number,
): number => {
  return x + y;
};

export class Klass {
  value = 0;

  // SITE constructor
  constructor(v: number) {
    this.value = v;
  }

  // SITE s05_method
  s05_method(): number {
    return this.value + 5;
  }

  // SITE s06_static
  static s06_static(): number {
    return 6;
  }

  // SITE s07_getter
  get s07_getter(): number {
    return this.value + 7;
  }

  // SITE s08_setter
  set s08_setter(v: number) {
    this.value = v;
  }

  // SITE s15_field_arrow
  s15_field_arrow = (): number => this.value + 15;
}

// SITE s09_async_decl
export async function s09_async_decl(): Promise<number> {
  return 9;
}

// SITE s10_async_arrow
export const s10_async_arrow = async (): Promise<number> => 10;

// SITE s11_generator
export function* s11_generator(): Generator<number> {
  yield 11;
}

// SITE s12_async_generator
export async function* s12_async_generator(): AsyncGenerator<number> {
  yield 12;
}

// SITE s16_iife
export const s16_iife = (function s16_iife(): number {
  return 16;
})();

export function s17_outer(): number {
  // SITE s17_inner
  function s17_inner(): number {
    return 17;
  }
  return s17_inner();
}

export function s18_map(): number[] {
  // SITE s18_callback
  return [1, 2].map(function s18_callback(v: number): number {
    return v * 18;
  });
}

export namespace NS20 {
  // SITE s20_in_namespace
  export function s20_in_namespace(): number {
    return 20;
  }
}

// SITE s14_default
export default function s14_default(): number {
  return 14;
}

test('sites: every synchronous shape runs once', () => {
  const k = new Klass(1);
  k.s08_setter = 2;
  expect(s01_decl(1)).toBe(2);
  expect(s02_expr(1)).toBe(3);
  expect(s03_arrow_one_line(1)).toBe(4);
  expect(s04_arrow_multiline(1, 2)).toBe(3);
  expect(k.s05_method()).toBe(7);
  expect(Klass.s06_static()).toBe(6);
  expect(k.s07_getter).toBe(9);
  expect(k.s15_field_arrow()).toBe(17);
  expect(s16_iife).toBe(16);
  expect(s17_outer()).toBe(17);
  expect(s18_map()).toEqual([18, 36]);
  expect(NS20.s20_in_namespace()).toBe(20);
  expect(s14_default()).toBe(14);
  expect(S19Component({ n: 19 }).tag).toBe('div');
});

test('sites: the async and generator shapes run once', async () => {
  expect(await s09_async_decl()).toBe(9);
  expect(await s10_async_arrow()).toBe(10);
  expect([...s11_generator()]).toEqual([11]);
  const out: number[] = [];
  for await (const v of s12_async_generator()) out.push(v);
  expect(out).toEqual([12]);
});
