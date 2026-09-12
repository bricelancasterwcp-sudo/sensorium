// The invocation's transform counts, and the per-file manifests beside them.
//
// One module because BOTH harnesses count. The Vite plugin transforms in
// vitest's main process; the loader hook transforms on each `node --test`
// child's hook thread. Held in the plugin, as it was, the counts existed for
// vitest runs and for nothing else, and every `node --test` trace carried no
// coverage number at all — while `HONESTY.md` §7 said a CommonJS file "is
// excluded and counted".
//
// TWO WRITERS, because the two threads end differently, and both facts below
// were measured on node v24.16.0 rather than assumed:
//
//   * the plugin installs a `process.on('exit')` writer. vitest transforms in
//     one process for the whole invocation, so the count is still moving until
//     that process ends, and a count that is still moving is not a count. The
//     file is `_tally.json`: one invocation, one number, every container's;
//   * the hook writes after every file it decides. An `exit` listener
//     registered from a module-customization hook NEVER FIRES — the hooks
//     thread is torn down with the process and runs no exit handlers — so an
//     exit-time write from there would write nothing at all. The file is named
//     by the CHILD's pid, because `node --test` runs one child process per test
//     file (measured: five files, five pids) and one shared name would be five
//     writers racing over one number. The count on such a trace is therefore
//     that container's own transform, which is the only one it had.
//
// A tally that cannot be written says so on stderr: the run is not the tally's
// to fail, but a silently missing count would let the converter under-report
// without anyone knowing (design §7).
import fs from 'node:fs';
import path from 'node:path';

/**
 * @typedef {{files_transformed: number, functions_focused: number,
 *   excluded: Record<string, number>}} Tally
 */

/**
 * `functions_focused` is how many function-likes the invocation's focus
 * actually selected -- zero on every unfocused run, which is what says a trace
 * with no LINE rows had nothing to record rather than a recorder that missed.
 * @type {Tally}
 */
const tally = { files_transformed: 0, functions_focused: 0, excluded: {} };

/**
 * The files already counted. Vite keeps one module graph per transform mode, so
 * a module a `node` file and a `jsdom` file both import is transformed TWICE
 * (measured: `setup.mjs` under a mixed suite). A count of files that counted
 * calls would over-report itself, and the converter would publish the inflation.
 * @type {Set<string>}
 */
const counted = new Set();

/** The invocation-wide name, read by the converter for every container. */
export const INVOCATION_TALLY = '_tally.json';

/** One container's own, named by its pid: `_tally-<pid>.json`. */
export const containerTally = () => `_tally-${process.pid}.json`;

/** @returns {string} the directory the driver named, or '' when it named none */
export function dir() {
  return process.env.SENSORIUM_MANIFEST_DIR ?? '';
}

/**
 * @param {string} file absolute path
 * @returns {boolean} whether this file has not been counted before
 */
function first(file) {
  if (counted.has(file)) return false;
  counted.add(file);
  return true;
}

/**
 * Count one file the transform declined without ever parsing it — the CommonJS
 * verdict, which no per-file manifest can carry because there is no manifest.
 * @param {string} file absolute path
 * @param {string} reason
 * @returns {void}
 */
export function exclude(file, reason) {
  if (!first(file)) return;
  tally.excluded[reason] = (tally.excluded[reason] ?? 0) + 1;
}

/**
 * Fold one transform result into the invocation's counts and write the file's
 * own manifest. The manifest is written on every call and the counts move only
 * on the first: the manifest is the same bytes either way, the count is not.
 * @param {string} file absolute path
 * @param {{code: string|null, manifest: import('./transform.mjs').Manifest}} out
 * @param {string} dirname the manifest directory, or '' for none
 * @returns {void}
 */
export function record(file, out, dirname) {
  if (dirname) writeManifest(dirname, out.manifest);
  if (!first(file)) return;
  for (const [reason, n] of Object.entries(out.manifest.excluded ?? {})) {
    tally.excluded[reason] = (tally.excluded[reason] ?? 0) + n;
  }
  // `code: null` is 'ours, untouched, counted' (R10): the file did not parse,
  // its manifest says so, and it was not edited.
  if (out.code !== null) tally.files_transformed += 1;
  tally.functions_focused += out.manifest.focused.length;
}

/**
 * The per-file manifest, named by its root-relative path with the separators
 * flattened so one directory holds them all.
 * @param {string} dirname
 * @param {import('./transform.mjs').Manifest} manifest
 * @returns {void}
 */
function writeManifest(dirname, manifest) {
  fs.mkdirSync(dirname, { recursive: true });
  fs.writeFileSync(
    path.join(dirname, `${manifest.rel.split('/').join('__')}.json`),
    JSON.stringify(manifest),
  );
}

/**
 * Write the counts as they stand.
 * @param {string} dirname
 * @param {string} name
 * @returns {void}
 */
export function write(dirname, name) {
  try {
    fs.mkdirSync(dirname, { recursive: true });
    fs.writeFileSync(path.join(dirname, name), JSON.stringify(tally));
  } catch (err) {
    process.emitWarning(`sensorium: could not write the transform tally to ${dirname}: ${err}`);
  }
}

let installed = false;

/**
 * Write `_tally.json` once, when the process that did the transforming ends.
 * @param {string} dirname
 * @returns {void}
 */
export function installExitWriter(dirname) {
  if (installed) return;
  installed = true;
  process.on('exit', () => write(dirname, INVOCATION_TALLY));
}
