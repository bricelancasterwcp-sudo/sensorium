// What `--focus` selects, answered BEFORE the run. `node src/resolve.mjs`,
// reading the root and the specs from the environment, one JSON line out.
//
// The driver runs this and refuses on what comes back, so the caller learns a
// mistyped spec in the second it takes to walk the tree rather than in the
// minutes it takes to run a suite that recorded the wrong thing — or nothing.
// A focus that matched nothing is the worst of the two: the transform would
// splice no statement probes at all, the runtime would still declare `line`,
// and the trace would say the recorder looked and found nothing to say.
//
// It reuses the transform's OWN pass one (`sitesOf`) and the same matcher the
// transform splices with (`focus.mjs`), so the two cannot disagree about what a
// spec selects. Nothing here splices, writes, or runs the consumer's code: it
// reads files and parses them.
//
// Environment (all three set by the driver; the first two are required here):
//   SENSORIUM_TS_ROOT  the project directory to walk
//   SENSORIUM_FOCUS    the specs, joined by the unit separator
//   SENSORIUM_TS_PKG   this package — unread: this script's imports are its own
//                      siblings, and it is exported only so the resolver's
//                      environment is the harness's
//
// Exit 0 with one JSON line on stdout, ALWAYS — an unmatched spec is an answer,
// not a failure, and the driver is what turns it into a refusal. Exit 2 with one
// line on stderr is reserved for a call this script cannot make sense of at all:
// a missing variable, a root that is not a directory, a consumer with no
// TypeScript to parse with.
import fs from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

import { closest, parseSpec, specMatches, specsFromEnv } from './focus.mjs';
import { ANONYMOUS } from './qualname.mjs';
import { classify, sitesOf } from './transform.mjs';

/** Directories the walk never enters: dependencies, and our own workspace. */
const SKIP_DIRS = new Set(['node_modules', '.sensorium']);

/** How many names an unmatched spec is offered. */
const SUGGESTIONS = 3;

/**
 * One line on stderr and exit 2. The caller is the driver, which prints this
 * verbatim behind its own `error:`, so it is a sentence and not a stack.
 * @param {string} message
 * @returns {never}
 */
function refuse(message) {
  process.stderr.write(`${message}\n`);
  process.exit(2);
}

/**
 * Every file under `dir`, recursively, in name order.
 *
 * A SYMLINK is not followed — neither a linked directory (a cycle is a hang,
 * and `node_modules` is full of them) nor a linked file, whose real path is
 * walked already when it is under the root and is not this recorder's business
 * when it is not.
 * @param {string} dir
 * @returns {Generator<string>}
 */
