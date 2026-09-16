# What a recording withholds — rule v1

Every recorder stored the whole process environment in plaintext until this
slice, at `0644`. A trace of any program launched from a developer's shell
therefore held whatever that shell was carrying — a live `GITHUB_TOKEN`, a
`PGPASSWORD`, an `OPENAI_API_KEY` — readable by every account on the box.

**Rule v1** replaces a secret-*named* environment value with `<redacted>` at
the WRITER, before anything reaches disk, and keeps an HMAC-SHA256 of the
plaintext under a key that never leaves the store, so `refocus` can still say
"this changed" without being told what it changed to. From this version it
does the same to every value a recording CAPTURES — an argument, a local, a
return, an exception message, a line of output — under the name that value
was asked for by, and takes a secret-shaped SPAN out of any stored text
whatever it was called.

This page is what the rule does, what it does not do, and what every command
prints about it. The contract is
[`TRACE-FORMAT.md`](TRACE-FORMAT.md) §2, §4 and §5; the rule's own cases are
[`trace-format/redaction-v1.json`](trace-format/redaction-v1.json), read by
all three recorders' suites.

## Not a secret scanner

Two halves, and neither is a scanner. The **name rule** fires on what a value
was CALLED: a secret in a variable called `x`, or in one this set has never
heard of, is stored as typed. The **content rule** fires on what a text LOOKS
like, and its list is a floor of nineteen shapes — a secret matching none of
them is stored as typed too. Between them they reach the environment (by name
only), every captured value (by name) and every stored text (by content).
What they do not reach is "The honest limits" below, and the README's "What a
trace file holds" says the same in shorter words.

Treat a trace the way you would treat a core dump. What the rule removes is
two classes of accident — the shell's exported credentials, which nobody
chose to put in the recording, and a secret-named or secret-shaped value that
happened to pass through a recorded frame — not the recording's plaintext
nature.

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

- **`PWD` and `KEY` fire only inside a longer name.** `MYSQL_PWD` and
  `DB_PWD` are passwords; `PWD` and `OLDPWD` are the shell's working
  directory on every machine that has ever run a shell. A bare `key` is a
  cache key, a dict key, a lookup key on almost every function that iterates
  a mapping, so redacting it by default would blind `watch` on the commonest
  local in the language; every compound spelling (`api_key`, `apiKey`,
  `secret_key`, `build_key`, `KEY_FILE`) still fires, and a codebase where a
  bare `key` IS the secret restores it with `SENSORIUM_REDACT_NAMES=key`.
  Amended into **rule v1** rather than minted as a v2, because when it was
  made no trace under the earlier spelling existed outside this box and CI.
- **`PGPASSWORD` fires by whole name.** Segment-exact matching cannot see
  inside a compound word — `PGPASSWORD` is one segment, which is neither `PG`
  nor `PASSWORD` — so libpq's standard password variable is in a short
  `EXACT` set of its own (`src/sensorium/redact.py::EXACT`). A name earns a
  place there only when a census or a report shows it matters.

The false positives that do fire are named rather than hidden: `SSH_AUTH_SOCK`
is a socket path and `GPG_KEY_ID` is an id. Each costs one plaintext path in
a trace, and the digest still makes the value comparable.

## The content rule

Nineteen patterns over a stored TEXT, whatever that text was called, most
floored by a minimum length so a short benign string cannot fire and the rest
by their own delimiters (`url-userinfo` by the `://` and the `@`, `pem` by
its BEGIN and END lines): a URL's userinfo
password, a PEM private-key body, an `Authorization: Bearer`/`Basic` value, a
JWT, and the provider-prefixed shapes — `sk-ant-`, `sk-`, Stripe's
`sk_live_`/`rk_test_`, `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`, `github_pat_`,
`glpat-`, `xox…-`, `AKIA`/`ASIA`, `AIza`, `hf_`, `npm_`, `pypi-`, `dop_v1_`,
`shpat_` and `SG.…`. `src/sensorium/redact_content.py`'s table is the list;
the Rust converter's `redact_content.rs` (the `regex` crate) and
`typescript/src/redact.mjs` hold the same nineteen, and
[`trace-format/redaction-v1.json`](trace-format/redaction-v1.json)'s
`content` list is what proves the three agree, pattern by pattern, with a
positive and a negative each.

Three things about it are worth stating plainly:

- **It replaces a SPAN and keeps the sentence around it.**
  `postgres://u:<redacted>@h/db` is what a person debugging a connection
  string needs, and it is why a content hit carries no digest — a partial
  cannot honestly commit to the whole.
