// The transform golden diff: what this tree's `transform.mjs` emits, against
// what another checkout's emits, over the same sources with the same focus.
//
//   node acceptance/transform_diff.mjs <base checkout> <root> <target...> \
//        [--focus <spec>]...
//
// `<base checkout>` is a directory holding a whole repository (a `git
// worktree` of the commit being compared against); its
// `typescript/src/transform.mjs` is the BASE and this file's sibling
// `../src/transform.mjs` is the HEAD. `<root>` is the package root the
// transform resolves `rel` against, and each `<target>` is a FILE or a
// DIRECTORY — a directory is walked for `.ts`, `.mts`, `.mjs` and `.js`,
// skipping `node_modules`, `.git` and declaration files.
//
// Two questions, and the second is why this is a script and not a `diff`:
//
//   1. DID ANY BYTE MOVE? Both transforms run over the same bytes and the two
//      outputs are written to a scratch directory and handed to the system
//      `diff -u`. Its text is the evidence; `changed` is whether it is empty.
//   2. WHOSE WRAPPER MOVED? The transform is line-preserving (`census.mjs`
//      treats a changed line count as a failure), so output line N is source
//      line N, and a changed line can be attributed by position: run the
//      transform's own `sitesOf` over the source, and the function a changed
//      line belongs to is the one whose start line is the GREATEST that is
//      still ≤ it. Lines above the first site are attributed to
//      `<file header>` — the import line the transform prepends.
//
// That attribution is deliberately the simple rule and not a scope analysis:
// it cannot tell a nested arrow's wrapper from its container's when the two
// share a line, and it says so here rather than in a reader's assumption. For
// this slice's question — "did exactly the functions the census named change,
// and no other byte" — the byte answer is (1) and (2) is how the report names
// them.
//
// Prints one JSON object on stdout and nothing else. Exit 0 when every file
// was compared, 2 on a usage error, 3 when a transform threw.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';

const EXT = new Set(['.ts', '.mts', '.mjs', '.js']);
const SKIP_DIR = new Set(['node_modules', '.git', 'dist', 'build']);

/** @param {string} dir @returns {string[]} absolute paths, sorted */
function walk(dir) {
  /** @type {string[]} */
  const found = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
    a.name < b.name ? -1 : 1,
  )) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIR.has(entry.name)) found.push(...walk(full));
    } else if (entry.isFile() && EXT.has(path.extname(entry.name)) && !entry.name.endsWith('.d.ts')) {
      found.push(full);
    }
  }
  return found;
}

/**
 * The consumer's own TypeScript where the root has one, this repository's
 * otherwise — the same rule `census.mjs` uses, with a fallback because a
 * corpus case directory carries no `package.json`.
 * @param {string} root
 */
function typescriptFor(root) {
  for (const from of [path.join(root, 'package.json'), path.join(HERE, '..', 'package.json')]) {
    try {
      return createRequire(from)('typescript');
    } catch {
      /* try the next */
    }
  }
  throw new Error('no `typescript` resolvable from the root or from typescript/');
}

const HERE = path.dirname(new URL(import.meta.url).pathname);

/** The lines at which the two texts differ, 1-based, on the head side. */
function changedLines(a, b) {
  const left = a.split('\n');
  const right = b.split('\n');
  const out = [];
  for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
    if (left[i] !== right[i]) out.push(i + 1);
  }
  return out;
}

/** The site a line belongs to: greatest start line still ≤ it. */
function ownerOf(sites, line) {
  let owner = null;
  for (const site of sites) {
    if (site.line <= line && (owner === null || site.line > owner.line)) owner = site;
  }
  return owner === null ? '<file header>' : owner.qualname;
}

function unified(scratch, rel, before, after) {
  const a = path.join(scratch, 'base');
  const b = path.join(scratch, 'head');
  fs.writeFileSync(a, before);
  fs.writeFileSync(b, after);
  try {
    execFileSync('diff', ['-u', '--label', `base/${rel}`, '--label', `head/${rel}`, a, b], {
      encoding: 'utf8',
    });
    return '';
  } catch (err) {
    if (typeof err.stdout === 'string') return err.stdout;
    throw err;
  }
}

function main(argv) {
  const focus = [];
  const positional = [];
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--focus') {
      focus.push(argv[i + 1]);
      i += 1;
    } else positional.push(argv[i]);
  }
  const [base, root, ...targets] = positional;
  if (!base || !root || targets.length === 0) {
    process.stderr.write(
      'usage: transform_diff.mjs <base checkout> <root> <target...> [--focus <spec>]...\n',
    );
    return 2;
  }
  // The base checkout is a bare `git worktree`: it has the sources and no
  // `node_modules`, and `transform.mjs` imports `magic-string`. Rather than
  // install into a throwaway tree, this links THIS tree's — the two commits
  // share the dependency, and the link is reported so a reader knows the base
  // transform ran against the head's `magic-string` and not its own.
  const baseModules = path.join(path.resolve(base), 'typescript', 'node_modules');
  let linked = null;
  if (!fs.existsSync(baseModules)) {
    fs.symlinkSync(path.join(HERE, '..', 'node_modules'), baseModules, 'dir');
    linked = `${baseModules} -> ${path.join(HERE, '..', 'node_modules')}`;
  }
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'transform-diff-'));
  const ts = typescriptFor(path.resolve(root));
  const files = [];
  for (const target of targets) {
    const full = path.resolve(target);
    files.push(...(fs.statSync(full).isDirectory() ? walk(full) : [full]));
  }
  return Promise.all([
    import(path.join(path.resolve(base), 'typescript', 'src', 'transform.mjs')),
    import(path.join(HERE, '..', 'src', 'transform.mjs')),
  ]).then(([baseMod, headMod]) => {
    const rows = [];
    for (const file of files) {
      const code = fs.readFileSync(file, 'utf8');
      const opts = { root: path.resolve(root), ts, rtPath: 'sensorium-ts/rt', focus };
      let before;
      let after;
      try {
        before = baseMod.transformSource(code, file, opts);
        after = headMod.transformSource(code, file, opts);
      } catch (err) {
        rows.push({ file, changed: null, error: String(err && err.message ? err.message : err) });
        continue;
      }
      if (before === null && after === null) continue; // not this recorder's
      const rel = (after ?? before).manifest.rel;
      const left = before?.code ?? '';
      const right = after?.code ?? '';
      const lines = changedLines(left, right);
      const sites = headMod.sitesOf(code, file, opts)?.sites ?? [];
      rows.push({
        file: rel,
        changed: lines.length > 0,
        functions: [...new Set(lines.map((n) => ownerOf(sites, n)))].sort(),
        changed_lines: lines,
        diff: lines.length > 0 ? unified(scratch, rel, left, right) : '',
        base_bytes: Buffer.byteLength(left),
        head_bytes: Buffer.byteLength(right),
      });
    }
    fs.rmSync(scratch, { recursive: true, force: true });
    const failed = rows.filter((r) => r.changed === null);
    process.stdout.write(
      `${JSON.stringify(
        {
          base,
          base_node_modules_linked: linked,
          root: path.resolve(root),
          focus,
          files_compared: rows.length,
          changed: rows.filter((r) => r.changed === true).length,
          failed: failed.map((r) => ({ file: r.file, error: r.error })),
          files: rows,
        },
        null,
        2,
      )}\n`,
    );
    return failed.length > 0 ? 3 : 0;
  });
}

Promise.resolve(main(process.argv.slice(2))).then((code) => {
  process.exitCode = code;
});
