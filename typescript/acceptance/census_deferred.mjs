// The seal-deferred census (design §4.6): walk a root with the transform's own
// pass one and print every function whose exit the seal defers — the ones whose
// wrapper 0.4.0 moves, and by omission every function it does not touch.
// Nothing is written and nothing is executed; this reads files and reports.
//
//   node acceptance/census_deferred.mjs <root> [<root> …]
//
// One object per root, IN THE ORDER GIVEN, because the record's §1 fixes that
// order (the probes, the corpus, the lens) and a root's own path is not
// something this slice commits:
//
//   {"roots": [{"root": "<as given>",
//               "deferred": [{"rel": …, "qualname": …, "line": …}, …],
//               "files_scanned": n,
//               "typescript": "consumer"|"recorder"}, …]}
//
// `rel` is repository-relative for a root inside this repository — the spelling
// the hand census's tables use — and root-relative for one outside it, which
// the lens is. `line` is the function's own definition line.
//
// A root may be a DIRECTORY or a single FILE: §4.6's third root is one file,
// and censusing the directory around it would answer a question nobody asked.
//
// The comparison against the hand-counted census is `census_matches` in
// `e12p_h8.py`; this prints, it does not judge.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

import { classify, sitesOf } from '../src/transform.mjs';

/** Directories the walk never enters — `resolve.mjs`'s set, for its reasons. */
const SKIP_DIRS = new Set(['node_modules', '.sensorium']);

/** This repository's root: `<repo>/typescript/acceptance/` is where we live. */
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

/**
 * Every file under `dir`, recursively, in name order. A symlink is not
 * followed, for `resolve.mjs`'s reasons: a linked directory is a cycle waiting
 * to hang, and a linked file's real path is walked already or is not ours.
 * @param {string} dir
 * @returns {Generator<string>}
 */
function* walk(dir) {
  /** @type {fs.Dirent[]} */
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries.sort((a, b) => (a.name < b.name ? -1 : 1))) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name)) yield* walk(full);
    } else if (entry.isFile()) {
      yield full;
    }
  }
}

/**
 * The consumer's own TypeScript where the root has one, this package's where it
 * has not. Which of the two is REPORTED rather than assumed: the sites a census
 * prints are the sites that parser found.
 * @param {string} dir
 * @returns {{ts: typeof import('typescript'), from: string}}
 */
function typescriptFor(dir) {
  try {
    const consumer = createRequire(path.join(dir, 'package.json'));
    return { ts: consumer('typescript'), from: 'consumer' };
  } catch {
    const own = createRequire(import.meta.url);
    return { ts: own('typescript'), from: 'recorder' };
  }
}

/**
 * @param {string} file absolute path
 * @param {string} dir the root the walk started at
 * @returns {string} the path this census spells the file with
 */
function relOf(file, dir) {
  const fromRepo = path.relative(REPO, file);
  const inRepo = fromRepo !== '' && !fromRepo.startsWith('..') && !path.isAbsolute(fromRepo);
  return (inRepo ? fromRepo : path.relative(dir, file)).split(path.sep).join('/');
}

/**
 * One root's census.
 * @param {string} given the root as the caller typed it
 * @returns {{root: string, deferred: {rel: string, qualname: string, line: number}[],
 *   files_scanned: number, typescript: string}}
 */
function census(given) {
  const full = path.resolve(given);
  const isFile = fs.statSync(full).isFile();
  // A file root is classified against its own directory: `classify` refuses a
  // path that IS the root, and the question here is about the file.
  const dir = isFile ? path.dirname(full) : full;
  const { ts, from } = typescriptFor(dir);
  /** @type {{rel: string, qualname: string, line: number}[]} */
  const deferred = [];
  let scanned = 0;
  for (const file of isFile ? [full] : walk(dir)) {
    if (classify(file, dir) !== 'transform') continue;
    scanned += 1;
    const out = sitesOf(fs.readFileSync(file, 'utf8'), file, { root: dir, ts });
    // A file the parser rejected offers no sites and says so through
    // `excluded['parse-error']`; either way there is nothing to count here.
    if (out === null) continue;
    for (const site of out.sites) {
      if (site.deferred) {
        deferred.push({ rel: relOf(file, dir), qualname: site.qualname, line: site.line });
      }
    }
  }
  return { root: given, deferred, files_scanned: scanned, typescript: from };
}

const roots = process.argv.slice(2);
if (roots.length === 0) {
  process.stderr.write('usage: node acceptance/census_deferred.mjs <root> [<root> …]\n');
  process.exit(2);
}
process.stdout.write(`${JSON.stringify({ roots: roots.map(census) }, null, 2)}\n`);
