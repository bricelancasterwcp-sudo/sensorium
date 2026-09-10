// Census: the catch sites the transform SEES on a consumer's own `src` tree,
// counted with the consumer's own TypeScript, printed as JSON. Nothing is
// written and nothing is executed — this reads files and reports (rung 1's
// `census.mjs` shape).
//
//   node acceptance/census_catch.mjs <root>
//
// This is E2″'s instrument: "is every catch site instrumented?" is a ratio of
// what the transform SPLICED over what an AST walk SAW, and a ratio needs both
// halves measured by something other than the thing under test. The `seen`
// half is here. The `spliced` half is the transform's own per-file manifest,
// which does not carry catch sites yet — S5 rung 2 Task 2 adds them — so
// `spliced` is `{}` and `ratio` is `null` until then, and `note` says so. A
// ratio invented from one half would read as 1.000 and mean nothing.
//
// The keys:
//   files              eligible files walked (`classify()` said `transform`)
//   catch_clauses      every `CatchClause` in the tree
//   callback_sites     `.catch(<one arg>)` call expressions (spec §2.2)
//   then_sites         `.then(<two args>)` call expressions (spec §2.2)
//   finally_completing `TryStatement`s whose `finallyBlock` holds a `return`,
//                      `break` or `continue` at closure depth 0 (spec §2.3)
//   excluded           every ineligible file, by `classify()`'s own verdict
//   parse_error        files the consumer's own parser rejected, so they were
//                      counted rather than walked blind (R10)
//   failed             [{file, error}] — files this census threw on; must be
//                      empty on the lens, and a non-empty list is a refusal to
//                      report a count taken over a tree it could not read
//   spliced            what the transform recorded splicing, by `how`
//   ratio              spliced / seen, after NAMED exclusions
//   note               why `spliced` and `ratio` read as they do
//
// `scriptKind` and `parseDiagnostics` below mirror `transform.mjs`'s own
// private `scriptKindFor` and `parseErrors`. They are duplicated rather than
// exported because Task 0 changes nothing under `typescript/src/`; Task 7
// re-runs this instrument against the same two rules, and a divergence between
// them would show up as a `parse_error` count that the run does not share.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

import { classify } from '../src/transform.mjs';

/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').SourceFile} SourceFile */
/** @typedef {import('typescript').Block} Block */
/** @typedef {{file: string, error: string}} Failure */
/** The printed shape, named so the refusal below can read `failed` as a list
 *  rather than as `unknown` — a report typed loosely enough to index blindly
 *  is a report whose precondition cannot be checked. */
/** @typedef {{files: number, catch_clauses: number, callback_sites: number,
 *    then_sites: number, finally_completing: number,
 *    excluded: Record<string, number>, parse_error: string[],
 *    failed: Failure[], spliced: Record<string, number>,
 *    ratio: number|null, note: string}} Report */

/** Directories never descended into. `classify()` refuses `node_modules` paths
 *  anyway; not walking them is what keeps this instrument's cost sane. */
const SKIP_DIR = new Set(['node_modules', '.git']);

/**
 * A **symlink** under `src` is neither walked nor counted: `Dirent.isFile()`
 * describes the link, not its target, so it is reported here rather than
 * discovered later as a gap in the denominator. `census.mjs` has the same
 * blind spot, and both roots this ran on at T0 hold zero symlinks under `src`
 * (`find <root>/src -type l | wc -l` → 0), so it is inert where E2″ measures.
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
    } else if (entry.isFile()) {
      found.push(full);
    }
  }
  return found;
}

/**
 * @param {TS} ts
 * @param {string} filePath
 * @returns {import('typescript').ScriptKind}
 */
function scriptKind(ts, filePath) {
  const ext = path.extname(filePath);
  if (ext === '.tsx') return ts.ScriptKind.TSX;
  if (ext === '.ts' || ext === '.mts') return ts.ScriptKind.TS;
  return ts.ScriptKind.JSX;
}

/**
 * The parser's own complaints. An ABSENT `parseDiagnostics` is not an absence
 * of errors (R10a): a TypeScript build that dropped the field would have this
 * census walk a recovered tree and report its counts as the file's.
 * @param {SourceFile} sf
 * @returns {number} how many the parser raised
 */
function parseDiagnostics(sf) {
  const diagnostics = /** @type {import('typescript').Diagnostic[]|undefined} */ (
    /** @type {any} */ (sf).parseDiagnostics
  );
  if (!Array.isArray(diagnostics)) {
    throw new Error(
      'sensorium-ts: this TypeScript build exposes no parseDiagnostics; refusing to count blind',
    );
  }
  return diagnostics.length;
}

/**
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean} whether `node` opens a new closure, so the walk below it
 *   is at a deeper closure depth
 */
function opensClosure(ts, node) {
  return (
    ts.isFunctionDeclaration(node) ||
    ts.isFunctionExpression(node) ||
    ts.isArrowFunction(node) ||
    ts.isMethodDeclaration(node) ||
    ts.isConstructorDeclaration(node) ||
    ts.isGetAccessorDeclaration(node) ||
    ts.isSetAccessorDeclaration(node) ||
    ts.isClassDeclaration(node) ||
    ts.isClassExpression(node)
  );
}

