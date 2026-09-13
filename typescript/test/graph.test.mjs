// The import graph through `src/` is acyclic, and this is the test that says so.
//
// It exists because the recorder had a cycle for months and the comment on it
// said the cycle was fine: `transform.mjs` imported `pairsOf`/`spliceFocused`
// out of `probe.mjs`, `probe.mjs` imported `lineOf`/`terminatorFor` back out of
// `transform.mjs`, and both sides were right that hoisted function declarations
// make it SAFE — the binding exists before either module's body runs, and
// neither is called until a transform is under way. Safe is not the property
// worth having. A reader tracing where a probe's positions come from was sent
// back into the file that had just called the probe, and the next module to
// join the cycle would have been added with the same reasoning and one more
// comment. S5 rung 4's debts cut `positions.mjs` out from between them; this
// test is what stops the edge coming back.
//
// Static imports only, which is the whole runtime graph: nothing under `src/`
// uses a dynamic `import()`, and a JSDoc `import('./x.mjs').Type` is a TYPE
// reference that emits no edge at all — `tasks.mjs` and `probe.mjs` both name
// `transform.mjs` that way and are not its dependents.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const SRC = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src');

/**
 * One static import or re-export of a RELATIVE specifier, at the start of a
 * line. Both forms count: `import x from './a.mjs'` and the side-effect
 * `import './a.mjs'`, which is the shape a cycle is most often reintroduced in.
 * The clause may span lines (`import {\n  a,\n} from './a.mjs'`), so the gap
 * before `from` is matched across newlines — but never across a `;` or a quote,
 * which is what keeps it from running out of one statement into the next.
 */
const EDGE = /^(?:import|export)\s(?:[^;'"]*?\bfrom\s*)?['"](\.[^'"]+)['"]/gm;

/**
 * @param {string} file a `*.mjs` basename under `src/`
 * @returns {string[]} the basenames it imports, in source order, with repeats
 */
function edgesOf(file) {
  const src = fs.readFileSync(path.join(SRC, file), 'utf8');
  return [...src.matchAll(EDGE)].map((m) => path.basename(m[1]));
}

/** @returns {Map<string, string[]>} every `src/*.mjs`, each with its edges */
function graph() {
  const files = fs.readdirSync(SRC).filter((f) => f.endsWith('.mjs')).sort();
  assert.ok(files.length >= 10, `src/ holds the recorder's modules: ${files}`);
  return new Map(files.map((f) => [f, edgesOf(f)]));
}

/**
 * Depth-first search with a three-colour map. Grey is "on the current path", so
 * an edge into a grey node is a back edge and the cycle is the tail of the path
 * from that node onward.
 * @param {Map<string, string[]>} g
 * @returns {string[]|null} the cycle as a path, `null` when there is none
 */
function findCycle(g) {
  /** @type {Map<string, 'grey'|'black'>} */
  const colour = new Map();
  /** @type {string[]} */
  const path_ = [];
  /** @param {string} node @returns {string[]|null} */
  function visit(node) {
    if (colour.get(node) === 'black') return null;
    if (colour.get(node) === 'grey') return [...path_.slice(path_.indexOf(node)), node];
    colour.set(node, 'grey');
    path_.push(node);
    for (const next of g.get(node) ?? []) {
      const cycle = visit(next);
      if (cycle) return cycle;
    }
    path_.pop();
    colour.set(node, 'black');
    return null;
  }
  for (const node of g.keys()) {
    const cycle = visit(node);
    if (cycle) return cycle;
  }
  return null;
}

test('the import graph through src/ is acyclic', () => {
  const cycle = findCycle(graph());
  assert.equal(cycle, null, cycle ? `import cycle: ${cycle.join(' → ')}` : '');
});

test('every relative edge names a file that is really there', () => {
  // Without this, a typo'd specifier would silently drop an edge and the
  // acyclicity above would be asserted over a graph missing the one that mattered.
  const g = graph();
  for (const [file, edges] of g) {
    for (const edge of edges) {
      assert.ok(g.has(edge), `${file} imports ${edge}, which is not a src/*.mjs`);
    }
  }
});

test('the edge reader sees a multi-line import clause and a side-effect import', () => {
  // The two shapes a line-at-a-time reader misses. `probe.mjs`'s real import of
  // `bindings.mjs` is written across five lines, so a regex that stopped at the
  // newline would report `probe.mjs` as having no dependency on it at all.
  assert.ok(edgesOf('probe.mjs').includes('bindings.mjs'),
    'probe.mjs imports bindings.mjs across several lines');
  const seen = [...`import {\n  a,\n} from './a.mjs';\nimport './b.mjs';\nimport c from 'node:fs';\n`
    .matchAll(EDGE)].map((m) => m[1]);
  assert.deepEqual(seen, ['./a.mjs', './b.mjs']);
});

test('probe.mjs does not import transform.mjs at runtime', () => {
  // The specific edge `positions.mjs` exists to remove, named so a reviewer
  // reading a reintroduction sees which one it was.
  assert.ok(!edgesOf('probe.mjs').includes('transform.mjs'),
    'positions.mjs owns lineOf and terminatorFor; probe.mjs reads them from there');
});
