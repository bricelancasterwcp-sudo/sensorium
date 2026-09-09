// Census: run the transform over a consumer's own `src` tree, with the
// consumer's own TypeScript, and print what it did as JSON. Nothing is written
// and nothing is executed — this reads files and reports.
//
//   node acceptance/census.mjs <root>
//
// The keys:
//   files         files transformed
//   failed        [{file, error}] — files the transform threw on; must be empty
//   parse_error   files the consumer's own parser rejected, so they were left
//                 untouched and counted rather than spliced blind (R10)
//   instrumented  function sites instrumented across the tree
//   excluded      every exclusion, by its own name, summed over the tree
//   by_kind       instrumented sites by the contract's frame kind
//   eligible      instrumented + excluded functions (every function-like seen)
//   ratio         instrumented / eligible
//   bloat         output bytes / input bytes
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

import { classify, transformSource } from '../src/transform.mjs';

/** Exclusions that count a whole file, not a function inside one. */
const FILE_LEVEL_REASONS = new Set(['commonjs', 'parse-error']);

/** Files a run instruments but a source census does not measure. */
const SKIP_NAME = /(\.test\.|\.spec\.|\.d\.ts$|^test-setup\.ts$|^setupTests\.)/;
const SKIP_DIR = new Set(['node_modules', '__tests__', '__mocks__', '.git']);

/**
 * @param {string} dir
 * @returns {string[]} absolute paths, depth first, sorted
 */
function walk(dir) {
  /** @type {string[]} */
  const found = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
    a.name < b.name ? -1 : 1,
  )) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIR.has(entry.name)) found.push(...walk(full));
    } else if (entry.isFile() && !SKIP_NAME.test(entry.name)) {
      found.push(full);
    }
  }
  return found;
}

/**
 * @param {string} root absolute path to the consumer's package root
 * @returns {Record<string, unknown>}
 */
function census(root) {
  const require = createRequire(path.join(root, 'package.json'));
  const ts = require('typescript');
  /** @type {{file: string, error: string}[]} */
  const failed = [];
  /** @type {string[]} */
  const parseError = [];
  /** @type {Record<string, number>} */
  const excluded = {};
  /** @type {Record<string, number>} */
  const byKind = {};
  let files = 0;
  let instrumented = 0;
  let inBytes = 0;
  let outBytes = 0;

  /** @param {Record<string, number>} tally @param {string} key @param {number} n */
  const add = (tally, key, n) => {
    tally[key] = (tally[key] ?? 0) + n;
  };

  for (const file of walk(path.join(root, 'src'))) {
    const verdict = classify(file, root);
    if (verdict === 'commonjs') add(excluded, 'commonjs', 1);
    if (verdict !== 'transform') continue;
    const code = fs.readFileSync(file, 'utf8');
    try {
      const out = transformSource(code, file, { root, ts, rtPath: 'sensorium-ts/rt' });
      if (!out) continue;
      for (const [reason, n] of Object.entries(out.manifest.excluded)) add(excluded, reason, n);
      if (out.code === null) {
        parseError.push(file);
        continue;
      }
      files += 1;
      inBytes += Buffer.byteLength(code);
      outBytes += Buffer.byteLength(out.code);
      instrumented += out.manifest.instrumented.length;
      for (const site of out.manifest.instrumented) add(byKind, site.kind, 1);
      if (out.code.split('\n').length !== code.split('\n').length) {
        failed.push({ file, error: 'line count changed' });
      }
    } catch (err) {
      failed.push({ file, error: err instanceof Error ? `${err.name}: ${err.message}` : String(err) });
    }
  }

  const functionExclusions = Object.entries(excluded)
    .filter(([reason]) => !FILE_LEVEL_REASONS.has(reason))
    .reduce((sum, [, n]) => sum + n, 0);
  const eligible = instrumented + functionExclusions;
  return {
    files,
    failed,
    parse_error: parseError,
    instrumented,
    excluded,
    by_kind: byKind,
    eligible,
    ratio: eligible === 0 ? 0 : Number((instrumented / eligible).toFixed(4)),
    bloat: inBytes === 0 ? 0 : Number((outBytes / inBytes).toFixed(4)),
  };
}

const root = process.argv[2];
if (!root) {
  process.stderr.write('usage: node acceptance/census.mjs <root>\n');
  process.exit(2);
}
process.stdout.write(`${JSON.stringify(census(path.resolve(root)), null, 2)}\n`);
