import { expect, test } from 'vitest';

import { Fog } from './fog';

test('a dense fog is computed and drawn', () => {
  const fog = new Fog();
  expect(fog.compute(25)).toBe(10);
  expect(fog.render(25)).toBe('fog(25)');
});