function* walk(dir) {
  /** @type {fs.Dirent[]} */
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    // A directory that cannot be read is not a reason to refuse a focus the
    // rest of the tree can answer: it offers no files, and the walk goes on.
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
 * Pass one over every eligible file under the root.
 * @param {string} root
 * @param {typeof import('typescript')} ts
 * @returns {{eligible: {rel: string, qualname: string, line: number, kind: string}[],
 *   excluded: {rel: string, qualname: string, line: number, reason: string}[],
 *   scanned: number, unparsable: number}}
 */
function survey(root, ts) {
  /** @type {{rel: string, qualname: string, line: number, kind: string}[]} */
  const eligible = [];
  /** @type {{rel: string, qualname: string, line: number, reason: string}[]} */
  const excluded = [];
  let scanned = 0;
  let unparsable = 0;
  for (const file of walk(root)) {
    if (classify(file, root) !== 'transform') continue;
    scanned += 1;
    /** @type {string} */
    let code;
    try {
      code = fs.readFileSync(file, 'utf8');
    } catch {
      // Counted with the unparsable: either way the file offered no sites,
      // and a resolver that dropped it silently would make `files_scanned`
      // a number nobody could reconcile.
      unparsable += 1;
      continue;
    }
    const out = sitesOf(code, file, { root, ts });
    if (out === null) continue;
    if (out.excluded['parse-error']) {
      unparsable += 1;
      continue;
    }
    for (const site of out.sites) {
      eligible.push({ rel: out.rel, qualname: site.qualname, line: site.line, kind: site.kind });
    }
    for (const site of out.excludedSites) {
      excluded.push({ rel: out.rel, qualname: site.qualname, line: site.line, reason: site.reason });
    }
  }
  return { eligible, excluded, scanned, unparsable };
}

/**
 * The names an unmatched spec is offered, in order.
 *
 * A name with an `<anonymous>` segment is left out: it is not a name the
 * caller can type back (`<` is the shell's, and an anonymous function carries
 * no ordinal to tell it from its siblings), and a suggestion nobody can retype
 * is worse than none — it fills the three slots a usable name wanted.
 * @param {{qualname: string}[]} eligible
 * @param {string} spec
 * @returns {string[]}
 */
function suggestions(eligible, spec) {
  const names = [...new Set(eligible.map((site) => site.qualname))]
    .filter((name) => !name.split('.').includes(ANONYMOUS));
  if (names.length === 0) return [];
  return closest(names, parseSpec(spec).qualname, SUGGESTIONS);
}

/**
 * @param {{rel: string, qualname: string, line: number, reason: string}[]} hits
 * @returns {Record<string, number>} how many of each reason, for the refusal
 */
function reasonsOf(hits) {
  /** @type {Record<string, number>} */
  const reasons = {};
  for (const hit of hits) reasons[hit.reason] = (reasons[hit.reason] ?? 0) + 1;
  return reasons;
}

function main() {
  const rootVar = process.env.SENSORIUM_TS_ROOT;
  if (!rootVar) refuse('SENSORIUM_TS_ROOT names no directory: the resolver walks a project root');
  const root = path.resolve(/** @type {string} */ (rootVar));
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
    refuse(`${root} is not a directory: the resolver walks a project root`);
  }
  const specs = specsFromEnv(process.env.SENSORIUM_FOCUS ?? '');
  if (specs.length === 0) {
    refuse('SENSORIUM_FOCUS names no spec: the resolver answers a focus, and there is none');
  }

  // The consumer's own TypeScript, resolved from the ROOT exactly as the
  // loader hook and the Vite plugin resolve it: the sites this reports are
  // the sites the transform will find, or they are somebody else's AST.
  const require = createRequire(path.join(root, 'package.json'));
  /** @type {typeof import('typescript')} */
  let ts;
  try {
    ts = require('typescript');
  } catch {
    refuse(`${root} has no typescript in node_modules: the resolver reads the same AST the `
      + 'transform will, and there is none here to read it with');
  }

  const { eligible, excluded, scanned, unparsable } = survey(root, /** @type {any} */ (ts));

  /** @type {{rel: string, qualname: string, line: number, kind: string}[]} */
  const matched = [];
  const seen = new Set();
  /** @type {{spec: string, closest: string[]}[]} */
  const unmatched = [];
  /** @type {{spec: string, reasons: Record<string, number>}[]} */
  const excludedOnly = [];
  for (const spec of specs) {
    const hits = eligible.filter((site) => specMatches(spec, site.rel, site.qualname));
    if (hits.length > 0) {
      // One entry per FUNCTION, not per spec: two specs that name the same
      // function focus it once, and `focus_matched` says so once.
      for (const hit of hits) {
        const key = `${hit.rel}:${hit.qualname}:${hit.line}`;
        if (seen.has(key)) continue;
        seen.add(key);
        matched.push(hit);
      }
      continue;
    }
    const skipped = excluded.filter((site) => specMatches(spec, site.rel, site.qualname));
    if (skipped.length > 0) excludedOnly.push({ spec, reasons: reasonsOf(skipped) });
    else unmatched.push({ spec, closest: suggestions(eligible, spec) });
  }

  process.stdout.write(`${JSON.stringify({
    matched,
    unmatched,
    excluded_only: excludedOnly,
    files_scanned: scanned,
    files_unparsable: unparsable,
  })}\n`);
}

main();
