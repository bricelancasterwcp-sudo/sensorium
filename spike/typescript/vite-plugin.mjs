// THROWAWAY spike Vite plugin: runs the transform before esbuild sees the
// file (enforce: 'pre'), for files under <root>/src and <root>/sensorium-probes.
import path from 'node:path';
import fs from 'node:fs';
import { transformSource } from './transform.mjs';

export default function sensoriumSpike(opts = {}) {
  const root = opts.root || process.env.SENSORIUM_TS_ROOT;
  const relBase = opts.relBase || path.dirname(root); // paths as `frontend/src/…`
  const manifestDir = process.env.SENSORIUM_MANIFEST_DIR || '';
  const dirs = [path.join(root, 'src'), path.join(root, 'sensorium-probes')];
  return {
    name: 'sensorium-spike',
    enforce: 'pre',
    transform(code, id) {
      const file = id.split('?')[0];
      if (!dirs.some((d) => file.startsWith(d + path.sep))) return null;
      if (!/\.(ts|tsx|js|jsx|mjs)$/.test(file)) return null;
      const out = transformSource(code, file, { root, relBase });
      if (!out) return null;
      if (manifestDir) {
        fs.mkdirSync(manifestDir, { recursive: true });
        const name = out.manifest.file.replace(/[\/\\]/g, '__') + '.json';
        fs.writeFileSync(path.join(manifestDir, name), JSON.stringify(out.manifest));
      }
      return { code: out.code, map: out.map };
    },
  };
}
