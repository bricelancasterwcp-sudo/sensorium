// The `node --test` loader hook. It is `register.mjs` that installs it; this is
// the module that runs on the loader thread.
//
// Two jobs, in this order, for a file under `SENSORIUM_TS_ROOT`:
//   1. instrument the source the consumer wrote — TypeScript types and all,
//      because the transform positions itself against the consumer's own AST;
//   2. for `.ts`/`.tsx` only, erase the types with the ROOT's own TypeScript.
// `.js`/`.mjs` under the root are instrumented and handed back unstripped:
// there is nothing to erase and `transpileModule` would only be a second
// parser's opinion of a file Node can already read.
//
// The default load is asked for `format: 'module'` explicitly. Node 24 strips
// types itself when it is left to choose, and this hook must see the source as
// the consumer wrote it — a tree with the types already whitespaced out is not
// the tree `transformSource` was designed against.
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { classify, transformSource } from './transform.mjs';

/** The consumer's project directory: what is in scope to instrument. */
const ROOT = path.resolve(process.env.SENSORIUM_TS_ROOT ?? '');
/** This package's directory: where the runtime every edited file imports lives. */
const PKG = path.resolve(process.env.SENSORIUM_TS_PKG ?? '');

/** One specifier for the runtime, so one instance answers for the process (R16). */
const RT_PATH = pathToFileURL(path.join(PKG, 'src', 'rt.mjs')).href;

const require = createRequire(path.join(ROOT, 'package.json'));
/** The consumer's own TypeScript — the compiler its build already trusts. */
const ts = /** @type {typeof import('typescript')} */ (require('typescript'));

/** The extensions whose types this hook erases; everything else it leaves alone. */
const STRIP = new Set(['.ts', '.tsx']);

/**
 * @param {string} code instrumented source
 * @param {string} file absolute path, which decides the parse mode
 * @returns {string} the same program with its types erased
 */
function strip(code, file) {
  return ts.transpileModule(code, {
    fileName: file,
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      sourceMap: false,
    },
  }).outputText;
}

/**
 * @param {string} url
 * @param {object} context
 * @param {(url: string, context: object) => Promise<{source?: string|ArrayBuffer|Uint8Array}>} nextLoad
 * @returns {Promise<{format?: string, source?: string|ArrayBuffer|Uint8Array, shortCircuit?: boolean}>}
 */
export async function load(url, context, nextLoad) {
  if (!url.startsWith('file:')) return nextLoad(url, context);
  const file = fileURLToPath(url);
  if (classify(file, ROOT) !== 'transform') return nextLoad(url, context);

  const loaded = await nextLoad(url, { ...context, format: 'module' });
  const src = loaded.source;
  const code = typeof src === 'string' ? src : Buffer.from(/** @type {any} */ (src)).toString('utf8');
  // A throw from here is the transform refusing to splice blind (R10a) and it
  // must reach the consumer: a file this hook cannot vouch for is not quietly
  // loaded unrecorded.
  const out = transformSource(code, file, { root: ROOT, ts, rtPath: RT_PATH });
  // `code: null` is 'ours, untouched, counted' (R10) — the file did not parse,
  // so it is loaded exactly as it was written, and Node reports the syntax
  // error itself rather than this hook reporting a mangled one.
  const edited = out && out.code !== null ? out.code : code;
  const source = STRIP.has(path.extname(file)) ? strip(edited, file) : edited;
  return { format: 'module', source, shortCircuit: true };
}
