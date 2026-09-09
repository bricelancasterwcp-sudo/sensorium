// The Vite plugin: the harness wiring for vitest. It runs `enforce: 'pre'`, so
// it sees the consumer's own TypeScript before esbuild has erased the types the
// transform positions itself against, and it hands Vite back the magic-string
// `hires` map so vitest reports the ORIGINAL line and column of a failure.
//
// Two resolutions, and neither of them uses this file's own location:
//   * `typescript` comes from the ROOT — the consumer's compiler, the one whose
//     AST the consumer's build already trusts. A recorder that parsed with its
//     own copy would be reading a different language from the one being run.
//   * `magic-string` comes from the PACKAGE — the recorder's own dependency.
//     `transform.mjs` bare-imports it, so the resolution here is a check, not a
//     handoff: it turns a cryptic ERR_MODULE_NOT_FOUND raised deep inside a
//     transform into a named refusal at config time.
//
// The tally is per PROCESS, not per file: vitest transforms in its main process
// and ships the result to the workers, so one tally covers the invocation. It is
// written on exit, never during, because a count that is still moving is not a
// count.
import fs from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

import { classify, transformSource } from './transform.mjs';

/** @typedef {{files_transformed: number, excluded: Record<string, number>}} Tally */

/** @type {Tally} */
const tally = { files_transformed: 0, excluded: {} };

/**
 * The files already counted. Vite keeps one module graph per transform mode, so
 * a module a `node` file and a `jsdom` file both import is transformed TWICE
 * (measured: `setup.mjs` under a mixed suite). A count of files that counted
 * calls would over-report itself, and the converter would publish the inflation.
 * @type {Set<string>}
 */
const counted = new Set();

let tallyInstalled = false;

/**
 * Fold one file's exclusion counts into the invocation's.
 * @param {Record<string, number>|undefined} excluded
 * @returns {void}
 */
function countExcluded(excluded) {
  for (const [reason, n] of Object.entries(excluded ?? {})) {
    tally.excluded[reason] = (tally.excluded[reason] ?? 0) + n;
  }
}

/**
 * @param {string} reason
 * @returns {void}
 */
function countOne(reason) {
  tally.excluded[reason] = (tally.excluded[reason] ?? 0) + 1;
}

/**
 * Write `_tally.json` once, when the process that did the transforming ends.
 * A tally that cannot be written says so on stderr: the run is not the tally's
 * to fail, but a silently missing count would let the converter under-report
 * without anyone knowing (design §7).
 * @param {string} dir
 * @returns {void}
 */
function installTally(dir) {
  if (tallyInstalled) return;
  tallyInstalled = true;
  process.on('exit', () => {
    try {
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, '_tally.json'), JSON.stringify(tally));
    } catch (err) {
      process.emitWarning(`sensorium: could not write the transform tally to ${dir}: ${err}`);
    }
  });
}

/**
 * The per-file manifest, named by its root-relative path with the separators
 * flattened so one directory holds them all.
 * @param {string} dir
 * @param {import('./transform.mjs').Manifest} manifest
 * @returns {void}
 */
function writeManifest(dir, manifest) {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, `${manifest.rel.split('/').join('__')}.json`),
    JSON.stringify(manifest),
  );
}

/**
 * @param {string} root the invocation root: the consumer's project directory
 * @param {string} pkgDir this package's directory
 * @returns {typeof import('typescript')} the consumer's own TypeScript
 */
function resolveTools(root, pkgDir) {
  const fromRoot = createRequire(path.join(root, 'package.json'));
  const fromPkg = createRequire(path.join(pkgDir, 'package.json'));
  fromPkg.resolve('magic-string');
  return fromRoot('typescript');
}

/**
 * @param {{root: string, pkgDir: string, rtPath: string}} opts
 *   `root` the consumer's project directory, `pkgDir` this package's directory,
 *   `rtPath` the specifier every instrumented module imports the runtime by —
 *   ONE specifier per invocation, or the runtime is two runtimes (R16).
 * @returns {{name: string, enforce: 'pre', transform: (code: string, id: string) =>
 *   {code: string, map: unknown}|null}} a Vite plugin
 */
export function sensorium(opts) {
  const root = path.resolve(opts.root);
  const pkgDir = path.resolve(opts.pkgDir);
  const rtPath = opts.rtPath;
  const ts = resolveTools(root, pkgDir);
  const manifestDir = process.env.SENSORIUM_MANIFEST_DIR ?? '';
  if (manifestDir) installTally(manifestDir);

  return {
    name: 'sensorium',
    enforce: /** @type {'pre'} */ ('pre'),

    /**
     * @param {string} code
     * @param {string} id
     * @returns {{code: string, map: unknown}|null}
     */
    transform(code, id) {
      // A virtual module has no file behind it and no line numbers we could
      // vouch for, whatever its id looks like after the query is stripped.
      if (id.startsWith('\0')) return null;
      const file = id.split('?')[0];
      const kind = classify(file, root);
      if (kind === 'skip') return null;
      // CommonJS is ours and countable, but this transform emits ESM and would
      // change what the module IS; it is excluded by name, never by silence.
      const first = !counted.has(file);
      counted.add(file);
      if (kind === 'commonjs') {
        if (first) countOne('commonjs');
        return null;
      }
      // A throw here is `transform.mjs` refusing to splice blind (R10a). It
      // propagates: a recorder that cannot vouch for its own edits must fail
      // the run by name rather than record a file it did not understand.
      const out = transformSource(code, file, { root, ts, rtPath });
      if (!out) return null;
      if (first) countExcluded(out.manifest.excluded);
      if (manifestDir) writeManifest(manifestDir, out.manifest);
      // Ours, untouched, counted (R10): the file did not parse, its manifest
      // says so, and Vite gets the source back exactly as it arrived.
      if (out.code === null) return null;
      if (first) tally.files_transformed += 1;
      return { code: out.code, map: out.map };
    },
  };
}

export default sensorium;
