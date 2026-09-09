// `node --import /abs/path/register.mjs --test <file.ts>`
import { register } from 'node:module';
register(new URL('./hook.mjs', import.meta.url));
