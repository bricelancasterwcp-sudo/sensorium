// The spec matcher, one test per spelling spec §2.1 allows and per rule
// `focus.mjs` writes down. The site-spelling table is a FIXTURE
// (`fixtures/site-spellings.json`) rather than a literal here, because the same
// table is read by the Python matcher's test at Task 7: one rule, two
// implementations, one file that says what the rule is (spec §4.3).
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

import {
  SEP,
  closest,
  fileMatches,
  parseSpec,
  qualnameMatches,
  specMatches,
  specsFromEnv,
} from '../src/focus.mjs';

/** @type {{rel: string, qualname: string, matching: string[], not_matching: string[]}} */
const TABLE = JSON.parse(
  readFileSync(new URL('./fixtures/site-spellings.json', import.meta.url), 'utf8'),
);

// ------------------------------------------------------------- the separator

test('SEP is the unit separator', () => {
  assert.equal(SEP, '\u001f');
  assert.equal(SEP.charCodeAt(0), 31);
  assert.equal(SEP.length, 1);
});

// ------------------------------------------------------------- specsFromEnv

test('specsFromEnv of an empty value is no specs at all', () => {
  assert.deepEqual(specsFromEnv(''), []);
});

test('specsFromEnv splits on the separator', () => {
  assert.deepEqual(specsFromEnv(`a${SEP}b.c${SEP}d.ts:e`), ['a', 'b.c', 'd.ts:e']);
});

test('specsFromEnv drops an empty field rather than minting a spec that matches all', () => {
  assert.deepEqual(specsFromEnv(`${SEP}a${SEP}${SEP}b${SEP}`), ['a', 'b']);
});

test('specsFromEnv of a single spec is that spec', () => {
  assert.deepEqual(specsFromEnv('Fog.compute'), ['Fog.compute']);
});

// ----------------------------------------------------------------- parseSpec

test('parseSpec reads a file part and a qualname', () => {
  assert.deepEqual(parseSpec('src/a.ts:Fog.run'), { file: 'src/a.ts', qualname: 'Fog.run' });
});

test('parseSpec of a bare qualname has no file part', () => {
  assert.deepEqual(parseSpec('Fog.run'), { file: null, qualname: 'Fog.run' });
});

test('parseSpec splits at the FIRST colon — a later one belongs to the qualname', () => {
  assert.deepEqual(parseSpec('src/a.ts:Fog:run'), { file: 'src/a.ts', qualname: 'Fog:run' });
});

// ----------------------------------------------------------- qualnameMatches

test('qualnameMatches an equal name', () => {
  assert.equal(qualnameMatches('Fog.compute', 'Fog.compute'), true);
});

test('qualnameMatches a container on a dot boundary', () => {
  assert.equal(qualnameMatches('Fog.compute', 'Fog'), true);
  assert.equal(qualnameMatches('refresh.<anonymous>', 'refresh'), true);
});

test('qualnameMatches nothing that shares only a prefix of a segment', () => {
  assert.equal(qualnameMatches('Fogs.compute', 'Fog'), false);
});

test('qualnameMatches is a prefix rule, not a suffix one', () => {
  assert.equal(qualnameMatches('Fog.compute', 'compute'), false);
});

test('qualnameMatches nothing longer than the name itself', () => {
  assert.equal(qualnameMatches('Fog.compute', 'Fog.compute.x'), false);
});

// --------------------------------------------------------------- fileMatches

test('fileMatches the root-relative path', () => {
  assert.equal(fileMatches('src/lib/cache.ts', 'src/lib/cache.ts'), true);
});

test('fileMatches the basename', () => {
  assert.equal(fileMatches('src/lib/cache.ts', 'cache.ts'), true);
});

test('fileMatches the stem, which strips the LAST extension only', () => {
  assert.equal(fileMatches('src/lib/cache.ts', 'cache'), true);
  assert.equal(fileMatches('src/lib/cache.test.ts', 'cache.test'), true);
  assert.equal(fileMatches('src/lib/cache.test.ts', 'cache'), false);
});

test('fileMatches no directory segment and no partial path', () => {
  assert.equal(fileMatches('src/lib/cache.ts', 'lib'), false);
  assert.equal(fileMatches('src/lib/cache.ts', 'src/cache.ts'), false);
  assert.equal(fileMatches('src/lib/cache.ts', 'lib/cache.ts'), false);
});

// --------------------------------------------------- specMatches: the fixture

test('every spelling the fixture calls matching matches the site', () => {
  for (const spec of TABLE.matching) {
    assert.equal(specMatches(spec, TABLE.rel, TABLE.qualname), true, spec);
  }
});

test('every spelling the fixture calls not matching does not match the site', () => {
  for (const spec of TABLE.not_matching) {
    assert.equal(specMatches(spec, TABLE.rel, TABLE.qualname), false, spec);
  }
});

test('the fixture is the table both implementations read', () => {
  assert.equal(TABLE.rel, 'src/lib/cache.ts');
  assert.equal(TABLE.qualname, 'Fog.compute');
  assert.equal(TABLE.matching.length, 5);
  assert.equal(TABLE.not_matching.length, 5);
});

test('specMatches narrows by the file part and never widens', () => {
  assert.equal(specMatches('other.ts:Fog', 'src/lib/cache.ts', 'Fog.compute'), false);
  assert.equal(specMatches('Fog', 'anywhere/else.ts', 'Fog.compute'), true);
});

// ------------------------------------------------------------------- closest

test('closest orders by shared trailing segments, then by name', () => {
  assert.deepEqual(closest(['m.f', 'S.k', 'h'], 'wrong.f'), ['m.f', 'S.k', 'h']);
});

test('closest of nothing eligible is nothing — the sentence drops the clause', () => {
  assert.deepEqual(closest([], 'x'), []);
});

test('closest keeps at most three, and takes the limit it is given', () => {
  const eligible = ['a.run', 'b.run', 'c.run', 'd.run', 'e.walk'];
  assert.deepEqual(closest(eligible, 'z.run'), ['a.run', 'b.run', 'c.run']);
  assert.deepEqual(closest(eligible, 'z.run', 1), ['a.run']);
  assert.deepEqual(closest(eligible, 'z.run', 5), ['a.run', 'b.run', 'c.run', 'd.run', 'e.walk']);
});

test('closest counts whole trailing segments, most first', () => {
  assert.deepEqual(closest(['x.Fog.compute', 'Fog.compute', 'compute', 'other'], 'y.Fog.compute'),
    ['Fog.compute', 'x.Fog.compute', 'compute']);
});

test('closest matches a segment whole — a shared prefix of one counts for nothing', () => {
  assert.deepEqual(closest(['comp', 'compute'], 'compute'), ['compute', 'comp']);
});

test('closest reads the spec\'s qualname part, so a file part never reaches it', () => {
  const { qualname } = parseSpec('src/a.ts:refrsh');
  assert.deepEqual(closest(['refresh', 'refreshAll'], qualname), ['refresh', 'refreshAll']);
});
