// The probe project's own vitest config, in two readings.
//
// DIRECT (`SENSORIUM_PROBE_DIRECT=1`, which `npm run probe` sets): it wires the
// recorder itself, minus the driver — the plugin, the setup file, and the one
// declaration that keeps the runtime a single instance. That is the reading the
// probes were written under, before a driver existed, and it is what holds the
// library honest on its own.
//
// PLAIN (anything else): an ordinary vitest config that names the probe files
// and nothing more. That is the reading `sensorium ts run` needs, because the
// driver's wrapper `mergeConfig`s this file and then adds the same three
// things — and `mergeConfig` CONCATENATES arrays. A config that wired them
// unconditionally would give a driven run two copies of the plugin, two setup
// files and two runtimes: exactly the fault the external declaration below
// exists to prevent, reintroduced one level up.
//
// R16, the hazard that declaration holds: instrumented modules import the
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

/** Whether this config wires the recorder itself. The driver's wrapper never sets it. */
const direct = process.env.SENSORIUM_PROBE_DIRECT === '1';

export default defineConfig({
  plugins: direct ? [sensorium({ root: here, pkgDir, rtPath })] : [],
  test: {
    include: ['src/**/*.probe.test.{ts,tsx}'],
    environment: 'node',
    ...(direct
      ? { setupFiles: ['./setup.mjs'], server: { deps: { external: [rtExternal] } } }
      : {}),
  },
});