- **A hit means the text CHANGED, never that a pattern matched.** The
  userinfo pattern matches the marker it put there itself, and replacing
  `<redacted>` with `<redacted>` is not a second hit. That is what makes the
  rule idempotent across a re-conversion and the `values` count below honest.
- **It runs where a text is STORED, and never over the environment.**
  Environment values are judged by NAME in all three recorders: the Rust
  runtime is dependency-free and has no regex engine, and one rule with two
  spellings would be two rules.

Before the table runs at all, a pre-check decides whether any of the nineteen
could match, so a string holding no secret-shaped prefix — which is nearly
every string a recorder touches — costs two searches rather than nineteen
substitutions. Two searches and not one: an alternation of the literal
prefixes of the case-SENSITIVE patterns, and a case-blind `Bearer|Basic` for
the one pattern that is itself case-blind. A pre-check narrower than the
pattern it guards is a leak, not an optimisation — the first spelling of it
covered `Bearer` and `bearer` and let `Authorization: BEARER <token>` through
untouched (ruling R21, fixed with the two fixture rows that now pin it in all
three languages).

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

Under `cargo sensorium`, a store whose key cannot be created or read records
**unkeyed** and says so on stderr once, **before the build** —
`sensorium: no redaction key at <path> (<reason>); digests will be absent` —
once for the whole invocation and never per recorded pid, which under a
`cargo test` would be once per process.
(`redaction_key.rs::only_the_door_that_was_asked_to_make_the_key_reports_not_having_one`
pins the REASON that line carries and which of the two doors produces one;
nothing asserts the printed line itself.) A store root that resolves to nothing
— neither `SENSORIUM_DIR` nor `HOME` set — is a different case and produces no
trace at all: the driver says nothing, cargo runs, and the converter's own
error afterwards names the missing store
(`cargo-sensorium: SENSORIUM_DIR is unset and HOME is unset too`, exit 2).
Failing in front of the build would cost a person the test run they asked for
over a trace they were going to be told about anyway.

## What lands in the trace

- `meta.env` stays a string-to-string map. A redacted value is the literal
  **`<redacted>`** — the spelling this repo's renderers already use for a
  withheld thing (`<unread>`, `<not in scope>`).
- `meta.redaction` says what the rule did:

  ```json
  {"rule": "v1", "mode": "on", "keyed": true, "key_id": "0a1b2c3d",
   "env": {"GITHUB_TOKEN": "9f2c…"}, "names": [], "allow": [],
   "by": "recorder", "values": 12}
  ```

  `env` maps each redacted NAME to its digest (`null` when unkeyed) and is
  **sorted**, so one environment gives one table byte for byte whichever
  language wrote it. `values` is the captured-value count of "What a captured
  value becomes" below, and `by` is the LAST hand that applied the rule:
  `"recorder"` only where the RUNTIME did both halves of it, `"converter"`
  otherwise. The object's key ORDER is **not** a wire promise: the Rust
  converter's map is alphabetised on the way out, and every reader here goes
  by key.
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

## What a captured value becomes

A capture is the tagged object [`TRACE-FORMAT.md`](TRACE-FORMAT.md) §5
describes — `{"k": "str", "v": …}`, a `seq`/`map` with a sample, an `obj`
with a `repr`, a `dbg` text. Rule v1 performs exactly ONE of two operations
on it, and which one is decided by what fired:

- **A name hit takes the WHOLE value** and leaves
  `"redacted": {"by": "name", "digest": "<16 hex>"}` beside the tag — `null`
  there where the store had no key. The tag itself is kept, so a reader that
  has never heard of the key still prints a string where a string was.
- **A content hit replaces the matched SPAN inside the text** and leaves
  `"redacted": {"by": "content", "digest": null}`.

The two never land on one capture: a value taken by name has no text left to
scan, and the content rule refuses anything already carrying `redacted`
(`tests/test_redact_values.py::test_the_content_rule_never_touches_a_name_redacted_capture`).

### Which name the rule is asked about

