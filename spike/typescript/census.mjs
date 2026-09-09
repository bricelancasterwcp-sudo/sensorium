// THROWAWAY E2 census: run the transform over every census file (frontend/src
// minus tests, .d.ts, test-setup.ts) and total instrumented vs excluded, plus
// files the transform threw on. Prints JSON.
import fs from 'node:fs';
import path from 'node:path';
import { transformSource } from './transform.mjs';

const root = process.env.SENSORIUM_TS_ROOT;
const relBase = path.dirname(root);
const files = [];
(function walk(d) {
  for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, ent.name);
    if (ent.isDirectory()) walk(p);
    else if (/\.(ts|tsx)$/.test(ent.name) && !/\.test\.|\.spec\.|\.d\.ts$/.test(ent.name) && ent.name !== 'test-setup.ts') files.push(p);
  }
})(path.join(root, 'src'));

const byKind = {};
const excluded = {};
const failed = [];
let instrumented = 0;
let inBytes = 0;
let outBytes = 0;
for (const f of files) {
  const code = fs.readFileSync(f, 'utf8');
  try {
    const out = transformSource(code, f, { root, relBase });
    if (!out) { failed.push({ file: f, why: 'transform returned null' }); continue; }
    inBytes += code.length;
    outBytes += out.code.length;
    for (const it of out.manifest.instrumented) { byKind[it.kind] = (byKind[it.kind] || 0) + 1; instrumented += 1; }
    for (const [k, n] of Object.entries(out.manifest.excluded)) excluded[k] = (excluded[k] || 0) + n;
  } catch (err) {
    failed.push({ file: path.relative(relBase, f), why: String(err && err.message || err).slice(0, 200) });
  }
}
const excludedTotal = Object.values(excluded).reduce((a, b) => a + b, 0);
console.log(JSON.stringify({
  files: files.length, failed_files: failed.length, failed,
  instrumented, excluded, eligible: instrumented + excludedTotal,
  ratio: instrumented / (instrumented + excludedTotal), by_kind: byKind,
  bloat: outBytes / inBytes,
}, null, 1));
