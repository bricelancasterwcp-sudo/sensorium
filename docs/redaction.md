# What a recording withholds — rule v1

Every recorder stored the whole process environment in plaintext until this
slice, at `0644`. A trace of any program launched from a developer's shell
therefore held whatever that shell was carrying — a live `GITHUB_TOKEN`, a
`PGPASSWORD`, an `OPENAI_API_KEY` — readable by every account on the box.

**Rule v1** replaces a secret-*named* environment value with `<redacted>` at
the WRITER, before anything reaches disk, and keeps an HMAC-SHA256 of the
plaintext under a key that never leaves the store, so `refocus` can still say
"this changed" without being told what it changed to.

This page is what the rule does, what it does not do, and what every command
prints about it. The contract is
[`TRACE-FORMAT.md`](TRACE-FORMAT.md) §2 and §4; the rule's own cases are
[`trace-format/redaction-v1.json`](trace-format/redaction-v1.json), read by
all three recorders' suites.

## Not a secret scanner

The rule fires on a NAME. A secret in a variable called `x`, or in one this
set has never heard of, is stored as typed. Nothing in this version reads a
VALUE looking for something that looks like a token — the content rule is a
later version's, and so is the redaction of captured argument, local, return
and output values, which **this version still stores in plaintext**
(`info`'s own `redaction: OFF` line says so in words:
`src/sensorium/query/info_cmd.py::redaction_line`).

Treat a trace the way you would treat a core dump. What the rule removes is
one class of accident — the shell's exported credentials, which nobody chose
to put in the recording — not the recording's plaintext nature.

## The name rule

A name is split into SEGMENTS: on every run of characters outside
`[A-Za-z0-9]`, and on both camelCase boundaries (`apiKey` → `API`, `KEY`;
`HTTPToken` → `HTTP`, `TOKEN`). Every segment is uppercased. The rule fires
when any segment is one of:

```
KEY APIKEY TOKEN SECRET SECRETS PASSWORD PASSWD PASSPHRASE PASS
AUTH AUTHORIZATION CREDENTIAL CREDENTIALS CREDS PRIVATE
COOKIE COOKIES SIGNATURE BEARER JWT DSN ACCESSKEY SECRETKEY AUTHTOKEN
PWD
```

Matching is **segment-exact, never substring**: substring `KEY` would fire on
`MONKEY_PATCH` and substring `PASS` on `BYPASS_CACHE`, and the fixture pins
both as non-firing. `XAUTHORITY` is one segment and does not fire; `authorId`
splits to `AUTHOR`, `ID` and does not fire.

Two amendments to that set, both from the census of 178 real environment
names in `tests/fixtures/benign-env-names.txt`
(`tests/test_redact.py::test_census_fires_on_exactly_the_listed_subset` pins
which of them fire, name by name):

- **`PWD` fires only inside a longer name.** `MYSQL_PWD` and `DB_PWD` are
  passwords; `PWD` and `OLDPWD` are the shell's working directory on every
  machine that has ever run a shell.
- **`PGPASSWORD` fires by whole name.** Segment-exact matching cannot see
  inside a compound word — `PGPASSWORD` is one segment, which is neither `PG`
  nor `PASSWORD` — so libpq's standard password variable is in a short
  `EXACT` set of its own (`src/sensorium/redact.py::EXACT`). A name earns a
  place there only when a census or a report shows it matters.

The false positives that do fire are named rather than hidden: `SSH_AUTH_SOCK`
is a socket path and `GPG_KEY_ID` is an id. Each costs one plaintext path in
a trace, and the digest still makes the value comparable.

## The three knobs

Read once at record time, from the recorded environment, and **recorded in
the trace** so a reader sees what the recording was made under. None of the
three names fires the rule, which the fixture pins — a knob that redacted
itself would hide the terms of its own recording.

