import { expect, test } from 'vitest';

import { FormulaError, parse } from './formula';

test('an unknown function is reported by type', () => {
  expect(() => parse('sqrt(4)')).toThrow(FormulaError);
});
