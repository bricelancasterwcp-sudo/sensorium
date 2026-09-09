// `node --import <pkg>/src/register.mjs --test <file.ts>`.
//
// Nothing here transforms anything: it installs `hook.mjs` on Node's loader
// thread and checks, once, that the two things the hook cannot invent are set.
// A missing variable refuses by name here rather than letting the run finish
// green with an empty spool — a recorder that records nothing must say so.
import { register } from 'node:module';

for (const name of ['SENSORIUM_TS_ROOT', 'SENSORIUM_TS_PKG']) {
  if (!process.env[name]) {
    throw new Error(`sensorium-ts: ${name} is not set; refusing to register a hook with no scope`);
  }
}

register(new URL('./hook.mjs', import.meta.url));