| Variable | Reading |
|---|---|
| `SENSORIUM_NO_REDACT` | Any non-empty value other than `0` turns the rule off for that recording; unset, empty and `=0` all leave it on. The spelling follows `SENSORIUM_NO_INVOCATION_LOG`. |
| `SENSORIUM_REDACT_NAMES` | A comma list of names that fire in ADDITION to the segment set. Compared after the same normalisation, so `myco_dsn`, `MYCO_DSN` and `mycoDsn` are one name. |
| `SENSORIUM_REDACT_ALLOW` | A comma list of names that never fire. **Wins over `SENSORIUM_REDACT_NAMES`** — a user's statement about their own variable outranks their own list. |

There is no CLI flag. `sensorium run` records the environment it was launched
in, and the knob belongs to that environment the way `SENSORIUM_DIR` does.
`tests/test_redact.py::test_env_honours_both_knobs` and
`tests/test_record_redaction.py::test_names_and_allow_knobs` are the pins.

## The key, and what a digest is

`<trace root>/redaction.key` — a sibling of `traces/`, 32 bytes from the OS
random source, mode `0600`. It is created once by whichever sensorium process
first needs it and is never copied into a trace, a spool, a header or the
invocation log.

- **Digest** = `HMAC-SHA256(key, value)`, first 16 hex characters, stored
  beside the NAME in the trace's `redaction.env` table.
- **`key_id`** = `SHA-256(key)`, first 8 hex, stamped once per trace: whether
  two traces' digests are comparable at all.
- **Created by content, never by an empty file.** 32 bytes go into a private
  per-pid `redaction.key.<pid>.tmp`, are written whole and fsynced, and only
  then is the finished file hard-linked at its name (ruling R15). An
  `O_EXCL` open on the final name would be visible at 0 bytes for as long as
  the write takes, and a recorder arriving in that window would read an empty
  key. A loser of the race reads the WINNER's file, so both recordings'
  digests are taken under one key
  (`tests/test_redact.py::test_a_created_key_is_published_whole_and_leaves_no_tmp`,
  `::test_a_loser_of_the_creation_race_reads_the_winners_key`; on a
  filesystem with no hard links it falls back to an atomic rename,
  `::test_a_filesystem_without_hard_links_falls_back_to_replace`).
- **A key file that is not 32 bytes, or cannot be read, is the USER's file
  and is never written over** — replacing it would invalidate every digest
  already in the store. The recording says `keyed: false` instead
  (`::test_an_empty_key_file_is_unkeyed_and_never_written_over`,
  `::test_a_key_file_of_the_wrong_size_is_unkeyed_and_says_why`).
- **No key at all** is a state, not a failure: the values are still redacted,
  every digest is `null`, and the trace says `keyed: false`
  (`tests/test_record_redaction.py::test_unreadable_key_records_unkeyed`).
  The fallback loses comparability and never loses safety.
- **A key looser than 0600 is read anyway and named on `info`** — refusing to
  record over the user's own file permissions helps nobody
  (`tests/test_info_redaction.py::test_a_key_looser_than_0600_is_named_on_the_keyed_line`).

**A digest is an equality identity, never a commitment.** Sixteen hex
characters say whether two values are the same value; anyone holding the key
file can compute the digest of any guess, so a redacted LOW-ENTROPY value —
`true`, a port number, a username — is guessable. That is why the key is
`0600`, why it is never in a trace, and why `info` prints the NAMES that were
redacted and never their digests
(`tests/test_info_redaction.py::test_the_digest_is_never_printed`).

### The key across a process boundary

The Python recorder reads the key file in-process. The Rust and TypeScript
runtimes never touch a key file at all — creating one means a directory, a
temporary, a link and a race, and those runtimes are linked into somebody
else's program. Their DRIVER (`cargo sensorium`, `sensorium ts run`) mints or
reads the key and hands the hex to the recorded process as
`SENSORIUM_REDACT_KEY`. **Every recorder DELETES that variable from what it
records** rather than redacting it: a digest of the key under the key is a
pointless row, and `keyed: true` already implies it was there
(`tests/test_redact.py::test_env_off_keeps_plaintext_but_drops_key_var`,
`rust/cargo-sensorium/tests/convert_e2e.rs::check_redaction`, which drives a
real invocation end to end). `refocus` knows the name too and never reports
it as a world change
(`tests/test_refocus_redaction.py::test_the_key_variable_is_not_compared_on_the_live_side`).