| Where | The name judged |
|---|---|
| a CALL argument, a LINE delta | the binding's own name |
| a RETURN value | the LAST segment of the CALLEE's qualname, split on `.` (Python, TypeScript) or `::` (Rust): `Store.get_api_key` is asked for by `get_api_key`, so its answer is an API key whatever the caller stores it in |
| a `map` sample's VALUE | the paired KEY's own text where that key is a `str` — a headers dict's `authorization` entry. **Python only**: the Rust and TypeScript recorders store a rendering rather than a decomposed map, and the content rule is their only reach into one |
| an output chunk, an exception message | none — the content rule alone; a message is a sentence the program wrote, not a value with an identity, so a hit is marked on the `exc` object and carries no digest — except a Rust `Err` return taken by name, whose origin RAISE repeats the RETURN's withholding (ruling R16): one withheld text on two rows, under one digest, `trunc` false on both, counted once |
| an element of a SPAWNED command line (`meta.children`) | none — the content rule alone, at the audit sink (ruling R25); an argv has positions rather than bindings, and a hit is counted like any other |

`tests/test_redact_values.py::test_named_return_reads_the_last_segment` and
`::test_a_map_value_under_a_firing_key_is_redacted_by_that_name`,
`typescript/test/rt.redaction.test.mjs`,
`rust/cargo-sensorium/tests/convert_redaction.rs`.

### What a name hit leaves, kind by kind

| `k` | After |
|---|---|
| `str` | `v` = `<redacted>`, `trunc` dropped; the digest is over the CLIPPED text, which is what the trace would otherwise have held |
| `num` | `v` = `<redacted>`; the digest is over `repr(v)`, so `1234` and `"1234"` never share one |
| `obj` | `repr` = `<redacted>`, `trunc` dropped; `type` and `oid` stay — an identity is not a value |
| `dbg` | `v` = `<redacted>`, `trunc` written **false** rather than dropped, so a reader never has to guess whether the formatter was cut short; the digest is over the text |
| `seq`, `map` | `sample`, `trunc` and `unread` dropped; `type`, `len` and `oid` stay, and `digest` is `null` — a container has no single text to hash |
| `none`, `bool`, `unread` | untouched. They withhold nothing, so a marker would cost a reader a fact and hide no secret |
| anything else | withheld WHOLE: `k` kept, every other key dropped, `digest` `null`. This control's failure direction has to be a lost fact, never a kept secret (`tests/test_redact_values.py::test_an_unknown_kind_is_withheld_whole_under_a_firing_name`) |

Two texts are exempt even under a firing name, because they say the program
produced no value at all: Rust's synthesised unit return `()` (ruling R17)
and a `dbg` text that is exactly `undefined` or `null` (ruling R19). Neither
is taken, marked or counted — whole texts and nothing near them, so a `NaN`
or a text that merely contains one of these is taken like any other
(`rust/cargo-sensorium/tests/convert_redaction.rs::a_unit_return_under_a_firing_name_keeps_its_value_and_is_not_counted`,
`tests/test_redact_values.py::test_a_dbg_text_that_withholds_nothing_is_never_taken`,
`::test_the_boundary_is_the_whole_text_and_nothing_near_it`).

### What the readers print

A taken value is never rendered as its marker TEXT, because every taken value
in a run carries the same one. The digest is what tells two of them apart,
and eight hex of it is what a screen shows
(`tests/test_fmt_redaction.py`, vector
[`v42-redaction-render`](trace-format/vectors/v42-redaction-render.json)):

| Reader | A value taken by name | A content hit |
|---|---|---|
| `frame`, `tree`, `grep` | `token=<redacted #01234567>` for a `str`/`num`/`dbg` (or `<redacted>` unkeyed); `cfg=dict[3]=<redacted>` for a container, whose size is a fact about the program; `Cfg#7` for an `obj`, byte for byte what it printed before | as stored: `url='postgres://u:<redacted>@h/db'` |
| `watch` | a state line reads `token=<redacted; no comparable value>`; a predicate that met only taken values ends `NOTHING WAS CHECKED` at exit 3, listed as `token: redacted by rule v1; no comparable value`, and the guidance names the remedy — `export SENSORIUM_REDACT_ALLOW=token && <the re-record command>` | compared as the text the trace holds |
| `flow --object` | refuses at exit 2: `'token' at e1 is redacted (by name) and has no identity or value to follow` — the kept address is real and its occupant was never recorded | followed exactly as before |
| `flow --value` | sights nothing, including `--value '<redacted>'`: a literal that happens to be the marker would report every secret in the run as sightings of one value | sighted by the text the trace holds |
| `info` | `; values redacted: N` on the `redaction:` line, keyed and unkeyed alike | counted the same way |

Whole digests are never printed — a digest beside the name it belongs to is
an offline guessing target for any short value
(`tests/test_fmt_redaction.py::test_the_whole_digest_is_never_printed`).

