# `probes/` — the recorder recording itself

A self-contained vitest project whose only job is to be recorded. Its expected
rows were pinned by the S5 mechanics spike (`docs/superpowers/spikes/2026-09-08-typescript-mechanics-spike.md`,
§1.1–§1.3) **before** this recorder existed, and `check.mjs` holds the spools to
them.

The same project is recorded two ways, and `check.mjs` asserts the same rows
either way.

**Directly**, with no driver at all: `vitest.config.ts` wires the recorder
itself — the Vite plugin from `../src/vite.mjs`, `setup.mjs` (the driver's
template with the in-tree import), and the R16 external declaration — but
**only** when `SENSORIUM_PROBE_DIRECT=1`, which the `probe` script sets. That
gate is not decoration: `sensorium ts run` writes a wrapper config that
`mergeConfig`s this one and then adds the same three things, and `mergeConfig`
concatenates arrays, so a config that wired them unconditionally would give a
driven run two plugins, two setup files and two runtimes.

**Through the driver**, which is how a consumer records anything:

```sh
cd typescript/probes
SENSORIUM_DIR=/path/to/a/store sensorium ts run -- npx vitest run
node check.mjs vitest /path/to/a/store/spool/<invocation> \
                      /path/to/a/store/spool/<invocation>/manifests
```

The driver mints the invocation, so the spool directory's name is printed by
the run (`invocation: <id>`) rather than chosen in advance.

## The recipe (direct)

Three environment variables and one script. Choose a spool directory OUTSIDE
this repository — the spools are large and are never committed.

```sh
cd typescript/probes
npm ci

export SENSORIUM_TIER=call
export SENSORIUM_SPOOL=/path/to/a/store/probes-1
export SENSORIUM_MANIFEST_DIR="$SENSORIUM_SPOOL/manifests"
npm run probe
```

and for the `node --test` harness, which needs two more:

```sh
export SENSORIUM_SPOOL=/path/to/a/store/nodetest-1
export SENSORIUM_TS_ROOT="$PWD"
export SENSORIUM_TS_PKG="$PWD/.."
npm run probe:nodetest
```

Both scripts run the harness and then the checker with `;`, never `&&`. That is
deliberate: **`vitest run` is red by design** — `never_settles.probe.test.ts`
parks forever and vitest times it out, and `swallow3.probe.test.ts` raises a
rejection nobody handles — so an `&&` would stop before the only thing that
actually decides anything. **`check.mjs`'s exit status is the gate**: 0 all
asserted, 1 a check failed, 2 it was called wrong.

`check.mjs` refuses with exit 2 and one line of usage when a directory is
missing — an unset variable reaches the script as an empty argument, which is
the same refusal. In `vitest` mode the manifest directory is required, so the
tally checks cannot be skipped by leaving an argument off.

```
node check.mjs <vitest|nodetest> <spool dir> [manifest dir]
```

## What is here

| | |
|---|---|
| `src/async.probe.test.ts` | E3 S1–S4 and the T1/T2 negative control, `node` |
| `src/async.jsdom.probe.test.ts` | the same under `// @vitest-environment jsdom` |
| `src/sites.probe.test.ts`, `src/sites.component.tsx` | E4: 20 shapes, each under a `// SITE <name>` marker |
| `src/swallow.probe.test.ts` | E8 shapes 1, 2, 4, 5, each row under a `// SWALLOW <shape> <kind> <how>` marker |
| `src/swallow3.probe.test.ts` | E8 shape 3, the rejection nobody handles |
| `src/each.probe.test.ts` | `test.each`: three rows, three names, no `#k` |
| `src/concurrent.probe.test.ts` | the naming hazard, counted and reported, never gated |
| `src/never_settles.probe.test.ts` | a frame that parks and never returns |
| `src/describe_chain.probe.test.ts` | `outer > inner > leaf`, synchronous describes (P11) |
| `src/timer_parentless.probe.test.ts` | a timer callback entered with an empty stack |
| `nodetest/async.probe.test.ts` | E3 again through `register.mjs`, outside vitest's `include` |
| `check.mjs` | reads every spool and asserts; JSON on stdout |
| `vitest.config.ts` | the probe files, plus the recorder's own wiring under `SENSORIUM_PROBE_DIRECT=1` |

The `// SITE` and `// SWALLOW` markers are read by `check.mjs` out of the source,
so no line number is written down twice: move a function and its expectation
moves with it.

## The versions

`package.json` pins `vitest` and `vite` **exactly**, with no caret, because the
acceptance lens is a version and a floating range would silently re-lens every
number this project produces. `npm ci` reproduces the lock; `npm install` is for
changing the pin on purpose.
