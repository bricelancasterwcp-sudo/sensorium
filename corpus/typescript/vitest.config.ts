// The corpus project's config, and deliberately a PLAIN one.
//
// `sensorium ts run` writes its own wrapper config under
// `node_modules/.sensorium/`, `mergeConfig`s this file into it, and adds the
// plugin, the setup file and the runtime externalisation itself. `mergeConfig`
// CONCATENATES arrays, so a config that wired any of those here would give a
// driven run two plugins, two setup files and two runtimes -- one spool with
// two BOOT records, which `spool.read` refuses by name.
//
// So this file names the test files and the environment, and nothing else.
// That is also what a consumer's own config looks like, which is the point:
// the corpus records through the same path a consumer does.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['*/**/*.test.ts'],
  },
});
