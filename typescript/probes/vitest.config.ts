// The probe project's own vitest config. It wires the recorder exactly as the
// driver will, minus the driver: the plugin, the setup file, and the one
// declaration that keeps the runtime a single instance.
//
// R16, the hazard this config exists to hold: instrumented modules import the
// runtime by absolute path through Vite's module runner, while a setup file can
// be externalised and import it natively. Two loaders, two module records, two
// runtimes — two BOOT lines in one spool, two id counters, and a trace that
// says a thing happened twice. Declaring the runtime external for EVERY
// importer settles it: Node resolves it once and caches it by path.
//
// The declaration must be a RegExp. `server.deps.external` matches a STRING
// entry only as `<moduleDirectory>/<entry>` — vitest's `matchPattern` joins it
// onto `/node_modules/` — so an absolute path given as a string silently
// matches nothing at all.
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

import { sensorium } from '../src/vite.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgDir = path.resolve(here, '..');
const rtPath = path.join(pkgDir, 'src', 'rt.mjs');
const rtExternal = new RegExp(`^${rtPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`);

export default defineConfig({
  plugins: [sensorium({ root: here, pkgDir, rtPath })],
  test: {
    include: ['src/**/*.probe.test.{ts,tsx}'],
    environment: 'node',
    setupFiles: ['./setup.mjs'],
    server: { deps: { external: [rtExternal] } },
  },
});