/**
 * Spec §2.3's rule, exactly: a `finally` block holding a `return`, `break` or
 * `continue` **at closure depth 0** discards an in-flight throw. Depth 0 is the
 * spec's word and this is its literal reading — a `break` inside a loop written
 * in the `finally` body counts, because the spec's rule is syntactic and Task 2
 * splices from the same rule. A rule read two ways is two rules.
 * @param {TS} ts
 * @param {Block} block
 * @returns {boolean}
 */
function completes(ts, block) {
  let found = false;
  /** @param {Node} node */
  const visit = (node) => {
    if (found || opensClosure(ts, node)) return;
    if (
      ts.isReturnStatement(node) ||
      ts.isBreakStatement(node) ||
      ts.isContinueStatement(node)
    ) {
      found = true;
      return;
    }
    ts.forEachChild(node, visit);
  };
  ts.forEachChild(block, visit);
  return found;
}

/**
 * `.catch(<one arg>)` and `.then(<two args>)` — spec §2.2's two call shapes.
 * `.catch()` with no argument and `.then(x)` with one are NOT sites: the spec
 * does not touch them, so counting them would put a miss in the denominator
 * that no splice was ever meant to fill.
 * @param {TS} ts
 * @param {Node} node
 * @returns {'catch'|'then'|null}
 */
function callbackSite(ts, node) {
  if (!ts.isCallExpression(node)) return null;
  const callee = node.expression;
  if (!ts.isPropertyAccessExpression(callee)) return null;
  if (callee.name.text === 'catch' && node.arguments.length === 1) return 'catch';
  if (callee.name.text === 'then' && node.arguments.length === 2) return 'then';
  return null;
}

/**
 * @param {string} root absolute path to the consumer's package root
 * @returns {Report}
 */
function census(root) {
  const require = createRequire(path.join(root, 'package.json'));
  const ts = require('typescript');
  /** @type {Failure[]} */
  const failed = [];
  /** @type {string[]} */
  const parseError = [];
  /** @type {Record<string, number>} */
  const excluded = {};
  let files = 0;
  let catchClauses = 0;
  let callbackSites = 0;
  let thenSites = 0;
  let finallyCompleting = 0;

  for (const file of walk(path.join(root, 'src'))) {
    const verdict = classify(file, root);
    if (verdict !== 'transform') {
      excluded[verdict] = (excluded[verdict] ?? 0) + 1;
      continue;
    }
    try {
      const code = fs.readFileSync(file, 'utf8');
      const sf = ts.createSourceFile(
        file,
        code,
        ts.ScriptTarget.Latest,
        true,
        scriptKind(ts, file),
      );
      if (parseDiagnostics(sf) > 0) {
        parseError.push(path.relative(root, file));
        continue;
      }
      files += 1;
      /** @param {Node} node */
      const visit = (node) => {
        if (ts.isCatchClause(node)) catchClauses += 1;
        if (ts.isTryStatement(node) && node.finallyBlock && completes(ts, node.finallyBlock)) {
          finallyCompleting += 1;
        }
        const site = callbackSite(ts, node);
        if (site === 'catch') callbackSites += 1;
        if (site === 'then') thenSites += 1;
        ts.forEachChild(node, visit);
      };
      ts.forEachChild(sf, visit);
    } catch (err) {
      // Node's own filesystem messages carry the ABSOLUTE path, and this list
      // is the one part of the output a failure puts prose into. The root is
      // cut out of it, as it already is out of `file`, so nothing this prints
      // can carry a box path into a record.
      const text = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
      failed.push({
        file: path.relative(root, file),
        error: text.split(`${root}/`).join(''),
      });
    }
  }

  return {
    files,
    catch_clauses: catchClauses,
    callback_sites: callbackSites,
    then_sites: thenSites,
    finally_completing: finallyCompleting,
    excluded,
    parse_error: parseError,
    failed,
    spliced: {},
    ratio: null,
    note:
      'The transform does not record catch sites in its per-file manifest yet, ' +
      'so `spliced` is empty and `ratio` is null rather than 1.000 over a ' +
      'denominator with no numerator. S5 rung 2 Task 2 adds the splice and its ' +
      'manifest entries; Task 7 re-runs this instrument and fills both.',
  };
}

const root = process.argv[2];
if (!root) {
  process.stderr.write('usage: node acceptance/census_catch.mjs <root>\n');
  process.exit(2);
}
const resolved = path.resolve(root);
for (const needed of [path.join(resolved, 'package.json'), path.join(resolved, 'src')]) {
  if (!fs.existsSync(needed)) {
    process.stderr.write(`census_catch: ${resolved} is not a consumer root (no ${path.basename(needed)})\n`);
    process.exit(2);
  }
}
const out = census(resolved);
process.stdout.write(`${JSON.stringify(out, null, 2)}\n`);
// A count taken over a tree this census could not fully read is not the
// denominator E2″ divides by, and printing it under a zero exit code would let
// a caller use it as one. The JSON goes out first — the `failed` list is the
// evidence for the refusal — and then this exits 1. (2 above is the bad-root
// code: a root that was never walked, as against a walk that came up short.)
if (out.failed.length > 0) {
  process.stderr.write(
    `census_catch: ${out.failed.length} file(s) could not be read; the counts ` +
      "above are over a tree this census did not fully see, and are not E2″'s " +
      'denominator\n',
  );
  process.exit(1);
}
