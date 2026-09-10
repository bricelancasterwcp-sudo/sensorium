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
// half is the AST walk below. The `spliced` half is the transform's OWN OUTPUT
// (Task 2's ruling, 2026-09-10): each eligible file is handed to
// `transformSource` and the markers `__srt.handled(` / `__srt.catchCb(` /
// `__srt.handledFinally(` are counted in what comes back, per LINE, against the
// site the walk saw at that line. No manifest key was added for this: the
// goldens hold the text's shape, and a numerator read out of the same walk that
// produced the denominator would be one rule counted twice rather than two
// halves. Splices are newline-free (the rung-1 invariant), so an original line
// number is the output's line number and the two halves line up exactly.
//
// At T0 this file had the `seen` half only and printed `spliced: {}` /
// `ratio: null`, which is what its two dry-run rows in the record's §2.2 hold.
//
// The keys:
//   files              eligible files walked (`classify()` said `transform`)
//   catch_clauses      every `CatchClause` in the tree
//   callback_sites     `.catch(<one arg>)` call expressions (spec §2.2)
//   then_sites         `.then(<two args>)` call expressions (spec §2.2)
//   finally_completing `TryStatement`s whose `finallyBlock` COMPLETES, by
//                      `escape.mjs`'s own `finallyCompletes` — the predicate the
//                      transform splices from (spec §2.3). Task 0 held a literal
//                      copy of the rule here, because `src/` had none yet; Task 2
//                      wrote it, and this census imports it rather than reading
//                      the same sentence a second way. A rule read two ways is
//                      two rules, and a denominator counted by the second one
//                      would not be the numerator's.
//   excluded           every ineligible file, by `classify()`'s own verdict
//   parse_error        files the consumer's own parser rejected, so they were
//                      counted rather than walked blind (R10)
//   failed             [{file, error}] — files this census threw on; must be
//                      empty on the lens, and a non-empty list is a refusal to
//                      report a count taken over a tree it could not read
//   spliced            markers found in the transform's output, by site kind
//   by_how             the `how` word each splice wrote, tallied — §1's
//                      ungated "share of catch clauses reading catch_escaped"
//   excluded_by_design [{file, line, kind, reason}] — sites the spec says are
//                      NOT spliced: a `.catch`/`.then` whose argument list holds
//                      a spread element (Task 2's Critical fix — `...args` is
//                      not an expression and wrapping it produces source the
//                      consumer's own parser rejects). These leave the
//                      denominator, which is what "after NAMED exclusions"
//                      means, and each is named here rather than counted away.
//   unspliced          [{file, line, kind, reason}] — every site the walk saw
//                      and the output does not carry a marker for, with what
//                      this census can say about why. NOT an exclusion: one of
//                      these is E2″'s unnamed miss and its STOP.
//   ratio              spliced / (seen - excluded_by_design)
//   note               how `spliced` and `ratio` were read
//
// `scriptKind` and `parseDiagnostics` below mirror `transform.mjs`'s own
// private `scriptKindFor` and `parseErrors`. They stay duplicated because both
// are private to a module this instrument must not reach into; Task 7 re-runs
// this instrument against the same two rules, and a divergence between them
// would show up as a `parse_error` count that the run does not share.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

import { finallyCompletes } from '../src/escape.mjs';
import { classify, transformSource } from '../src/transform.mjs';

/** @typedef {typeof import('typescript')} TS */
/** @typedef {import('typescript').Node} Node */
/** @typedef {import('typescript').SourceFile} SourceFile */
/** @typedef {import('typescript').Block} Block */
/** @typedef {{file: string, error: string}} Failure */
/** One site the walk saw, and the marker the transform owes it.
 *  @typedef {{kind: 'catch_clause'|'callback_site'|'then_site'|'finally_completing',
 *    marker: string, line: number, spread: boolean, hoisted: boolean}} Site */
/** @typedef {{file: string, line: number, kind: string, reason: string}} Miss */
/** The printed shape, named so the refusal below can read `failed` as a list
 *  rather than as `unknown` — a report typed loosely enough to index blindly
 *  is a report whose precondition cannot be checked. */
