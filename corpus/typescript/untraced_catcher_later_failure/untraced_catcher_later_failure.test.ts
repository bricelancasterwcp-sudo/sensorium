import { expect, test } from 'vitest';

import { FormulaError, parse } from './formula';

test('an unknown function is reported by type, then the test itself fails', () => {
  expect(() => parse('sqrt(4)')).toThrow(FormulaError);
  throw new Error('the assertion after was wrong');
});