### `values`, and whose hand took them

`redaction.values` is the number of values the trace WITHHOLDS, counted by
the trace's writer: the Python recorder at finalize over what it wrote, the
Rust and TypeScript converters as they build. It is a pure function of the
trace's contents, which is why a secret local re-captured at every line of a
loop counts ONCE — only the deltas a row stores are counted — and why one
text written into two rows (a panic's message; an `Err` return and the origin
RAISE synthesised in front of it, ruling R16) counts once too. A `RAISE` and
a `HANDLED` of one exception are two stored texts and count two. Absent
entirely under `mode: off`, so a zero is always a measured zero
(`tests/test_record_values_redaction.py::test_a_secret_local_in_a_loop_is_counted_once_not_once_per_line`,
`tests/test_ts_ingest_redaction.py::test_values_counts_the_captures_and_not_the_records`,
`rust/cargo-sensorium/tests/convert_redaction.rs::an_err_return_taken_by_name_is_withheld_on_its_origin_raise_under_one_digest`).

`by` says which hand was LAST: `"recorder"` only where the runtime did the
value half itself — the Rust wire at v4 or better with a `redaction` header
whose mode is on, or `sensorium-ts` 0.6.0 or better. A Rust spool a 0.6.0
runtime wrote and a 0.5.0 TypeScript spool have plaintext captures the
converter judges, so those traces say `"converter"` even though the
environment was the recorder's work. **A trace re-converted from such a spool
therefore says `converter` where it used to say `recorder`** — a visible
change to a published key, and the honest one: the digests on its captures
are under the key the CONVERTER held.

Converters re-apply the rule idempotently. The content rule runs on every
path (a marker is a fixed point, and a capture already carrying `redacted` is
skipped); the CALL/LINE name rule runs only for a runtime that did not do it
(Rust wire below 4, `sensorium-ts` below 0.6.0); the RETURN name rule always
runs in Rust, because no Rust runtime has a qualname at its exit probe, and
in TypeScript only for a BOOT older than 0.6.0
(`tests/test_ts_ingest_redaction.py::test_a_capture_the_recorder_already_took_is_carried_through`,
`::test_a_capture_an_older_recorder_left_in_plaintext_is_taken_here`,
`tests/fixtures/rust-spools/redacted-values`).

### The Rust spool's plaintext window