/** @typedef {{files: number, catch_clauses: number, callback_sites: number,
 *    then_sites: number, finally_completing: number,
 *    excluded: Record<string, number>, parse_error: string[],
 *    failed: Failure[], spliced: Record<string, number>,
 *    by_how: Record<string, number>, seen_total: number, eligible: number, spliced_total: number,
 *    excluded_by_design: Miss[], unspliced: Miss[],
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

/** The three markers, and the site kind each answers for. A marker is matched
 *  WITH its opening parenthesis: `__srt.handledFinally(` would otherwise be
 *  counted as a `__srt.handled` too, and the finally sink would be booked
 *  against the catch clauses. */
const MARKER = {
  catch_clause: '__srt.handled(',
  callback_site: '__srt.catchCb(',
  then_site: '__srt.catchCb(',
  finally_completing: '__srt.handledFinally(',
};

/**
 * `vi.mock` / `vi.doMock` / `vi.hoisted` / `vi.unmock` — the calls vitest hoists
 * above the transform's own header, whose whole subtree `transform.mjs`'s
 * `splice` returns from without visiting. A site inside one is a site the
 * transform never reaches, and this census says so by name rather than leaving
 * it as an unexplained miss.
 * @param {TS} ts
 * @param {Node} node
 * @returns {boolean}
 */
function isHoisted(ts, node) {
  return (
    ts.isCallExpression(node) &&
    ts.isPropertyAccessExpression(node.expression) &&
    ts.isIdentifier(node.expression.expression) &&
    node.expression.expression.text === 'vi' &&
    ['mock', 'doMock', 'hoisted', 'unmock'].includes(node.expression.name.text)
  );
}

/** The `how` word each splice writes down, read back out of the text the
 *  transform emitted: `__srt.handled(__sf,e,19,"catch_escaped")` and
 *  `__srt.catchCb(__sf,7,"catch_callback_opaque",(`. This is §1's ungated
 *  "share of catch clauses reading `catch_escaped`" — the escape rule's own
 *  verdict distribution over the lens, which no run has to happen to read. */
