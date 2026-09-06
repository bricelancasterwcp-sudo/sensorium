# Pending vectors

Vectors whose rows no builder can write yet. `tests/vectors.load_all` globs `vectors/v*.json`
non-recursively, so nothing here runs. **Promotion rule:** a pending vector moves to `../` (and
is renamed `vNN-…`) in the same commit that teaches `tests/vectors.py` to build its rows; it may
not be promoted before it passes. Authored 2026-09-05 (S0); promotion is S1's first task.

Every finalized meta, format 4 or format 5 alike, carries TRACE-FORMAT §4's full required set
(`run_id, argv, cwd, env_hash, start_ts, end_ts, exit_status, main_thread_ident,
fingerprint_basis, truncated_count, source_hashes, recorder, lang, capabilities`) -- a model
trace earns no exemption from it.

Keys beyond VECTORS.md: `tokens` (rows: task, pos, token, piece, logprob, entropy, topk, ts),
`spans` (rows: task, kind, first_pos, last_pos, text, ref); for two-trace vectors `meta2`
(`{"same_as": "meta", ...overrides}`), `tokens2`, `spans2`; for two-trace **program** vectors
`codes2`, `frames2`, `events2` (the second trace's own `codes`/`frames`/`events`, same shape and
row-position rules as the first); `absent2` -- the builder mints a run id for `$RUN2` but builds
no trace with it, so the id resolves to nothing; and `harness` (`{"reader_max_format": n}`) -- the
question runs through a reader pinned at that format rather than the shipped default. Question
keys beyond VECTORS.md: `expect_absent` (substrings that must not appear), `expect_col0` (a line
that must start at column 0), `expect_same_key` (the printed `"key"` equals the previous
question's). `$RUN`/`$RUN2` substitute as in VECTORS.md.