Under `cargo sensorium`, when neither `SENSORIUM_DIR` nor `HOME` resolves to
a store, the driver records **unkeyed** and says so on stderr once — and only
after the build, never per recorded pid, which under a `cargo test` would be
once per process.

## What lands in the trace

- `meta.env` stays a string-to-string map. A redacted value is the literal
  **`<redacted>`** — the spelling this repo's renderers already use for a
  withheld thing (`<unread>`, `<not in scope>`).
- `meta.redaction` says what the rule did:

  ```json
  {"rule": "v1", "mode": "on", "keyed": true, "key_id": "0a1b2c3d",
   "env": {"GITHUB_TOKEN": "9f2c…"}, "names": [], "allow": [],
   "by": "recorder"}
  ```

  `env` maps each redacted NAME to its digest (`null` when unkeyed) and is
  **sorted**, so one environment gives one table byte for byte whichever
  language wrote it. `by` is the LAST hand that applied the rule —
  `"recorder"`, or `"converter"` where a spool from a runtime that predates
  the rule was converted under it.
  The object's key ORDER is **not** a wire promise: the Rust converter's map
  is alphabetised on the way out, and every reader here goes by key.
- **Mode off** writes exactly `{"rule": "v1", "mode": "off"}` and nothing
  more — a header naming a key or a knob list while claiming to have applied
  nothing would invite a reader to believe the plaintext beside it had been
  considered
  (`tests/test_redact.py::test_meta_off_and_on_shapes`).
- **No `redaction` key at all** is a trace recorded before the rule existed.
  It holds the shell's environment as it was. Absence of the key is not
  absence of secrets.
- `env_hash` is taken over the environment **as stored**, so a reader can
  recompute it from the trace, and two runs of one unchanged shell hash alike
  whatever their secrets were
  (`tests/test_record_redaction.py::test_env_hash_is_over_the_stored_env`).

## What `info` prints

The `env:` field on the interpreter line has three forms, and the difference
between the last two is the point:

```
env:3c2cfb29                                        # no rule ran, or mode off
env:3c2cfb29 (120 vars, 0 redacted)                 # the rule ran and fired on nothing
env:3c2cfb29 (120 vars, 2 redacted: GITHUB_TOKEN, SSH_AUTH_SOCK)
```

A MEASURED zero is not the same fact as the bare hash a trace from before the
rule prints. Names only, first eight then `+N more` — a digest beside the
name it belongs to would be an offline guessing target for any short value.

Directly under `caps:`, one line on every trace, in one of four forms —
the keyed one carrying a note when the store's key is loose:

```
redaction: rule v1, keyed (key 0a1b2c3d), by recorder
redaction: rule v1, keyed (key 0a1b2c3d), by recorder (key mode 0644 -- expected 0600)
redaction: rule v1, UNKEYED (no redaction.key in the store); by recorder
redaction: OFF (SENSORIUM_NO_REDACT) -- the environment and every captured value are stored in plaintext
redaction: none -- recorded before redaction existed; plaintext throughout
```

The mode note rides the keyed form only when the store's key is loose AND is
the key that took THESE digests — a note about some other store's file
permissions would send a reader to the wrong file. Vectors
`v42-redaction-render` and `v42b-redaction-none` pin the lines in the format;
`tests/test_info_redaction.py` pins each form and its placement.

## What `refocus` compares

`refocus` re-runs a recording and asks whether the world it ran in was the
same. It never printed environment VALUES, so a redacted one costs it
nothing it was using: for a name either side redacted, it compares DIGESTS.

