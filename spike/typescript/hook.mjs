// THROWAWAY spike loader hook for `node --import <register.mjs> --test`.
// Transforms .ts/.tsx under the configured root, then strips types with
// the frontend's own TypeScript (ts.transpileModule), returning ESM.
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { transformSource } from './transform.mjs';

const TS_ROOT = process.env.SENSORIUM_TS_ROOT;
const require = createRequire(path.join(TS_ROOT, 'package.json'));
const ts = require('typescript');
const dirs = [path.join(TS_ROOT, 'src'), path.join(TS_ROOT, 'sensorium-probes')];

export async function load(url, context, nextLoad) {
  if (!url.startsWith('file:')) return nextLoad(url, context);
  const file = fileURLToPath(url);
  if (!dirs.some((d) => file.startsWith(d + path.sep)) || !/\.(ts|tsx)$/.test(file)) return nextLoad(url, context);
  const src = (await nextLoad(url, { ...context, format: 'module' })).source;
  const code = typeof src === 'string' ? src : Buffer.from(src).toString('utf8');
  const out = transformSource(code, file, { root: TS_ROOT, relBase: path.dirname(TS_ROOT) });
  const edited = out ? out.code : code;
  const js = ts.transpileModule(edited, {
    fileName: file,
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, sourceMap: false },
  }).outputText;
  return { format: 'module', source: js, shortCircuit: true };
}
