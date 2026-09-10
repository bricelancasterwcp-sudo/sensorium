// The `node --test` loader hook. It is `register.mjs` that installs it; this is
// the module that runs on the loader thread.
//
// ONE job, for an ES MODULE under `SENSORIUM_TS_ROOT`: instrument the source the
// consumer wrote — TypeScript types and all, because the transform positions
// itself against the consumer's own AST — and hand it back under the format
// NODE reported for it. THIS HOOK ERASES NOTHING. `module-typescript` goes back
// as `module-typescript`, and Node strips it with the stripper plain
// `node --test` already uses; `module` goes back as `module` and is loaded as
// written. So `.ts` and `.mts` are stripped alike, and a construct Node's
// strip-only mode rejects (`enum`, `namespace`, parameter properties) fails
// IDENTICALLY plain and hooked, with Node's own error — which is R37 carried
// one step further: Node decides the format AND the erasure. The consumer's own
// TypeScript stays `require`d because the TRANSFORM parses against it; that was
// never the stripper's.
//
// `.tsx`/`.jsx` cannot reach this hook under `node --test` at all — Node's own
// loader throws `ERR_UNKNOWN_FILE_EXTENSION` from `nextLoad` before `load` sees
// the file — so such a file is outside NODE's scope here, not an exclusion of
// ours, and is not counted: the hook never decided anything about it. It is not
// made loadable either. A recorder that made an unloadable file load would be
// changing the program, which is the one thing this one promises not to do.
// (`classify()` still calls `.tsx`/`.jsx` eligible — that is the vitest
// plugin's scope, where they load.)
//
// A transform result whose `code` is null is 'ours, untouched, counted' (R10):
// the file did not parse, so it is loaded exactly as it was written and Node
// reports the syntax error itself, rather than this hook reporting a mangled
// one. A THROW from the transform is R10a — it refuses to splice blind — and
// reaches the consumer: a file this hook cannot vouch for is not quietly
// loaded unrecorded.
//
// The default load is called with the context it was given, never with
// `format: 'module'` forced into it: a `.js` in a package with no `"type"`
// field is CommonJS, and forcing it to ESM spliced an `import` header into a
// file full of `require` calls and broke a test suite that passes without
// this recorder — while `HONESTY.md` §7 promised such a file was "excluded
// and counted". A CommonJS result (`commonjs`, `commonjs-typescript`) passes
// through `excluded()` untouched and counted. Measured on node v24.16.0,
// `nextLoad` reports what Node itself would use and hands back the source AS
// WRITTEN: `commonjs` (with a null source — the CJS loader reads the file
// itself) for a detected-CommonJS `.js` and for `.cjs`; `commonjs-typescript`
// for a detected-CommonJS `.ts`/`.cts`, types intact; `module` for `.mjs`; and
// `module-typescript` for an ESM `.ts` or `.mts`, types intact. Nothing arrives
// here pre-stripped, which is the one thing the forced format was there to
// prevent.
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import * as tally from './tally.mjs';
import { classify, transformSource } from './transform.mjs';

/** The consumer's project directory: what is in scope to instrument. */
const ROOT = path.resolve(process.env.SENSORIUM_TS_ROOT ?? '');
/** This package's directory: where the runtime every edited file imports lives. */
const PKG = path.resolve(process.env.SENSORIUM_TS_PKG ?? '');
/** Where the counts and the per-file manifests go, or '' when nobody asked. */
const MANIFEST_DIR = tally.dir();

/** One specifier for the runtime, so one instance answers for the process (R16). */
const RT_PATH = pathToFileURL(path.join(PKG, 'src', 'rt.mjs')).href;

const require = createRequire(path.join(ROOT, 'package.json'));
/** The consumer's own TypeScript — the compiler its build already trusts. */
const ts = /** @type {typeof import('typescript')} */ (require('typescript'));

/** The formats this transform must not touch: its header is an `import`. */
const COMMONJS_FORMATS = new Set(['commonjs', 'commonjs-typescript']);

/**
 * Count one file this hook declined, and write the counts out.
 *
 * Written after every decision rather than on exit: an `exit` listener
 * registered from a loader hook never fires (measured — see `tally.mjs`), so
 * an exit-time write from this thread would write nothing at all.
 * @template T
 * @param {string} file absolute path
 * @param {T} loaded the default load's own result, handed straight back
 * @returns {T}
 */
function excluded(file, loaded) {
  tally.exclude(file, 'commonjs');
  if (MANIFEST_DIR) tally.write(MANIFEST_DIR, tally.containerTally());
  return loaded;
}

/**
 * @param {string} url
 * @param {object} context
 * @param {(url: string, context: object) => Promise<{format?: string, source?: string|ArrayBuffer|Uint8Array}>} nextLoad
 * @returns {Promise<{format?: string, source?: string|ArrayBuffer|Uint8Array, shortCircuit?: boolean}>}
 */
export async function load(url, context, nextLoad) {
  if (!url.startsWith('file:')) return nextLoad(url, context);
  const file = fileURLToPath(url);
  const kind = classify(file, ROOT);
  if (kind === 'skip') return nextLoad(url, context);
  // `.cjs` and `.cts` are CommonJS by their extension; Node names the rest.
  if (kind === 'commonjs') return excluded(file, await nextLoad(url, context));
  const loaded = await nextLoad(url, context);
  if (COMMONJS_FORMATS.has(loaded.format ?? '')) return excluded(file, loaded);

  const src = loaded.source;
  const code = typeof src === 'string' ? src : Buffer.from(/** @type {any} */ (src)).toString('utf8');
  // A throw from here is the transform refusing to splice blind (R10a) and it
  // must reach the consumer: a file this hook cannot vouch for is not quietly
  // loaded unrecorded.
  const out = transformSource(code, file, { root: ROOT, ts, rtPath: RT_PATH });
  if (out === null) return loaded;
  tally.record(file, out, MANIFEST_DIR);
  if (MANIFEST_DIR) tally.write(MANIFEST_DIR, tally.containerTally());
  // Node's own format goes back with the edited source: `module-typescript`
  // is stripped by the stripper plain `node --test` already uses, `module`
  // is loaded as written. This hook erases nothing.
  const edited = out.code !== null ? out.code : code;
  return { format: loaded.format, source: edited, shortCircuit: true };
}
