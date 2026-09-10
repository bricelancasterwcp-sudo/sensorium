// R2: the setup file exists twice and the two copies must stay one text.
// `src/setup.mjs` is the template the driver writes out with `__PKG__` replaced
// by the installed package; `probes/setup.mjs` is the same text with the in-tree
// relative path, which is what lets the probes run with no driver. If the two
// drift, the probes stop proving anything about what the driver ships — so the
// only difference either is allowed is the runtime's import specifier.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const TEMPLATE = fileURLToPath(new URL('../src/setup.mjs', import.meta.url));
const PROBE = fileURLToPath(new URL('../probes/setup.mjs', import.meta.url));

const TEMPLATE_IMPORT = "import * as rt from '__PKG__/src/rt.mjs';";
const PROBE_IMPORT = "import * as rt from '../src/rt.mjs';";

/** The statements the template owes, in order (design §5, the driver's contract). */
const BODY = [
  "import { beforeEach, expect } from 'vitest';",
  TEMPLATE_IMPORT,
  'rt.nameProvider(() => expect.getState().currentTestName ?? null);',
  'rt.fileStart(expect.getState().testPath ?? null, expect.getState().environment ?? null);',
  'beforeEach(() => { rt.seen(expect.getState().currentTestName ?? null); });',
];

/** @param {string} file @returns {string[]} */
const lines = (file) => fs.readFileSync(file, 'utf8').split('\n');

test('the setup template says exactly what the driver has to write', () => {
  const code = lines(TEMPLATE).filter((line) => !line.startsWith('//') && line !== '');
  assert.deepEqual(code, BODY);
});

test('R2: the probe copy differs from the template on the import line alone', () => {
  const template = lines(TEMPLATE);
  const probe = lines(PROBE);
  assert.equal(probe.length, template.length);
  const differing = template
    .map((line, i) => (line === probe[i] ? -1 : i))
    .filter((i) => i !== -1);
  assert.equal(differing.length, 1, `differing lines: ${JSON.stringify(differing)}`);
  assert.deepEqual(
    [template[differing[0]], probe[differing[0]]],
    [TEMPLATE_IMPORT, PROBE_IMPORT],
  );
});

test('neither copy names a placeholder the other has already resolved', () => {
  assert.equal(fs.readFileSync(PROBE, 'utf8').includes('__PKG__'), false);
  assert.equal(lines(TEMPLATE).filter((line) => line.includes('__PKG__')).length, 1);
});
