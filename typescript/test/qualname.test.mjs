// Test and suite callbacks are named from the call. Every other nameless
// function stays `<anonymous>` with no ordinal: two of those on one line still
// share a fingerprint key (HONESTY blind spot 1).
import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';

import { sitesOf } from '../src/transform.mjs';

const require = createRequire(import.meta.url);
const ts = require('typescript');

const SRC = [
  'import { describe, it, test, suite } from "vitest";',
  '',
  'describe("math", () => {',
  '  it("adds", () => {});',
  '});',
  '',
  'it.skip("skips", () => {});',
  'test.only("solo", () => {});',
  'suite("edges", () => {});',
  'describe.each(table)("group", () => {});',
  'test.each(rows)("row", () => {});',
  'it.skip.each(rows)("skipped row", () => {});',
  'test.each`a | b`("cell", () => {});',
  'test("opt", { timeout: 1 }, () => {});',
  'test(name, () => {});',
  'it(`tmpl`, () => {});',
  'it(`tmpl ${x}`, () => {});',
  'it("say \\"hi\\"", () => {});',
  'it("a\\\\b", () => {});',
  'it("a.b", () => {});',
  'test("kept", function kept() {});',
  'test("cond", flag ? () => 1 : () => 2);',
  'it("paren", (() => {}));',
  'it("maps", () => {',
  '  [1].map((n) => n);',
  '});',
  'const twins = [(n) => n, (m) => m];',
  '',
].join('\n');

test('a test or suite callback is named from the root callee and the title', () => {
  const out = sitesOf(SRC, '/w/src/names.ts', { root: '/w', ts });
  assert.ok(out);
  assert.deepEqual(out.sites.map((site) => site.qualname), [
    'describe("math")',
    'describe("math").it("adds")',
    'it("skips")',
    'test("solo")',
    'suite("edges")',
    'describe("group")',
    'test("row")',
    'it("skipped row")',
    'test("cell")',
    'test("opt")',
    '<anonymous>',
    'it("tmpl")',
    '<anonymous>',
    'it("say \\"hi\\"")',
    'it("a\\\\b")',
    'it("a.b")',
    'kept',
    '<anonymous>',
    '<anonymous>',
    '<anonymous>',
    'it("maps")',
    'it("maps").<anonymous>',
    '<anonymous>',
    '<anonymous>',
  ]);

  const lines = SRC.split('\n');
  const condLine = lines.findIndex((line) => line.startsWith('test("cond"')) + 1;
  const twinLine = lines.findIndex((line) => line.startsWith('const twins')) + 1;
  // Not direct callbacks, and not test callbacks: same line, same name, no ordinal.
  for (const line of [condLine, twinLine]) {
    /** @type {string[]} */
    const names = [];
    for (const site of out.sites) {
      if (site.line === line) names.push(site.qualname);
    }
    assert.deepEqual(names, ['<anonymous>', '<anonymous>']);
  }
});
