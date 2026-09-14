# The TypeScript recorder's honesty ledger — §13: Redaction

Section 13 of [`typescript/HONESTY.md`](HONESTY.md), **written here 2026-09-14
(secrets redaction part B) rather than in that file, which is one line under
800**, on the precedent [`HONESTY-COST.md`](HONESTY-COST.md) set 2026-09-11
and [`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md) before it. The ledger's
own index carries one `| 13 |` row pointing here, the way its `| 9 |` rows
point at the cost file. `§13` names this section wherever it is cited.

## 13. Redaction

**The promise.** A secret this rule can name never reaches a spool, and
everywhere it could not reach is stated rather than left to be found.
[`../docs/redaction.md`](../docs/redaction.md) is the rule itself; this is
what THIS recorder does with it.

**Both halves run at the writer, in the runtime.** Unlike the Rust recorder,
which has no regex engine and leaves the content half to its converter, this
runtime does all of it before a line is appended to the spool:

- **The environment**, once at boot. `bootEnv` writes the stored `env`, its
  `envHash`, the `envRedaction` name → digest table and the `redaction`
  object into the BOOT record, and deletes `SENSORIUM_REDACT_KEY` from what
  it stores — the driver mints or reads the store's key and hands the hex
  over, because a runtime linked into somebody else's program has no business
  creating files.
- **Every captured value**, under the name it was bound to.
  `redactCaptures` takes a focused CALL's arguments and a LINE's deltas;
  `redactReturn` takes a RETURN under the LAST `.`-segment of the CALLEE's
  own qualname, which the FILE record already declared. A name that does not
  fire is offered to the content rule instead, and that ORDER is load-bearing:
  a digest taken after a span had been replaced would be an HMAC of a
  CONSTANT, and two different secrets would then carry one identity.
- **Every text with no name to be asked about.** `dbg.mjs`'s `exc` runs the
  content rule over a thrown message, and a hit is marked on the `exc` object.
- **The key and the knobs are read ONCE, lazily, and never re-read.** A
  program that edits `process.env` half way through its own test run cannot
  change what the rest of the recording was made under, or turn the rule off
  after the first secret has been withheld.

**What a taken capture keeps.** The kind stays `dbg`, `v` becomes
`<redacted>`, `trunc` is written **false** rather than dropped (nothing was
clipped — the whole of it was taken), `oid` and `type` stay so `flow --object`
can still follow the thing, and `redacted: {by, digest}` says which rule took
it. Two captures are left exactly as they arrived because there is nothing to
take: an `unread`, which never held a text, and a `dbg` whose text is exactly
`undefined` or `null`, which is how node's inspector spells a function that
produced no value (ruling R19). Whole texts and nothing near them — `NaN` is a
value the program had.

**The wire stays v1.** A JSON object with one more optional key is additive:
an ingest older than this version copies a capture verbatim, so the key rides
through unread, and a READER older than it ignores the key and prints the
marker text — which leaks nothing either way. The ingest of this version
carries a 0.6.0 recorder's
judgement through untouched, applies the NAME rule itself to a spool from
0.5.0 or earlier (whose captures nobody judged), applies the CONTENT rule on
every path because it is idempotent, and counts `redaction.values` at the
WRITE — one per stored capture carrying a `redacted` object, whichever hand
put it there, so the count is a function of the trace's contents.

**`by` names the LAST hand.** `recorder` only where the BOOT says `mode: "on"`
AND was written by `sensorium-ts 0.6.0` or better; `converter` otherwise. A
0.5.0 spool's environment is the recorder's work and its captures are the
ingest's, one word cannot say both, and the later hand is the one whose key
the capture digests are under. **So re-ingesting a 0.5.0 spool produces a
trace that says `converter` where it used to say `recorder`.**

**What it does not reach, stated:**

- A secret in a binding named `x`, or in a bare `key`, or one whose shape is
  on none of the nineteen content patterns. The rule is a floor, not a
  scanner.
- **`argv`** — the harness command line is stored in plaintext.
- **Anything at all under `SENSORIUM_NO_REDACT`**, which the trace records,
  and which the ingest obeys rather than overruling: a recording made with
  the rule off is converted as it was written.
- **The wrapper's files under the consumer's `node_modules/.sensorium/`** are
  at the platform default rather than `0600`. They hold no environment and no
  digests. The spool itself, and the directory holding it, are `0600`/`0700`.
- **A spool ingested against a store that did not record it**: `redaction`
  carries the recording driver's `key_id` while any digest the INGEST took is
  under the ingesting store's key. On one box those are one key.
- Program output is not a limit here, because this recorder declares it
  absent (§7) and stores none.

**Falsified by** `typescript/test/redact.test.mjs`, which reads
[`../docs/trace-format/redaction-v1.json`](../docs/trace-format/redaction-v1.json)
— the same file the Python and Rust suites read, so three implementations of
one rule agree only on what all three are asked;
`typescript/test/rt.redaction.test.mjs` (a focused run withholds the value
under a firing name and the secret in every text; a return the seal defers is
withheld under the same rule; a firing name that returned nothing says so;
a thrown message is scanned and a name the rule does not know is not);
`tests/test_ts_ingest_redaction.py` (the carried-through case, the older-spool
case, the `mode: "off"` case, `values` counting captures and not records, and
the RETURN under a firing qualname); `tests/test_ts_driver_redaction.py` for
the key hop and the spool's modes; and `corpus/typescript/secret_in_env`,
which plants a token in the environment of a real vitest run and asks `info`,
`frame`, `watch` and `flow` what became of it — every one of its questions
asserting the token itself appears nowhere in the answer.