| Original | Re-run | Answer |
|---|---|---|
| digest, key K | digest, key K | the digests; a mismatch withholds exactly as a changed variable always did |
| plaintext | digest, key K | the plaintext's HMAC under the store's key, when the store's key is K |
| digest, key K | digest, key K′ | **unverifiable** — `different keys` |
| digest `null` | anything | **unverifiable** — `unkeyed` |

Three rules follow from that, and each is a pin:

- **A redacted session or harness variable keeps its exemption.** Membership
  of session set 1 or harness set 1 is a judgement about the NAME — which
  shell a process was launched from, which worker of a pool ran it — so it
  holds for a value nobody can read exactly as it holds for one anybody can
  (ruling R21). `SSH_AUTH_SOCK` is in session set 1 AND fires rule v1, and
  the two branches disagreeing would mean a re-run from another terminal
  withholding on a trace made after the rule and granting on one made before
  it (`tests/test_refocus_redaction.py::test_a_redacted_session_variable_keeps_its_exemption`).
- **An unverifiable name never withholds** (ruling R19). It is named on the
  env line and stamped as a check that could not run —
  `env: unverifiable in part (redacted variables not comparable)`, which
  `info` replays short as `licence unverifiable: env (redacted, not
  comparable)` — beside the names, `1 redacted variable(s) not comparable
  (different keys): GITHUB_TOKEN`. A check that could not run is not a
  finding against the pair. Vector `v43-refocus-redacted-env`.
- **The `compared` count excludes them** (ruling R22). A line that said
  "12 variables compared" and then named one of them as not comparable would
  have counted a check it did not run
  (`tests/test_refocus_redaction.py::test_the_compared_count_excludes_the_uncomparable`).

## File modes

Everything a recorder CREATES from this version on is `0600`, and every
directory it creates is `0700` — by explicit mode at creation, never by a
later `chmod`, because a file created `0644` and tightened a moment later is
readable for exactly the moment it is being filled with what it holds. That
covers the trace, the store root, `traces/`, `redaction.key`, the Rust
spool directory and its `<pid>.proc.json` / `.spool` / `<pid>.runner.json`,
and the TypeScript spool
(`tests/test_record_redaction.py::test_created_files_are_0600_and_dirs_0700`;
`rust/cargo-sensorium/tests/convert_e2e.rs::check_modes` asserts the same
end to end over a real invocation).

A file or directory that **already exists** keeps the permissions its owner
chose: a person who pointed `SENSORIUM_DIR` at a directory of their own is
not overruled. **Windows** has no POSIX mode bits; every number here is
advisory there.

## The honest limits

- **Captured values are still plaintext.** Arguments, locals, return values
  and program output are stored as the caps clipped them. A later version
  redacts them.
- **A name this set has never heard of is stored as typed.**
  `SENSORIUM_REDACT_NAMES` is the remedy, and it is recorded.
- **A digest is guessable for a low-entropy value** by anyone holding the key
  file. See "The key, and what a digest is" above.
- **Digests compare within one language.** A non-UTF-8 environment value
  digests differently in Python — which hashes the surrogateescaped byte
  `os.environ` handed it
  (`tests/test_redact.py::test_digest_hashes_surrogateescaped_bytes`) — and
  in Rust and TypeScript, which hash the U+FFFD they stored in its place.
  This is the same per-recorder rule `env_hash` already carries in
  [`TRACE-FORMAT.md`](TRACE-FORMAT.md) §4, for the same reason.
- **A trace that predates the rule is not covered by it.** Nothing rewrites
  a stored trace in this version.

## Coming in later versions

- **Captured values**, by the same name rule and by a CONTENT rule that reads
  a value for token-shaped text whatever its name is. The fixture already
  carries an empty `content` list for those cases
  (`tests/test_redact.py::test_the_fixtures_content_list_is_still_empty`),
  and the Rust spool grows a content window with them.
- **`sensorium redact`**, a retrofit that applies the rule to traces already
  in the store and tightens their modes when asked.
