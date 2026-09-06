# Pending vectors

Vectors whose rows no builder can write yet. `tests/vectors.load_all` globs `vectors/v*.json`
non-recursively, so nothing here runs. **Promotion rule:** a pending vector moves to `../` (and
is renamed `vNN-…`) in the same commit that teaches `tests/vectors.py` to build its rows; it may
not be promoted before it passes. Authored 2026-09-05 (S0); promotion is S1's first task.

## The set

| file | pins |
|---|---|
| `m01-format5-refused-by-format4-reader` | a format-5 file is refused by name, never read as empty frames |
| `m02-model-trace-program-commands-refuse` | `tree`/`frame`/`grep`/`exceptions` exit 2 with the one sentence |
| `m03-gens-unnamed-pairs-by-order` | `gen-N` is unnamed; pairs only with unnamed, by order |
| `m04-diff-first-divergence-and-margin` | `p`, pieces, both margins; a token outside top-k reports `> topk-floor` |
| `m05a` / `m05b` / `m05c` `-diff-within-noise-needs-blessed-band` | no band → `DIVERGED` and one line saying why the reading did not happen; a blessed band → `MATCH (within noise)` naming its baseline; a band measured under other weights → `REFUSED` |
| `m06-exit-status-not-a-process-exit` | `exit: n/a (model trace)`; never `None`, never `0` |
| `m07a-spans-exec-ref-joins-program-trace` / `m07b-spans-exec-ref-trace-not-found` | the two exit sources printed as two labeled facts: the daemon's own witness, and the program trace's — present, and not found |
| `m08-join-group-in-runs` | `runs` groups by `join.group`; a trace without `join` lists in place |
| `m09-attention-declared-unwitnessable-under-fa` | `info` prints the flash-attention gap sentence, not `0` and not "predates" |
| `m10-zero-token-generation-row` | a zero-token generation has a `task_fingerprints` row with `n_events 0`, and `gens` prints `H̄:n/a minH:n/a` with no position |
| `m11-fingerprint-ignores-measurement` | identical token ids with different `logprob`/`entropy`/`topk`/`ts` hash equal → `MATCH` (the falsifier `model/HONESTY.md` §4 cites) |
| `p01-signature-canonical-json` | `signature --json`'s shape and printed `key`, `msg` absent, key stable under a file-local rename |

Every finalized meta, format 4 or format 5 alike, carries TRACE-FORMAT §4's full required set
(`run_id, argv, cwd, env_hash, start_ts, end_ts, exit_status, main_thread_ident,
fingerprint_basis, truncated_count, source_hashes, recorder, lang, capabilities`) -- a model
trace earns no exemption from it.

## `meta2: {"same_as": "meta", …}`

The second trace's meta **starts as a copy of the first**, and then each key listed beside
`same_as` **replaces that whole top-level key** -- no deep merge, so a listed `model` object is
the second trace's entire `model`, not a patch over the first's. A key whose value is `null` is
**removed** rather than copied. The removal is not a nicety: `noise_band` is a property of one
trace (the blessed one), and letting it inherit would put a band on both sides and leave the
vector unable to discriminate the case it exists to pin -- which is why `m05b` and `m05c` both
set `"noise_band": null`. A two-trace vector whose second meta is written out in full (`m07a`,
`m08`, `p01`) uses no `same_as` and carries the full required set itself.

Keys beyond VECTORS.md: `tokens` (rows: task, pos, token, piece, logprob, entropy, topk, ts),
`spans` (rows: task, kind, first_pos, last_pos, text, ref); for two-trace vectors `meta2`
(above), `tokens2`, `spans2`; for two-trace **program** vectors `codes2`, `frames2`, `events2`
(the second trace's own `codes`/`frames`/`events`, same shape and row-position rules as the
first); `absent2` -- the builder mints a run id for `$RUN2` but builds no trace with it, so the
id resolves to nothing; and `harness` (`{"reader_max_format": n}`) -- the question runs through a
reader pinned at that format rather than the shipped default. Question keys beyond VECTORS.md:
`expect_absent` (substrings that must not appear -- `m10` uses it to pin that a zero-token
generation prints no `H̄:0`, `minH:0` or `at p0`), `expect_col0` (a line that must start at
column 0), `expect_same_key` (the printed `"key"` -- the one MODEL-TRACES §8 defines -- equals
the previous question's). `$RUN`/`$RUN2` substitute as in VECTORS.md.
