import { expect, test } from 'vitest';

import { describeAmount } from './amount';

test('an amount is described for the receipt', () => {
  expect(describeAmount('twelve')).toContain('not an amount');
});