The Rust runtime applies the NAME rule to a LINE delta at its own writer —
wire v4's tag 4 carries the digest where the text was — and nothing else. It
has no regex engine, so between the runtime and the converter the spool under
`<target>/sensorium/spool/` holds **content-plaintext**: a token inside a
struct's `Debug` rendering, and `get_token()`'s return, which no runtime
judges. Those files are `0600` and a `cargo clean` takes them, but the window
is real and is named here rather than left to be discovered
(`rust/README.md`, "Where traces go"; `rust/HONESTY.md` §14).

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
redaction: rule v1, keyed (key 0a1b2c3d), by recorder; values redacted: 12
redaction: rule v1, keyed (key 0a1b2c3d), by recorder (key mode 0644 -- expected 0600); values redacted: 12
redaction: rule v1, UNKEYED (no redaction.key in the store); by recorder; values redacted: 12
redaction: OFF (SENSORIUM_NO_REDACT) -- the environment and every captured value are stored in plaintext
redaction: none -- recorded before redaction existed; plaintext throughout
```

The mode note rides the keyed form only when the store's key is loose AND is
the key that took THESE digests — a note about some other store's file
permissions would send a reader to the wrong file. The `values redacted:`
clause rides the two forms the rule actually RAN under, and only where the
writer counted: a recording made before the count existed carries no `values`
key, and a zero invented for it would be a measurement nobody made. The two
forms the rule did not run under say in words that nothing was taken. Vectors
`v42-redaction-render` and `v42b-redaction-none` pin the lines in the format;
`tests/test_info_redaction.py` pins each form and its placement
(`::test_the_keyed_line_counts_the_values_the_rule_took`,
`::test_a_measured_zero_is_printed_rather_than_left_out`,
`::test_a_recorder_that_never_counted_says_nothing`,
`::test_the_clause_never_rides_a_rule_that_did_not_run`).

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

Everything a recorder CREATES under the store and the spool directories
from this version on is `0600`, and every directory it creates there is
`0700` — by explicit mode at creation, never by a later `chmod`, because a
file created `0644` and tightened a moment later is readable for exactly the
moment it is being filled with what it holds. That covers the trace, the
store root, `traces/`, `redaction.key`, `invocations.jsonl`, the Rust spool
directory and its `<pid>.proc.json` / `.spool` / `<pid>.runner.json`, and
the TypeScript spool
(`tests/test_record_redaction.py::test_created_files_are_0600_and_dirs_0700`;
`rust/cargo-sensorium/tests/convert_e2e.rs::check_modes` asserts the same
end to end over a real invocation).

**What this does NOT cover**, and what stays at the platform default: the
Rust build tree under `<target>/sensorium/` — `mirror.rs`, `rt_build.rs` and
`fallback.rs`'s `manifests/`, and **the mirror holds a copy of your source** —
and `ts/wrapper.py`'s files under the user's `node_modules`. They hold no
environment and no digests, but they are not `0600`, and they are named in
`docs/CARRIED-DEBT.md` as outside this version's promise.

A file or directory that **already exists** keeps the permissions its owner
chose: a person who pointed `SENSORIUM_DIR` at a directory of their own is
not overruled. **Windows** has no POSIX mode bits; every number here is
advisory there.

## The honest limits

- **A name this set has never heard of is stored as typed**, and so is a
  secret in a variable called `x`. `SENSORIUM_REDACT_NAMES` is the remedy,
  and it is recorded.
- **A secret matching none of the nineteen content patterns is stored as
  typed.** The list is a floor, not a scanner. The rule also sees the CLIPPED
  text rather than the value the program had, so a secret that BEGINS near
  the 200-byte cap can leave a fragment shorter than every pattern's minimum
  length — which then matches nothing, and is stored as typed.
- **An output chunk is scanned one `write()` at a time.** A token split
  across two writes is not seen: the tee holds no state between writes, and
  one that did would be a buffer of the program's output living inside the
  instrument.
- **The recorded program's OWN command line is stored in plaintext.** A
  secret passed to it on the command line is in the trace, in `meta.argv` and
  in the Rust proc header, and no part of rule v1 reaches it. The command
  lines of the processes it SPAWNS are covered differently rather than not at
  all: each element of `meta.children` takes the CONTENT rule at the audit
  sink and counts into `values` (ruling R25), so a shape the patterns know is
  replaced where it stands — but a command line has positions rather than
  bindings, so there is no name to ask about and the NAME rule never runs on
  one.
- **A `?`-hop RAISE's message in Rust is the probe's own read of the error**,
  not the returned value, so it takes the content rule like any other message
  and is never withheld whole by the qualname that took the RETURN.
- **A spool converted against a store that did not record it** carries the
  recorder's `key_id` in `redaction` while the CAPTURE digests the converter
  took are under the ingesting store's key. On one box those are one key; a
  spool carried elsewhere makes them two, and nothing in the trace says so.
- **`exceptions` counts an origin message as one of a SET.** The message is
  deliberately not in a group's key (`query/exceptions_group.py`: Rust's is
  `(tag, site, masked verdict, route)`, TypeScript's
  `(disposition, reason, site, masked verdict, route)`); it rides in
  `shape.messages`, and a group whose members differ there prints
  `messages: N distinct (first shown)`. Two messages identical after
  redaction therefore drop that N by one. On the Python side an exception's
  identity is its `serial`, which redaction never touches; only the legacy
  `(type, msg, oid)` fallback for traces recorded before serials existed
  reads the message at all.
- **A digest is guessable for a low-entropy value** by anyone holding the key
  file. See "The key, and what a digest is" above.
- **Digests compare within one language.** A non-UTF-8 environment value
  digests differently in Python — which hashes the surrogateescaped byte
  `os.environ` handed it
  (`tests/test_redact.py::test_digest_hashes_surrogateescaped_bytes`) — and
  in Rust and TypeScript, which hash the U+FFFD they stored in its place.
  This is the same per-recorder rule `env_hash` already carries in
  [`TRACE-FORMAT.md`](TRACE-FORMAT.md) §4, for the same reason.
- **A trace that predates the rule holds plaintext until `sensorium redact`
  is run over it**, which is the retrofit the next section describes.

## The retrofit: `sensorium redact`

The rule is at the three recorders' writers; `redact` is what reaches the
traces already on disk, doing to each what a recorder would have done at birth:

    sensorium redact last              # one trace
    sensorium redact --all             # every trace in this store
    sensorium redact --all --dry-run   # what it would take, written nowhere

One flushed line per trace in sorted run-id order, then one summary:

```
run 20260916-093012-a1b2c3: env 2 redacted (GITHUB_TOKEN, SLACK_TOKEN); values 12; mode 644 -> 600
run 20260916-094155-c3d4e5: nothing to redact; mode 600
run 20260916-095001-e5f607: in flight (incomplete), skipped
run 20260916-095744-071829: REFUSED: env_hash does not reproduce under the python formula
redacted 1 of 4 traces (1 already clean, 1 skipped, 1 refused); spools under target/ and the TypeScript spool dirs are not reached
```

Names are capped at eight and then counted, `info`'s own cap; the lines are
pinned to the character in `tests/test_redact_cmd.py`. Exit **0** when
something changed or would, **1** when nothing needed doing, **2** when a trace
was refused — the others still ran, and a judgement that RAISES is a refusal
too (`REFUSED: cannot judge: …`) and not a traceback (ruling R10).

- **What one pass takes.** The environment takes the NAME rule alone, never the
  content rule; the values are exactly what the writers reach — `args`/`deltas`
  bindings by name, a map sample's value under its key, a RETURN under its
  callee's last qualname segment, messages, `unwind_exc`, `output` rows and
  `meta.children`; `argv`, `cwd` and `source_hashes` stay.
- **`env_hash` is reproduced before it is recomputed**, under that trace's own
  formula (JSON for Python, the sorted `k=v` join for Rust and TypeScript): a
  pass that cannot reproduce the OLD hash refuses the trace by name.
- **The knobs are the CALLER's** — `SENSORIUM_REDACT_NAMES` and
  `SENSORIUM_REDACT_ALLOW` read from the environment `redact` itself runs in,
  and stamped. **`SENSORIUM_NO_REDACT` is ignored**: running the command IS the
  decision, `mode` is always `on`, and the judgement forces the knob off.
- **A second pass takes nothing**: a name already in `redaction.env` keeps its
  digest and marker; only one absent from it that fires now is taken. A trace
  keyed under ANOTHER key is refused (`digests under key <id>, the store's is
  <id>; nothing rewritten`); an UNKEYED one becomes keyed under a keyed store.
- **`by: "retrofit"`, and an ADDITIVE `values`**: `info` reads `by retrofit`
  rather than `by recorder`, and the count is the previous stamp's plus this
  pass's — a content hit leaves text, not a marker, so it cannot be recounted.
- **The rewrite is a copy; the original is whole until one rename.**
  `Connection.backup` into `.<run>.db.redact.<pid>.tmp` (`O_EXCL`, 0600 — a
  byte copy would lose committed rows still in the `-wal`), one transaction,
  `TRUNCATE` checkpoint, fsync, rename, directory fsync. The ORIGINAL's
  `-wal`/`-shm` go LAST, or SQLite recovers that plaintext log over the
  redacted database. A kill leaves the original whole and a tmp, swept by the
  next pass once that pid is dead and refusing the trace while it lives — also
  how two `--all` passes stay apart.
- **An in-flight trace is skipped, never raced**: one still marked `incomplete`
  is open in WAL mode elsewhere, and `.<run>.db.tmp` files are never walked.
- **Modes.** A rewritten trace is 0600 by creation; one needing no rewrite but
  at another mode is tightened in place with its sidecars and counts as
  CHANGED. `--all` also tightens `traces/` to 0700 and says so — itself a
  change, so a pass that tightened it and redacted nothing still exits 0
  (ruling R11); `redact <run>` never touches the directory.
- **The stale key tmp sweep** runs once per invocation, before any trace: every
  `redaction.key.<pid>.tmp` whose writer is dead — 32 bytes of a secret nobody
  will finish writing (ruling R15) — is unlinked and counted.
- **`--dry-run` prints the real run's stdout, byte for byte** — same lines,
  summary, order and exit, with `dry run: nothing was written` on STDERR — for
  it runs the judgement alone, the function the real pass applies. Two corners:
  an unkeyed store's dry run READS a key where a real run MINTS one, so the
  other-key refusal says `none` in the first and a key id in the second; and
  the sweep is real in both modes, so a dry run consumes litter a later real
  run would have counted. It also opens each trace read-write to judge it — a
  WAL database needs a writable `-shm` even to read — so SQLite may leave a
  `-wal`/`-shm` beside a trace whose CONTENT nothing touched.
- **What it does not reach**: the spools (named on every summary rather than
  left out of its count), another store, `invocations.jsonl`, the recorded
  command line, whatever else the limits above place outside rule v1. It never
  re-keys a store, and nothing reverses it.