const HOW_WORD = [
  /__srt\.handled\((?:__sf|null),(?:[A-Za-z_$][\w$]*|undefined),\d+,"(\w+)"\)/g,
  /__srt\.catchCb\((?:__sf|null),\d+,"(\w+)",\(/g,
];

/**
 * @param {string} code the transform's output
 * @param {Record<string, number>} into tally to add to
 */
function tallyHow(code, into) {
  for (const rx of HOW_WORD) {
    for (const m of code.matchAll(rx)) into[m[1]] = (into[m[1]] ?? 0) + 1;
  }
}

/**
 * How many times each marker appears on each line of the transform's output.
 * @param {string} code
 * @returns {Map<string, number>} `"<line>\t<marker>"` -> count
 */
function markerCounts(code) {
  /** @type {Map<string, number>} */
  const counts = new Map();
  const lines = code.split('\n');
  for (let i = 0; i < lines.length; i += 1) {
    for (const marker of new Set(Object.values(MARKER))) {
      let from = 0;
      let n = 0;
      for (;;) {
        const at = lines[i].indexOf(marker, from);
        if (at < 0) break;
        n += 1;
        from = at + marker.length;
      }
      if (n > 0) counts.set(`${i + 1}\t${marker}`, n);
    }
  }
  return counts;
}

/**
 * Reconcile one file's sites against one file's transform output.
 *
 * Line by line and marker by marker, because two sites can share a line and a
 * file-wide total would let a missed one be paid for by a spare one somewhere
 * else — which is exactly the miss E2″ exists to catch.
 * @param {Site[]} sites
 * @param {string} rel root-relative file, for the named rows
 * @param {string} code the transform's output
 * @returns {{spliced: Record<string, number>, excluded: Miss[], missed: Miss[]}}
 */
function reconcile(sites, rel, code) {
  const counts = markerCounts(code);
  /** @type {Record<string, number>} */
  const spliced = {};
  /** @type {Miss[]} */
  const excluded = [];
  /** @type {Miss[]} */
  const missed = [];
  for (const site of sites) {
    if (site.spread) {
      excluded.push({
        file: rel, line: site.line, kind: site.kind,
        reason: 'a spread element in the argument list: the splice would '
          + 'produce source the consumer\'s own parser rejects, so the call is '
          + 'left to the program (spec §2.2, Task 2)',
      });
      continue;
    }
    const key = `${site.line}\t${site.marker}`;
    const left = counts.get(key) ?? 0;
    if (left > 0) {
      counts.set(key, left - 1);
      spliced[site.kind] = (spliced[site.kind] ?? 0) + 1;
      continue;
    }
    missed.push({
      file: rel, line: site.line, kind: site.kind,
      reason: site.hoisted
        ? 'inside a hoisted `vi.*` call, whose subtree the transform does not visit'
        : 'no marker on this line in the transform\'s output',
    });
  }
  return { spliced, excluded, missed };
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
  /** @type {Record<string, number>} */
  const spliced = {};
  /** @type {Miss[]} */
  const excludedSites = [];
  /** @type {Miss[]} */
  const unspliced = [];
  /** @type {Record<string, number>} */
  const byHow = {};

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
      /** @type {Site[]} */
      const sites = [];
      /** @param {number} pos */
      const lineAt = (pos) => sf.getLineAndCharacterOfPosition(pos).line + 1;
      /** @param {Node} node @param {boolean} hoisted */
      const visit = (node, hoisted) => {
        const inHoisted = hoisted || isHoisted(ts, node);
        if (ts.isCatchClause(node)) {
          catchClauses += 1;
          sites.push({
            kind: 'catch_clause', marker: MARKER.catch_clause,
            line: lineAt(node.block.getStart(sf)), spread: false, hoisted: inHoisted,
          });
        }
        if (
          ts.isTryStatement(node) &&
          node.finallyBlock &&
          finallyCompletes(ts, node.finallyBlock)
        ) {
          finallyCompleting += 1;
          sites.push({
            kind: 'finally_completing', marker: MARKER.finally_completing,
            line: lineAt(node.finallyBlock.getStart(sf)), spread: false,
            hoisted: inHoisted,
          });
        }
        const site = callbackSite(ts, node);
        if (site !== null && ts.isCallExpression(node)) {
          if (site === 'catch') callbackSites += 1;
          if (site === 'then') thenSites += 1;
          const arg = node.arguments[site === 'catch' ? 0 : 1];
          sites.push({
            kind: site === 'catch' ? 'callback_site' : 'then_site',
            marker: MARKER.callback_site,
            line: lineAt(arg.getStart(sf)),
            spread: node.arguments.some((a) => ts.isSpreadElement(a)),
            hoisted: inHoisted,
          });
        }
        ts.forEachChild(node, (child) => visit(child, inHoisted));
      };
      ts.forEachChild(sf, (child) => visit(child, false));

      // The numerator: the transform's own output over this same file.
      const out = transformSource(code, file, {
        root, ts, rtPath: 'sensorium-ts/rt',
      });
      if (out === null || out.code === null) {
        throw new Error(
          out === null
            ? 'transformSource returned null for a file classify() called eligible'
            : 'transformSource returned no code for a file that parsed clean',
        );
      }
      const rel = path.relative(root, file);
      tallyHow(out.code, byHow);
      const seen = reconcile(sites, rel, out.code);
      for (const [kind, n] of Object.entries(seen.spliced)) {
        spliced[kind] = (spliced[kind] ?? 0) + n;
      }
      excludedSites.push(...seen.excluded);
      unspliced.push(...seen.missed);
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

  const seenTotal = catchClauses + callbackSites + thenSites + finallyCompleting;
  const eligible = seenTotal - excludedSites.length;
  const splicedTotal = Object.values(spliced).reduce((a, b) => a + b, 0);
  return {
    files,
    catch_clauses: catchClauses,
    callback_sites: callbackSites,
    then_sites: thenSites,
    finally_completing: finallyCompleting,
    excluded,
    parse_error: parseError,
    failed,
    spliced,
    by_how: byHow,
    seen_total: seenTotal,
    eligible,
    spliced_total: splicedTotal,
    excluded_by_design: excludedSites,
    unspliced,
    ratio: eligible === 0 ? null : Number((splicedTotal / eligible).toFixed(4)),
    note:
      'The denominator is the AST walk over this root; the numerator is the ' +
      "transform's own output over the same files, matched marker by marker " +
      'and LINE by line (splices are newline-free, so the two line up). ' +
      '`eligible` is `seen_total` less `excluded_by_design`, which is the ' +
      '"after NAMED exclusions" of E2″\'s rule; every site the output carries ' +
      'no marker for is in `unspliced` by name, and is a MISS, not an ' +
      'exclusion. `ratio` is null only when nothing was eligible.',
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
