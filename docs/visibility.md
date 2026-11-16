# Visibility

What a trace stores, and what no query can see. The file layout is
[TRACE-FORMAT.md](TRACE-FORMAT.md), with conformance vectors under
`trace-format/vectors/`.

## What a trace file holds

A trace is one SQLite file under `$SENSORIUM_DIR/traces` (default
`~/.sensorium/traces`), created **`0600` in a `0700` directory** from 0.15.0
on, `0644` under your umask before that. It holds:

- **the process environment** at record time, variable by variable, minus
  what **rule v1** withheld: a secret-*named* variable is stored as
  `<redacted>` beside an HMAC under a key that never leaves the store, so
  `refocus` can still say whether it changed; `info` names what it took;
- **everything the program wrote** to stdout and stderr, interleaved with the
  events it wrote them between;
- the command line, the working directory, the git commit, and content
  digests of every source file the run traced;
- **captured argument, return and local values**, clipped to the caps `info`
  prints and under that same rule by NAME, with any secret-shaped SPAN inside
  a stored text replaced where it stands ([redaction.md](redaction.md));
- which asyncio task each event ran in, and the tasks' names;
- one causal fingerprint per thread (events outside any task) and per
  asyncio task.

The file layout is trace format 4; `TRACE-FORMAT.md` is the contract, with
conformance vectors under `trace-format/vectors/`. A Rust trace holds the
environment, command line, source digests and captured `Debug` values the same
way; its tasks are libtest tests and spawned threads, its output is declared
absent, and its spool holds the same until conversion
([../rust/README.md](../rust/README.md)).

`info` refuses to print the environment and `refocus` the variables it
compared: both carry secrets. **What rule v1 does not reach is stored as it
was**, a secret in a variable named `x` or a bare `key`, one no content
pattern knows, the command line, a token split across two `write()`s,
anything under `SENSORIUM_NO_REDACT`, every mode bit on Windows, and every
trace already on disk until `sensorium redact` runs over it. Treat a trace as
you would a core dump or a `.env`: sharing one shares all of the above, and
`SENSORIUM_DIR` is the only control over where it lands.

## What sensorium sees at all

Code that this run traced, for the Python recorder, Python code in files
under the run's own root; for the Rust recorder, the workspace's own crates;
for the TypeScript recorder, the eligible ES modules under the invocation's
root. **Nothing else.** On a Python trace, no command here says anything about:

- any child process, by any mechanism;
- any thread not started through Python's own `threading` / `_thread`;
- any file the program read or wrote, only source files are hashed, so
  config, fixtures, databases and inputs move unseen;
- any code outside the run's root: the stdlib, site-packages, installed
  dependencies, `PYTHONPATH` modules, and whatever `--include` / `--exclude`
  filtered out;
- the environment beyond the variables a command names as compared;
- the clock, the network, and everything else the machine did.

This is stated as a category rather than as a list of mechanisms on purpose.
Five review rounds of `refocus` each found a mechanism the tool could not see;
an enumeration that looks complete is more dangerous than no enumeration,
because a reader who checks the list concludes their case was covered. The
Rust and TypeScript recorders draw their boundaries the same way, in
[../rust/HONESTY.md](../rust/HONESTY.md) and
[../typescript/HONESTY.md](../typescript/HONESTY.md) with their blind-spot files
beside them.
