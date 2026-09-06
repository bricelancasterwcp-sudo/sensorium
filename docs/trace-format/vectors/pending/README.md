# Pending vectors

Vectors whose rows no builder can write yet. `tests/vectors.load_all` globs `vectors/v*.json`
non-recursively, so nothing here runs. **Promotion rule:** a pending vector moves to `../` (and
is renamed `vNN-…`) in the same commit that teaches `tests/vectors.py` to build its rows; it may
not be promoted before it passes. Authored 2026-09-05 (S0); promotion is S1's first task.

Keys beyond VECTORS.md: `tokens` (rows: task, pos, token, piece, logprob, entropy, topk, ts),
`spans` (rows: task, kind, first_pos, last_pos, text, ref), and for two-trace vectors `meta2`
(`{"same_as": "meta", ...overrides}`), `tokens2`, `spans2`, `absent2` (the second trace is
deliberately missing). Question keys beyond VECTORS.md: `expect_absent` (substrings that must not
appear), `expect_col0` (a line that must start at column 0), `expect_same_key` (the printed
`"key"` equals the previous question's). `$RUN`/`$RUN2` substitute as in VECTORS.md.
