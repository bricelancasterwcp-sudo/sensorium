// H1 under `node --test`: an `.mts` is instrumented by this recorder and
// stripped BY NODE. Before the hook returned Node's own reported format its
// `STRIP` set held `.ts` and `.tsx` only, so this file came back with its
// types still in it and Node threw a SyntaxError on the first annotation --
// the R46 residual this closes. There is no provider under `node --test`, so
// the task below is named by its lexical title (`basis: "title"`).
//
// Run by `npm run probe:nodetest` as one of an explicit list of files; see
// `README.md` for the recipe.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { type Pair, total } from './ext.lib.mts';

function pair(a: number, b: number): Pair {
  return { a, b };
}

test('M1 an .mts is stripped by Node and recorded', () => {
  assert.equal(total(pair(1, 2)), 3);
});
