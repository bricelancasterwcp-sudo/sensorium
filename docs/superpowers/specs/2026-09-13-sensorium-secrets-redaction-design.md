# Secrets redaction — rule v1, the store key, file modes, `sensorium redact`, and E16

**Date:** 2026-09-13 · **Status:** design, approved in conversation (Brice,
2026-09-13: all three scopes — "Env + file modes", "Also captured bindings by
name", "Also retrofit existing traces"; approach 1 "yes"; sections 1–4
"approved") · **Design authority:** Claude · **Base:** main `7dd25d2`
(Python 0.14.0; `sensorium-ts` 0.4.0; crates rt 0.5.0 / transform 0.5.0 /
driver 0.6.0), with PR #39 (relicense) pending beside it · **Branch:**
`docs/secrets-redaction-design` (this document and its plan), then
`feat/redaction-a`, `feat/redaction-b`, `feat/redaction-c` for the three PRs
of §1.

The finding this slice answers, read off main the same day: every recorder
stores the **entire process environment in plaintext** — the Python recorder
at `record/boot.py::_write_run_meta`, the Rust runtime at
`sensorium-rt/src/spool.rs::sorted_env`, the TypeScript runtime in the BOOT
record of `typescript/src/rt.mjs` — and every converter passes it through.
Trace files are created with the process umask (0644 on a default Linux
setup), the TypeScript ingest hardcodes 0644, and there is no redaction pass;
the README's "What a trace file holds" says exactly this. The 273 traces in
this box's `~/.sensorium/traces` each carry `CLAUDE_CODE_MESSAGING_TOKEN`
in plaintext at 0644. Captured argument, local and return values are clipped
by length and never filtered by content, so an `api_key=` argument is stored
as typed.

The same day sensorium's direction changed: the repository went private, is
being relicensed (PR #39), and is to be offered as a hosted MCP service for
companies with a free tier for individuals. A hosted trace store cannot hold
plaintext credentials, so this slice is a prerequisite of that product, not
a feature of it. The question "would redacting at the MCP layer keep the data
pure?" was asked and answered in the same conversation: no — the store would
be the liability, the CLI path (the debugging skills read the CLI directly)
would bypass it, and a presentation filter protects against one reader
only. The MCP layer owns *policy* (tenant name lists, whether the
environment is ever shown, audit) on top of a store that is already clean.
That is §11's first entry, not this slice.

## 0. Rulings this design rests on

- **Scope (Brice, 2026-09-13):** all three — environment redaction with
  file modes, captured bindings by name, and a retrofit for existing traces.
- **Where the rule runs (approved):** at the WRITER, in every recorder,
  before anything reaches disk (approach 1). Converters re-apply the rule
  idempotently for spools written by an older runtime. Not at the MCP or
  presentation layer, for the reasons above.
- **Default on.** Enterprise users are the stated audience; a leak that
  requires opting *in* to close is a leak. One knob turns it off per run and
  the trace says so when it is off (§4.3).
- **Keyed digests, not bare hashes (Claude).** A redacted value keeps an
  equality identity so `refocus` and `diff` can still say "changed" without
  printing it, and that identity is an HMAC under a per-store key — a bare
  truncated SHA-256 of a password is dictionary-crackable, which a security
  reviewer would flag first.
- **`seal` mode reserved, not built.** Reversible encryption under the same
  store key plus a `sensorium reveal` for the developer at their own machine
  is the answer to "I want the plaintext back locally". The key exists
  after this slice so the door is open; §11.
- **The three-PR shape (approved):** one spec, one plan, three PRs so each
  lands on its own (§1).
- **Design authority:** every question below that is not scope, merge,
  money or a destructive action was Claude's to decide and is recorded here
  as decided, with the reason.

## 1. What ships

| PR | Branch | Contents |
|---|---|---|
| A | `feat/redaction-a` | The rule module in each language (§2), the key (§3), env redaction in all three recorders (§5.1–5.3 env halves), converters' idempotent pass (§5.4), file modes (§5.5), meta `redaction` and `env_hash` over the stored env (§4.3–4.4), `info` and `refocus` (§6.1–6.2), the contract, the shared fixture, vector v43 and the `info` half of v42 (§8), E16 H2, H3, H6 and the env half of H1 (§9). |
| B | `feat/redaction-b` | Captured bindings and output in all three recorders (§5.1–5.3 value halves), Rust wire v4 (§5.2), the `redacted` capture object and its renderers (§4.2, §6.3), `watch` and `flow` (§6.3), the value half of v42 and three corpus cases (§8), the value half of H1 and H5. |
| C | `feat/redaction-c` | `sensorium redact` (§7), H4, the final wording of README and both HONESTY files (§10). |

Each PR carries its own CHANGELOG entry and bumps only what it changed
(§10). PR B depends on A (the key and the meta); C depends on both.

## 2. Rule v1

Rule v1 is one rule with two parts, spelled once in
`docs/trace-format/redaction-v1.json` (§2.5) and implemented three times.
The number is the rule's identity: a trace says which rule redacted it, and
a later rule is v2, never an amended v1.

### 2.1 The name rule

A name is normalised and split: on every run of characters outside
`[A-Za-z0-9]`, and on every camelCase boundary (a lowercase or digit
followed by an uppercase, and an uppercase run followed by uppercase +
lowercase, so `HTTPToken` → `HTTP`, `Token`). Every segment is uppercased.
The rule **fires when any segment is in this set**:

```
KEY APIKEY TOKEN SECRET SECRETS PASSWORD PASSWD PASSPHRASE PASS
AUTH AUTHORIZATION CREDENTIAL CREDENTIALS CREDS PRIVATE
COOKIE COOKIES SIGNATURE BEARER JWT DSN ACCESSKEY SECRETKEY AUTHTOKEN
```

Fires: `API_KEY`, `apiKey`, `accessToken`, `DATABASE_DSN`, `oauth_token`,
`SSH_AUTH_SOCK`, `GPG_KEY_ID`, `password`, `get_api_key`. Does not fire:
`KEYBOARD`, `KEYRING`, `authorId`, `OAUTH_URL` (segments `OAUTH`, `URL`),
`XAUTHORITY` (one segment), `PWD`, `OLDPWD`, `SESSION_MANAGER`,
`DBUS_SESSION_BUS_ADDRESS`, `PATH`, `HOME`. The false positives that do fire
(`SSH_AUTH_SOCK`, `GPG_KEY_ID`: paths and ids, not secrets) cost a plaintext
path in a trace and nothing else: the digest keeps the value comparable,
`refocus` names variables rather than printing them, and the allowlist
(§2.4) is the remedy for a name a user knows is not a secret. Matching is segment-exact, never substring, because
substring `KEY` would fire on `MONKEY_PATCH` and substring `PASS` on
`BYPASS_CACHE`; the fixture pins both directions.

### 2.2 The content rule

A fixed list of patterns, each with a minimum length so a short benign
string cannot fire. The list is a **floor**, and every document that
mentions it says "not a secret scanner". v1:

| Pattern | Shape (regex, case-sensitive unless noted) | Span replaced |
|---|---|---|
| URL userinfo password | `://[^/\s:@]{1,64}:([^@\s/]{1,256})@` | group 1 |
| PEM private-key block | `-----BEGIN [A-Z ]*PRIVATE KEY-----` through the matching `-----END … PRIVATE KEY-----`, or to end of text when truncated | the body between the two lines |
| Authorization header value | `(?i)\b(Bearer\|Basic)\s+([A-Za-z0-9._~+/=-]{16,})` | group 2 |
| JWT | `eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}` | whole match |
| Anthropic / OpenAI / Stripe keys | `\bsk-ant-[A-Za-z0-9_-]{20,}`, `\bsk-[A-Za-z0-9_-]{20,}`, `\b(sk\|rk)_(live\|test)_[A-Za-z0-9]{16,}` | whole match |
| GitHub / GitLab | `\bgh[pousr]_[A-Za-z0-9]{20,}`, `\bgithub_pat_[A-Za-z0-9_]{20,}`, `\bglpat-[A-Za-z0-9_-]{20,}` | whole match |
| Slack | `\bxox[abprs]-[A-Za-z0-9-]{10,}` | whole match |
| AWS / Google | `\b(AKIA\|ASIA)[0-9A-Z]{16}\b`, `\bAIza[0-9A-Za-z_-]{35}\b` | whole match |
| Hugging Face / npm / PyPI / DigitalOcean / Shopify / SendGrid | `\bhf_[A-Za-z0-9]{20,}`, `\bnpm_[A-Za-z0-9]{20,}`, `\bpypi-[A-Za-z0-9_-]{20,}`, `\bdop_v1_[a-f0-9]{20,}`, `\bshpat_[a-f0-9]{20,}`, `\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}` | whole match |

Every pattern in the fixture has at least one positive and one negative
case (a `sk-` 8 characters long; `Bearer` followed by the word `token`;
`eyJ` alone). The list is the same text in all three implementations —
Python `re`, JavaScript `RegExp`, and the `regex` crate in the Rust
converter (§5.2 says why the converter and not the runtime) — and the
fixture is what proves the three agree, pattern by pattern.

### 2.3 Two operations, decided by what fired

- **A name hit redacts the WHOLE value and keeps a digest.** The value has
  an identity worth comparing: two runs whose `API_KEY` differs are two
  different worlds, and `refocus` must be able to say so. For an
  environment variable the digest is over the variable's whole plaintext
  value; for a captured binding, over the capture's text as it would have
  been stored (the clipped `str`/`repr`/`dbg` text), so the digest is of
  what the trace would otherwise have held and nothing longer.
- **A content hit replaces the MATCHED SPAN inside text and keeps no
  digest.** A repr, a `Debug` rendering, a log line or a URL is not a value
  with an identity; it is text that happened to contain one. Replacing the
  span keeps everything around it (`postgres://u:<redacted>@h/db`), which
  is what a person debugging a connection string needs, and a partial
  cannot honestly carry a digest of the whole.
- **Environment values are the one exception to "no digest on content":**
  an env value redacted by span still records a digest of its whole
  plaintext in `redaction.env` (§4.3), because `refocus`'s environment
  clause compares values by name and must not go blind on `DATABASE_URL`
  merely because the rule chose the span operation there.
- **Allow wins.** A name in `SENSORIUM_REDACT_ALLOW` is subject to neither
  operation, whatever its content. That is the user's statement about
  their own variable, recorded in `redaction.allow` so a reader of the
  trace knows a plaintext `API_KEY` there was asked for.

### 2.4 The knobs

Three environment variables, read once at record time by every recorder
(and by the drivers, which pass them on unchanged), recorded in
`redaction` (§4.3) so the trace says what it was recorded under:

| Variable | Reading | Precedent for the spelling |
|---|---|---|
| `SENSORIUM_NO_REDACT` | Any non-empty value other than `0` turns the whole rule off for that recording; `=0` leaves it on. | `SENSORIUM_NO_INVOCATION_LOG` in this repo, `NO_COLOR` outside it. |
| `SENSORIUM_REDACT_NAMES` | Comma-separated exact names (env variables or binding names) that fire the name rule in addition to the segment set. Compared after the same normalisation (case-insensitive, segments joined), so `myco_dsn` and `MYCO_DSN` are one name. | comma lists in `no_proxy`, `PYTHONWARNINGS`. |
| `SENSORIUM_REDACT_ALLOW` | Comma-separated exact names that never fire, name rule or content rule. Wins over `SENSORIUM_REDACT_NAMES`. | "allowlist" is the word every scanner uses. |

No flag on the CLI: `sensorium run` records the environment it was launched
in, and the knob belongs to that environment like `SENSORIUM_DIR` does. The
knobs themselves are recorded like any other variable — none of the three
names fires the rule (`REDACT` is not a segment in the set), which the
fixture pins, because a knob that redacted itself would hide what the run
was recorded under.

### 2.5 The fixture

`docs/trace-format/redaction-v1.json`: a list of cases, each `{"name":
<string or null>, "value": <string>, "expect": {"op": "whole" | "span" |
"none", "by": "name" | "content" | null, "text": <the stored text after
the operation, or null when "whole">}}`, plus a `"split"` list of `{"name",
"segments"}` pairs pinning the normaliser. Every segment in §2.1 has a
firing case and a near-miss; every pattern in §2.2 has a positive and a
negative; the three knob names appear as non-firing names; the allowlist is
exercised through a case with `"allow": true`. All three suites load the
same file — `tests/test_redact.py`, `sensorium-rt`'s and
`cargo-sensorium`'s `#[test]`s (the rt tests the name rule and the
digest; the converter tests the content rule), and
`typescript/test/redact.test.mjs` — and each rule line is mutation-tested
against it in the plan: delete or invert the line, the fixture case for it
must fail, restore.

## 3. The key and the digest

- **`<trace root>/redaction.key`**, beside `traces/`: 32 bytes from the
  OS random source, created once with `O_CREAT|O_EXCL` at 0600 by
  whichever sensorium process first needs it; a loser of that race reads
  the winner's file. Never copied into a trace, a spool, a header or the
  invocation log.
- **Digest** = `HMAC-SHA256(key, plaintext bytes)`, first 16 hex characters.
  The plaintext bytes are UTF-8 of the string as the recorder holds it (a
  Rust env value read lossily is hashed as the lossy string it recorded).
  64 bits is an equality identity, not a commitment: two equal values in
  one store share it, and without the key, reversing a digest means
  guessing the key.
- **`key_id`** = `SHA-256(key)`, first 8 hex. Stamped in `redaction.key_id`
  so two traces can tell whether their digests are comparable at all
  (§6.2).
- **How each runtime gets it.** The Python recorder reads the file
  in-process. The Rust driver (`cargo sensorium`) and the TypeScript driver
  (`sensorium ts run`) create-or-read it and pass the hex to the recorded
  process as `SENSORIUM_REDACT_KEY`; the runtime reads it at boot and
  **removes it from the environment it records** (the one variable a
  recorder deletes rather than redacts, because a digest of the key under
  the key is a pointless row and the variable's presence is already
  implied by `keyed: true`). `is_recorder_key` in both `refocus` branches
  learns the name so a re-run never reports it as a world change.
- **No key.** A store where the file can neither be created nor read (a
  read-only store, a permissions accident) records `keyed: false`, every
  digest is `null`, and the values are still redacted — the fallback loses
  comparability and never loses safety. `refocus` then names the redacted
  variables as unverifiable (§6.2). A key file that exists with a mode
  other than 0600 is read anyway and named on `info`'s `redaction:` line
  (`key mode 0644 -- expected 0600`), because refusing to record over the
  user's own file permissions helps nobody.
- **Windows** has no mode bits the way POSIX does; the key is created with
  the platform default and the docs say so (§5.5).

## 4. Markers and the trace shape

### 4.1 The environment

`meta.env` stays a string-to-string map — every reader that assumes so is
unchanged. A whole-redacted value is the literal `<redacted>`; a
span-redacted value is the text with each matched span replaced by
`<redacted>` (`postgres://u:<redacted>@h/db`). Which names were touched, and
their digests, live in `redaction.env` (§4.3), not in the values: a reader
that wants to know whether a value is a marker or a literal string asks the
table, never parses the value. The angle-bracket spelling is the one this
repo's renderers already use for withheld things (`<unread>`,
`<unreadable T#n>`, `<not in scope>`) and the one every log redactor a
reader has seen uses.

### 4.2 A captured value

A capture keeps its tag and gains one optional key:

```
{"k": "str"|"dbg"|"obj"…, "v"|"repr": <text>, …,
 "redacted": {"by": "name"|"content", "digest": <16 hex>|null}}
```

- **By name** (whole): `v` (or `repr`) is the literal `<redacted>`, `trunc`
  is absent, `digest` is the digest of the text that would have been
  stored (§2.3), or `null` when unkeyed.
- **By content** (span): `v` is the text with the span(s) replaced,
  `trunc` is whatever the clip said, `digest` is `null`.
- `fmt_value` renders a whole-redacted value as `<redacted #abcd1234>`
  (the digest's first 8 hex — `#` is the spelling `obj#oid` already uses
  for "identity of this thing", and it means the same here: two equal
  markers are two equal values) or `<redacted>` when there is no digest; a
  span-redacted value renders as its text, marker included.
- **Graceful on an old reader.** A 0.14.0 reader that meets this object
  ignores the key and prints `'<redacted>'` for a str — a string, quoted,
  and nothing leaks. That is why the tag is kept and not replaced by a new
  one: a new `k` would render `?` there, which reads as a value that could
  not be read.
- Containers: a `map` sample whose key is a captured `str` that fires the
  name rule has its paired value capture whole-redacted (`{"api_key": …}`,
  a headers dict); a `seq` has no names and gets only the content rule
  through its elements.

### 4.3 The meta key `redaction`

One shared optional key (TRACE-FORMAT §4's "written by every recorder,
read with defaults" set), written by every recorder from PR A on:

```
{"rule": "v1", "mode": "on",
 "keyed": true, "key_id": "0a1b2c3d",
 "env": {"CLAUDE_CODE_MESSAGING_TOKEN": "9f2c…", "DATABASE_URL": "…", …},
 "names": ["MYCO_DSN"], "allow": ["KEY_PRESSED"],
 "by": "recorder", "values": 12}
```

- `env`: every environment name the rule touched, whole or span, with its
  whole-value digest (or `null`). This map is the list of names; there is
  no second list to drift from it.
- `names` / `allow`: the two knobs as read, split; `[]` when unset.
- `by`: `"recorder"` (the runtime did it), `"converter"` (a converter
  applied the rule to a spool from a runtime that had not), `"retrofit"`
  (`sensorium redact` rewrote a stored trace). One value: the LAST hand
  that applied the rule, because a retrofit re-applies the whole rule and
  the earlier stamp adds nothing a reader can act on.
- `values`: the number of captured values (args, deltas, returns, output
  rows, map values) redacted by either operation — a witness count, so
  `info` can print it and a zero is a measured zero. Absent from PR A's
  traces, which redact no values yet; `info` reads it with `.get`.
- **Mode off:** `{"rule": "v1", "mode": "off"}` and nothing else — the
  environment and every value are plaintext, `env_hash` is over that
  plaintext, and `info` says so in words (§6.1).
- A trace with **no `redaction` key at all** predates this slice, holds
  plaintext, and every reader treats it as `mode: "off"` without the stamp
  — the same three-way reading `Trace.declares` already makes for
  capabilities: absent, declared off, declared on.

### 4.4 `env_hash`

Computed over the environment **as stored** (each language's own formula,
unchanged — `json.dumps(env, sort_keys=True)` in Python, the sorted
`k=v` join in Rust and TypeScript). A reader can therefore recompute it
from the trace, which was never true of a hash over plaintext the trace
does not hold. Nothing compares `env_hash` across traces today (`info`
prints it; `refocus` compares `env` by name), so nothing changes meaning.
The retrofit recomputes it the same way (§7).

## 5. Where it runs

### 5.1 Python

- `src/sensorium/redact.py`, new, pure, no imports from `record` or `query`:
  `split(name) -> list[str]`, `fires(name, names, allow) -> bool`,
  `content(text) -> tuple[str, bool]` (text after span replacement, and
  whether anything matched), `Key` (load-or-create, `digest(text)`,
  `key_id`), `env(environ, key, knobs) -> tuple[dict, dict]` (the stored
  env and the `redaction.env` table), `named(name, capture, key, knobs)
  -> dict`, `text_capture(capture) -> dict`, and `Knobs.from_environ()`.
  Under ~250 lines; the patterns are one table at the top.
- `record/boot.py::_write_run_meta`: `env, table = redact.env(dict(os.environ), key, knobs)`;
  writes `env`, `env_hash` over `env`, and `redaction`. The key is loaded
  once at boot, before the program runs, so a program that `chdir`s or
  rewrites `SENSORIUM_DIR` cannot move it.
- `record/tracer.py`: the CALL's `{n: capture_value(loc[n])}` becomes
  `{n: redact.named(n, capture_value(loc[n]), …)}`; LINE deltas the same
  per name; the RETURN's value runs the name rule against the callee's
  last qualname segment (`get_api_key` → `GET`, `API`, `KEY` fires), then
  the content rule. `capture_value` itself applies the content rule to
  every `str` and `repr` text and, in the map sampler, the name rule to a
  paired value whose key is a firing `str`. Output: the tee in `boot.py`
  runs `redact.content` on each chunk before `add_output` — a `print(token)`
  is output, and H1 (§9) would fail without it. The cost of all of this is
  H5's number.
- `SENSORIUM_REDACT_KEY` is not used by the Python recorder (in-process
  read), but if present it is deleted from the recorded env like the
  runtimes do, so a Python program launched by a TypeScript harness under
  `sensorium ts run` does not record the TypeScript driver's key.

### 5.2 Rust

- `sensorium-rt/src/redact.rs`, new, zero dependencies like the rest of
  the crate: the normaliser and the segment set, `fires`, an HMAC-SHA256
  over the crate's own `sha256.rs`, `digest`, `key_id`, and
  `redact_env(Vec<(String,String)>) -> (Vec<(String,String)>, Vec<(String,String)>)`
  (the stored env, and the name→digest table). The runtime reads
  `SENSORIUM_REDACT_KEY`, `SENSORIUM_NO_REDACT`, `SENSORIUM_REDACT_NAMES`,
  `SENSORIUM_REDACT_ALLOW` at boot, removes the key variable from
  `sorted_env()`'s result, and writes into the proc header three new
  siblings of `env`: `"env_redaction": {name: digest|null}`,
  `"redaction": {"rule": "v1", "mode", "keyed", "key_id", "names",
  "allow"}`. The **name rule only** runs in the runtime: it needs no
  regex, and the crate stays dependency-free.
- **LINE deltas**, in `line()` where the closure's `(name, Capture)` pairs
  are iterated: a firing name's `Capture` is written with a new value tag.
  **Wire v4** — verbatim, the converter is written against it:

  ```text
  file header:  b"SNSR" u8 version=4 …   (everything else as v3)
  value block:  u8 tag (0 = no value, 1 = debug text, 2 = unread,
                        3 = REDACTED BY NAME) u8 truncated (0 on tag 3)
                tag 3's text is the 16-hex digest, or empty when unkeyed
                (LINE: u16 text_len then text; RETURN: the rest)
  ```

  Tag 3 appears on LINE rows only. It never appears on a RETURN on the
  wire, because the runtime does not know a site's function name (that is
  manifest data); the converter applies the RETURN name rule itself, below,
  and writes the result straight into the trace. The converter reads v2,
  v3 and v4; a converter older than PR B meeting a v4 header refuses
  the spool by version exactly as it refuses an unknown version today.
- **`cargo-sensorium/src/convert/redact.rs`**, new, takes the `regex`
  crate: the content rule over every `dbg` text (deltas, returns, err
  messages), span replacement and the `redacted: {by: "content"}` flag;
  the RETURN name rule against the site's qualname from the manifest
  (whole, digest under the key the driver hands the converter); and the
  full rule over the header's `env` when the header carries no
  `redaction` object (an rt older than PR A), stamped `by: "converter"`.
  `convert/meta.rs::build` emits `redaction`. **Consequence, stated in
  `rust/README.md` and `rust/HONESTY.md`:** between the runtime and the
  converter the spool under `target/` holds content-plaintext (a token in
  a struct's `Debug` text, `get_token()`'s return) at 0600 — never a
  name-hit delta and never an environment value, which the runtime already
  redacted. H1's Rust arm asserts exactly that split.
- The driver: `runner.rs` / the invocation path create-or-read the key and
  set `SENSORIUM_REDACT_KEY` for the test binary; the converter is handed
  the same key in-process. The driver passes the three knobs through
  untouched.

### 5.3 TypeScript

- `typescript/src/redact.mjs`, new: the normaliser, `fires`, the content
  rule as `RegExp`s, HMAC via `node:crypto`, `redactEnv`. The runtime
  reads the four variables at boot, deletes the key variable from the BOOT
  record's `env`, and writes `envRedaction` and `redaction` beside it.
- `captures(pairs)` applies the name rule per name (CALL args and LINE
  deltas both come through it); `ret(f, v)` applies it against the frame's
  code name (the runtime has it: `file(rel, abs, codes, sha)` registered
  the names); `dbg()` in `dbg.mjs` applies the content rule to its text.
  The `Captured` typedef gains the optional `redacted` object; the wire
  stays **v1** — a JSON object with one more optional key is additive, and
  an ingest older than PR B drops the key and keeps the marker text, which
  leaks nothing.
- `src/sensorium/ts/build.py::_meta` maps `envRedaction`/`redaction` to
  the meta key and, for a BOOT with no `redaction` object (an rt older
  than PR A), applies the Python rule to `env` and stamps
  `by: "converter"`. `ts/driver.py::_harness_env` sets
  `SENSORIUM_REDACT_KEY` beside the other recorder variables and
  `refocus_typescript.is_recorder_key` learns it.

### 5.4 Converters re-apply, idempotently

A converter that meets a header or BOOT already carrying `redaction` with
`mode: "on"` trusts it and does not re-run the env rule (the plaintext is
gone; there is nothing to run it on). `mode: "off"` is preserved as off —
a converter does not overrule the recording's own knob, and the trace says
off. A marker is never re-redacted: `<redacted>` contains no firing
segment and matches no pattern, and the fixture has a case saying so.

### 5.5 File modes

Every file this slice's writers CREATE is 0600 and every directory 0700,
by explicit mode at creation, never by `chmod` afterwards:

| Writer | Today | After |
|---|---|---|
| `store/db.py::create_trace` | `sqlite3.connect` under the umask | the file is pre-created `O_CREAT\|O_EXCL\|0o600` and handed to sqlite, the way `ts/ingest.py` already pre-creates its tmp; `-wal`/`-shm` inherit the database file's mode (SQLite's unix VFS copies it) |
| `paths.traces_dir()` | `mkdir(parents=True)` | `mode=0o700` on creation; an existing directory is not touched |
| `ts/ingest.py` | `0o644` hardcoded | `0o600` |
| `invocations.py` | `open("a")` | pre-created 0600 when absent |
| `sensorium-rt` spool files, proc header tmp | `OpenOptions`/`File::create` | `.mode(0o600)` (unix) |
| `sensorium-rt` spool dir, `runner.rs` record | `create_dir_all` / `fs::write` | `DirBuilder.mode(0o700)`; `OpenOptions.mode(0o600)` |
| `convert/sqlite.rs::TraceWriter::create` | `Connection::open(tmp)` | tmp pre-created 0600, then opened |
| `rt.mjs` spool | `appendFileSync` / `mkdirSync` | `{mode: 0o600}` / `{mode: 0o700}` |

Existing files and directories are left as they are — changing a user's
store permissions behind their back is the retrofit's job, done when asked
(§7). Windows treats every mode as advisory; the README says so in the
"What a trace file holds" rewrite (§10) rather than pretending.

## 6. The query side

### 6.1 `info`

The `env:` field grows: `env:3c2cfb29 (120 vars, 2 redacted:
CLAUDE_CODE_MESSAGING_TOKEN, SSH_AUTH_SOCK)` — names only, first
eight then `+N more`, the cap `refocus_world._shown` already uses. A new
line after `caps:`:

```
redaction: rule v1, keyed (key 0a1b2c3d), by recorder; values redacted: 12
redaction: rule v1, UNKEYED (no redaction.key in the store); by recorder
redaction: OFF (SENSORIUM_NO_REDACT) -- the environment and every captured value are stored in plaintext
redaction: none -- recorded before redaction existed; plaintext throughout
```

`values redacted:` is printed only when the key is present (PR B on).
Vector v42 pins all four lines.

### 6.2 `refocus`

`_env_diff` (`refocus_world.py`) learns the tables. For each name on
either side:

| Original | Re-run | Comparison |
|---|---|---|
| digest, key K | digest, key K | digests; a mismatch is a difference and withholds exactly as a changed variable does today |
| plaintext (older trace or allowlisted) | digest, key K | the plaintext's HMAC under the store's key when `key_id == K`; else unverifiable |
| digest, key K | digest, key K′ | unverifiable: `redacted, not comparable (different keys)` |
| digest `null` (unkeyed) | anything | unverifiable: `redacted, not comparable (unkeyed)` |

Unverifiable names go on a sixth list from `_env_diff`, printed on the env
line and stamped in `refocus_licence_unverifiable` alongside the checks
that could not run — **not** withholding, per the rule `refocus_licence`
already applies to declared-absent output: a check that could not run is
named, and only a difference withholds. `is_recorder_key` in both branches
adds `SENSORIUM_REDACT_KEY`. Vector v43 pins the three outcomes (hold,
withhold, unverifiable) on a Python pair built from meta alone.

### 6.3 `watch`, `flow`, `frame`, `tree`, `grep`

- `watch`: a REDACTED sentinel beside NOT_CAPTURED and TRUNCATED; renders
  `<redacted; no comparable value>`; an expression whose names only ever
  meet redacted values ends in the existing `NOTHING WAS CHECKED`, exit 3.
- `flow --value <lit>` on a binding whose capture is redacted refuses at
  exit 2 in the shape of its primitive refusal: `'token' at e12 is
  redacted (by name); --value cannot follow it`. `flow --object` is
  unaffected (identity, not value).
- `frame`, `tree`, `grep`: `fmt_value`/`fmt_args` render §4.2's markers,
  so a secret's pattern cannot match `grep`'s rendered events — which is the
  point, and vector v42 greps for the planted token and expects 0.
- `diff` compares event streams and `runs` prints meta; neither reads
  values, neither changes.

## 7. `sensorium redact`

```
sensorium redact <run>          one trace
sensorium redact --all          every trace in the store
      [--dry-run]               print what would change; change nothing
```

For each trace: apply rule v1 in full — the env (both operations, digests
under the store's key, `env_hash` recomputed with the trace's own
language formula), every event payload's captured values (name rule on
`args`/`deltas` keys, on map keys, on RETURN by the callee's qualname
segment; content rule on every text), every `output` row — stamp
`redaction` with `by: "retrofit"` (and `mode: "on"`, whatever it was: the
caller asked), and set the file to 0600. The rewrite is **copy → rewrite →
fsync → rename** over the run id's own path, so a killed retrofit leaves
the original whole and the run id unchanged; `-wal`/`-shm` sidecars of the
original are removed with it once the rename has happened.

One line per trace, and the same lines under `--dry-run`:

```
run 20260912-125149-d82847: env 2 redacted (CLAUDE_CODE_MESSAGING_TOKEN, SSH_AUTH_SOCK); values 12; mode 644 -> 600
run 20260912-125137-51a477: nothing to redact; mode 600
redacted 271 of 273 traces (2 already clean); spools under target/ and typescript spool dirs are not reached
```

Exit **0** when anything changed in any trace (or would, under
`--dry-run`), **1** when nothing needed to, **2** on a bad reference or a
trace of a newer format (refused, named, the others continue). A trace
with no `redaction` key is redacted and stamped; one at `mode: "off"` is
redacted anyway and stamped `on` — the knob described the recording, and
the command is a later, explicit decision. Spools are named as out of
reach on the summary line rather than silently skipped. The command is
appended to `invocations.jsonl` like every other, argv only.

## 8. Contract, tests, corpus, census

- **TRACE-FORMAT.md** §4: `redaction` joins the shared optional set;
  the "env … may be withheld for privacy" sentence is rewritten to say what
  is withheld and how the table says so. §5: the `redacted` object joins
  the capture shape, with the old-reader rendering stated. `TRACE_FORMAT`
  stays **4**: no column changes, no new required key, and a 0.14.0 reader
  opens every trace this slice writes and renders every value as a string.
- **Rust wire v4** documented in `spool.rs`'s doc comment (the verbatim
  block of §5.2) and `rust/README.md`; `convert/spool/mod.rs` lists v4 among
  the versions it reads.
- **`docs/trace-format/redaction-v1.json`** (§2.5) read by all three suites.
- **Vectors:** `v42-redaction-render` — PR A writes the four `info` lines;
  PR B adds the `frame`/`tree` markers, `watch`'s sentinel and exit 3,
  `flow --value`'s refusal, and `grep` finding 0 of the planted token —
  and `v43-refocus-redacted-env` (hold / withhold / unverifiable on
  meta-built pairs), PR A's.
- **Corpus:** one case per language — `corpus/secret_in_env` (Python),
  `corpus/rust/secret_in_env`, `corpus/typescript/secret_in_env` — each
  planting `SENSORIUM_CORPUS_TOKEN=tok_corpus_…` (40 chars) in the env and
  a token in an argument, a local, a return value, a header dict and (Python)
  a print. The questions pin `info`'s env line naming the variable,
  `frame` showing `<redacted #…>` for the argument, and — through the
  harness's existing `expect_absent` on every command the case runs — the
  token's text appearing nowhere. The corpus runner sets the variable itself, so the
  case does not depend on the launching shell.
- **The false-positive census** (rigorous-experiments §1: a structural
  comparison, computable in seconds, run before anything expensive):
  `tests/test_redact_census.py` runs rule v1 over every env value and every
  captured text in the four fixture traces and every corpus trace the
  suite builds, and asserts the number of redactions equals the planted
  count exactly — zero on today's traces. A rule that fires on the corpus's
  own benign values fails here before E16 runs.
- **Mutation**: every rule line and every renderer branch is mutation-tested
  in the plan (delete/invert, the pinned test must fail, restore; purge
  `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`).

## 9. E16, pre-registered

Measured once, after PR C, on this box, against the three probe programs
the plan adds under `probes/redaction/{python,rust,typescript}`; each
carries `SENSORIUM_E16_TOKEN` in the environment and receives the same
string as an argument, a local, a return value, a header dict value and
(Python) a `print`. The value is `sk-e16-` followed by 33 random characters
(40 in all), minted by the instrument and never committed: the prefix puts
it inside the content rule's `sk-` pattern, so the cases that carry no
firing name — the header dict in Rust's `Debug` text, Python's `print` —
are reached by content, and a token that only the name rule could see
would measure the name rule twice and the content rule never. The instrument is `tests/acceptance/e16.sh`, dry-run
first on a 4-character decoy to check every artifact path it reads exists.
Both readings are committed here.

| H | Claim | PASS | STOP |
|---|---|---|---|
| H1 | The token's bytes appear in **no file under the store** (`*.db`, `*.db-wal`, `*.db-shm`, `invocations.jsonl`, `redaction.key`) and in no Python or TypeScript spool for any of the three recorders. In the Rust spool it may appear only inside a `dbg` text (content) or a RETURN value block, **never** in a LINE tag-3 block, the proc header's `env`, or any file after conversion. Checked with `grep -c` over raw bytes, per file, before and after conversion. | every count 0 where 0 is required | any non-zero: a missed path. Named, fixed, and the whole of E16 re-measured from zero with a fresh token — an acceptance test of correctness is re-run after a fix, and the record says which run is the first PASS |
| H2 | Every file the three runs created under the store and the spool dirs is 0600; every directory 0700; `redaction.key` 0600. `stat -c %a`, listed per file. | all | any other mode |
| H3 | `refocus` on the Python and Rust probes, token unchanged: licence held, env line names the redacted variable among the compared. Then the token changed between the recording and the re-run (the instrument re-exports it): licence WITHHELD naming `SENSORIUM_E16_TOKEN` as a difference. | both | either the wrong way |
| H4 | `sensorium redact --all --dry-run` on a **copy** of this box's `~/.sensorium/traces` (273 traces) reports every trace holding `CLAUDE_CODE_MESSAGING_TOKEN` plaintext; `sensorium redact --all` on the copy leaves `grep -c <that token's value>` at 0 across every file, every trace still opens (`info` exit 0), and the count line matches the dry run. | all | any residue, any trace that no longer opens, or dry-run ≠ real |
| H5 | Overhead: `corpus/_bench` before PR A and after PR C, same box, n=5 each, the existing harness. Reported as the two medians and the ratio. **Never gated** (rust/HONESTY.md §10: cost is reported, never gated). | n/a | n/a — an outlier ratio is a finding for CARRIED-DEBT, not a stop |
| H6 | The census (§8) on the three probes' traces equals the planted count (env 1, values: Python 5, TypeScript 4, Rust 4 — the Rust probe has no output row and the TypeScript probe no print row) exactly. | exact | any other number: an over- or under-firing rule |

Record: `docs/superpowers/acceptance/<date measured>-sensorium-e16-redaction.md`,
with the per-file grep table, the mode table, the two refocus transcripts,
the dry-run/real pair, the bench numbers and their lens.

## 10. Docs, versions, seams

- **README** "What a trace file holds": the paragraph that says "there is
  no redaction pass" is rewritten to what is true after PR C — what rule v1
  withholds, what it does not (a secret in a variable named `x`; a secret
  the content list does not know; anything under `SENSORIUM_NO_REDACT`;
  everything on Windows' mode bits), and the core-dump sentence kept.
  README is at 796 lines after PR #39; the rewrite must not grow it.
- **`docs/redaction.md`**, new: the rule, the knobs, the key, the markers,
  `sensorium redact`, and the honest limits, in one place; `docs/query.md`
  (797 lines) gains one line pointing to it.
- **`rust/HONESTY.md`** and **`typescript/HONESTY.md`**: one section each,
  "Redaction", promise → falsifier, and a row each in their indexes;
  `rust/HONESTY.md` names the spool's content-plaintext window.
  `typescript/HONESTY.md` is at 795 lines — its section goes in
  `typescript/HONESTY-REDACTION.md` with a pointer, the split
  `HONESTY-COST.md` already made.
- **`docs/trace-format/TYPESCRIPT-KEYS.md`**: `envRedaction`/`redaction`
  under Container.
- **CHANGELOG** entry per PR; **CARRIED-DEBT** appended at each merge.
- **Versions:** PR A — Python **0.15.0**, `sensorium-ts` **0.5.0**,
  `sensorium-rt` **0.6.0** (env redaction in the header), `cargo-sensorium`
  **0.7.0**. PR B — Python 0.16.0, `sensorium-ts` 0.6.0, `sensorium-rt`
  0.7.0 (wire v4), `cargo-sensorium` 0.8.0. PR C — Python 0.17.0. The
  transform is untouched throughout: every probe it emits is unchanged,
  and the redaction happens inside the runtime the probe calls.
- **Seams near the ceiling**, named now: `record/boot.py` 768 (the env
  write is ~15 lines; if the key load pushes it, `record/boot_meta.py`
  takes `_write_run_meta`), `refocus_world.py` 710 (the sixth list goes in
  `refocus_env.py`, which exists for exactly this), `rt.mjs` 798 (the
  knob reads and the BOOT siblings go in `redact.mjs`, not here),
  `spool.rs` 752 (`redact_env` lives in `redact.rs`; `sorted_env` calls it).

## 11. Not in this slice

- **The MCP policy layer** — tenant name lists, whether the environment is
  ever exposed to a model, value-size caps, an audit log of what was shown.
  The product's, on top of a store this slice makes clean.
- **`seal` mode** — reversible AES-GCM under the store key, `sensorium
  reveal <run> <name>` for the developer at their own machine. The key
  exists after PR A; the mode is a later slice with its own threat model
  written first.
- **Scanner parity** — the content list is a floor; gitleaks-scale pattern
  sets, entropy heuristics and per-provider validators are not attempted.
- **Allow-globs / regex knobs** — exact names only; a glob is a later
  demand-driven addition (designing-notation §3: read demand off failures,
  not off imagination).
- **Windows ACLs** — modes are documented as advisory there; setting ACLs
  is not attempted.
- **Redacting spools under `target/`** — the Rust content window is named,
  bounded at 0600, and not closed; closing it means the runtime takes a
  regex dependency, which is a different crate than the one that ships.
- **Retrofitting stores other than the local one** — `redact` reads
  `SENSORIUM_DIR` like every command; a remote store is the product's.

## 12. Risks named

- **False positives on legitimate names** (`key_pressed`, `pass_count`,
  `auth_url`): bounded by segment-exact matching, the allowlist, and the
  census that fails the suite the moment the rule fires on the corpus's
  own values. The residual cost is a `<redacted #…>` where a value was
  wanted, which `info`'s `redaction:` line explains.
- **Content-regex cost at capture** on every string, repr and output
  chunk: H5's number. If it is large, the mitigation is a cheap pre-check
  (no `:`, no `-----`, no `ey`, no prefix byte → skip the regexes), applied
  before any pattern runs, and measured again.
- **The wire bump** touches every converter test that builds a v3 header;
  the plan builds v4 alongside and keeps the v3 fixtures as the
  older-runtime path.
- **The key on a shared or network store**: two users of one
  `SENSORIUM_DIR` share one key, so their digests are comparable and each
  can brute-force the other's low-entropy values with it — the same trust
  they already extend by sharing a store of full traces. Documented, not
  solved.
- **An old reader renders the marker as a quoted string** (`'<redacted>'`):
  graceful, and slightly misleading. The contract says so; nothing older
  than 0.14.0 is in use anywhere.
- **`redact --all` on a live store** while a recording is writing: the
  copy-rewrite-rename touches only completed `*.db` files (a recording's
  file is `.<run>.db.tmp` until finalized), so an in-flight trace is not
  reached; the summary line says how many `.tmp` files it saw and skipped.

## 13. Dated amendments

Amendments are footnoted here with the date, the old wording kept visible.

- **2026-09-13 — one plan per PR, not one plan.** §1's "one spec, one plan"
  reading (the conversation's words; this document said "its plan") becomes
  three plan files, one per PR, each written from this spec when the one
  before it merges: `docs/superpowers/plans/2026-09-13-sensorium-redaction-a.md`
  now; `-b` and `-c` at A's and B's merges. Reason: the 800-line ceiling
  binds plans too, and a single-slice plan already runs 250–540 lines.
- **2026-09-13 — E16 is measured in three parts (plan decision A1).** §9's
  "Measured once, after PR C" is read as *each part once, at its PR's close,
  on the cells that PR delivers*: A = H1-env, H2, H3, H6-env; B = H1-values,
  H5, H6-values; C = H4. One record file, three dated sections, each
  byte-locked when written. The old sentence stands above, unedited.

### 2026-09-14 — PR A shipped: the plan's decisions, the controller's rulings, and where the code differs

PR A (`docs/superpowers/plans/2026-09-13-sensorium-redaction-a.md`, Tasks
0–9) is the first of the three. Nothing in §§1–12 above is edited; this
section says what shipped, what was ruled while it shipped, and every place
the code and the sections above disagree. Where they disagree, **the code as
landed is what the docs describe**.

#### (a) The plan's decisions A1–A11, as shipped

| # | as shipped |
|---|---|
| A1 | E16 is measured in three parts, one per PR, each once — A = H1-env, H2, H3, H6-env; B = H1-values, H5, H6-values; C = H4. One record file, dated sections, each byte-locked when written. Part A shipped two sections (**R30**), run 1 and run 2. |
| A2 | `_env_diff(was, now, redaction=None)` returns a six-tuple with `uncomparable` last; `_env_state(meta, env, now_meta=None)` builds the `RedactionPair` from both metas and `Key.load(paths.trace_root())`; the five existing unpack sites take the sixth name. **Amended by R21**: a redacted name whose digests differ IS partitioned by name (session/harness), only RELOCATION is skipped. |
| A3 | `UNVERIFIABLE_ENV = "env: unverifiable in part (redacted variables not comparable)"`, short form `env (redacted, not comparable)`, computed from the two metas through `redact.uncomparable`; the names ride the env line, not the marker. Shipped as written. |
| A4 | `convert_dir(spool_dir, key: &Key)`; the driver passes the key it created, standalone `cargo sensorium convert` builds one with `Key::load(&store_root()?)` and never creates. Shipped as written; **R25** made the unkeyed WARN line the driver's only. |
| A5 | Key creation lives in the drivers and the Python recorder, never in a runtime; `cargo-sensorium/src/redaction_key.rs` reads 32 bytes from `/dev/urandom` (std only). Shipped as written; **R15** changed HOW it is published, not where. |
| A6 | The census input is the committed `tests/fixtures/benign-env-names.txt` (this box's shell names plus 40 common CI names, expected firing subset at its top); the corpus runner's own environment is not a census input in PR A. Shipped as written — and it is what found the **R10** gap. |
| A7 | `info`'s `env:` field. Shipped with **three** forms, not one: the bare hash, `(N vars, 0 redacted)`, and `(N vars, k redacted: …)` capped at eight names. |
| A8 | The `redaction:` line goes directly after `caps:`, four forms. Shipped as written; `values redacted: N` is absent because PR A redacts no values. |
| A9 | Versions and the changelog land in Task 7, one commit, `## 0.15.0` dated. Shipped at `fbd1a03` (Python 0.15.0, sensorium-rt 0.6.0, cargo-sensorium 0.7.0, sensorium-ts 0.5.0). |
| A10 | E16 part A records existing programs, no new probes, each with `SENSORIUM_E16_TOKEN` exported. **Amended by R27**: `corpus/typescript/aliasing` does not exist; the TypeScript arm records `corpus/typescript/async_interleaved` and the Rust arm's `--focus` names a function that exists in `corpus/rust/aliasing`. |
| A11 | The fixture's schema is fixed now, `docs/trace-format/redaction-v1.json`; PR B fills `content`. Shipped as written, `content` empty, read by all three languages' suites. |

#### (b) The controller's rulings R1–R38

Each was ruled during execution and is in the plan's gitignored ledger with
its evidence. The third column is the cost the ruling was taken at.

| R | the ruling | cost if wrong |
|---|---|---|
| R1 | §6.2's per-name comparison lives ONCE, in `redact.compare(before, after, was, now, key)`; `uncomparable()` and `RedactionPair.compare` both delegate. | one extra small type in T1 |
| R2 | When `mode == "off"` every writer and converter emits exactly `{"rule": "v1", "mode": "off"}` and nothing else. | a converter that adds `by` on an off trace is a one-line fix |
| R3 | Task 5 owns both `is_recorder_key` edits; Task 6 does not touch them. | none, T6's reviewer would see a no-op diff |
| R4 | `paths.traces_dir()` creates the trace root 0700 FIRST, then `traces` 0700 — `mkdir(parents=True)` gives parents default perms. | H2 STOPs on the root dir |
| R5 | `redact.Key` is a frozen dataclass of `path` and `material`; `keyed`/`key_id` are properties. | none |
| R6 | Model assignment per task (opus for the multi-file and prose-driven tasks, sonnet for the rest), reviewers likewise. | *(process; no cost recorded)* |
| R7 | Every digest hashes `text.encode("utf-8", "surrogateescape")` — env values arrive surrogateescaped. | none, ASCII values are unaffected |
| R8 | `redact.Key` carries `problem: str \| None` naming why it is unkeyed, for `info`'s UNKEYED line. | an unused field |
| R9 | `redact.compare` is called only for a name in at least one side's `redaction.env`; names in neither keep plain equality. | a redacted name compared as plaintext, which T6's tests would catch |
| R10 | **§2.1 amended**: `PWD` joins SEGMENTS but fires only in a name of two or more segments; an EXACT set `{PGPASSWORD}` fires regardless of segments. | two fixture rows to revert |
| R11 | E16 runs the three recordings under `env -i` with an explicit allowlist, and preflight refuses if any allowlisted name fires. | a scrubbed env that breaks cargo/vitest shows up in the dry run |
| R12 | `mode_note` prints `0644`-style (`{mode:04o}`), the spec's spelling. | one f-string |
| R13 | The `redaction.env` table is emitted with SORTED keys by every writer. | none |
| R14 | `digest()` falls back to `("utf-8", "replace")` if surrogateescape raises, and never raises. | a digest mismatch on a value no recorder produces today |
| R15 | **§3 amended**: key publication is atomic-by-content — `redaction.key.<pid>.tmp` (0600, fsynced) hard-linked at the name, `FileExistsError` → read the winner; `os.replace` + re-read where `link` is refused. | one more branch in a 30-line function |
| R16 | `db.create_trace` pre-creates with `O_WRONLY\|O_CREAT` at 0600 and `fchmod`s, WITHOUT `O_EXCL`, because `ts/ingest.py` hands it a file it already reserved. | a pre-existing non-empty file at that path would be opened by sqlite as a database, which is exactly what happened before this change |
| R17 | Task 6 runs before Tasks 3/4/5, because the Python recorder redacts while the live re-run side is plaintext. | none; the order is the plan's argument, not the spec's |
| R18 | `invocations.record`'s parent `mkdir` gains `mode=0o700` — the third creator of the store root. | one line |
| R19 | The Python `refocus` branch relicenses and prints its unverifiable checks exactly as the Rust and TypeScript branches do, so `UNVERIFIABLE_ENV` never withholds a Python pair. | a Python licence granted with the marker printed beside it, which is what the other two branches already do |
| R20 | `refocus_cmd.py` pops `redact.KEY_VAR` from the live environment snapshot; it is NOT added to `_UNCOMPARED_ENV`, whose printed list is pinned byte-for-byte. | none |
| R21 | **Amends plan A2**: a redacted name whose `compare` is False is partitioned by NAME (`session`, `harness`, else `changed`); only RELOCATION is skipped. | a redacted session variable's change is exempted exactly as its plaintext change was |
| R22 | The `compared` count and the "compared and unchanged" fact exclude the uncomparable names. | none |
| R23 | The runtime keeps its 0700 spool `DirBuilder`; Task 4 gives the DRIVER's two creators 0700 and adds an end-to-end mode assertion. | a listable spool dir under the driver until T4 lands, which is today's state |
| R24 | `Knobs` matching uses a linear scan, never `binary_search` over pub fields a foreign constructor may leave unsorted. | nothing at these sizes |
| R25 | The unkeyed WARN line prints from `load_or_create` (the driver) only; the read-only `load` (standalone `convert`) is silent. | a silent unkeyed standalone conversion of an OLD spool; `info` still says UNKEYED on the trace |
| R26 | The Rust converter's two remaining `create_dir_all`s (`convert/sqlite.rs`, `convert/runid.rs`) become 0700, with a test. | two lines |
| R27 | **Pre-launch amendment to the pre-registration**, recorded beside the locked §1: the TypeScript arm records `corpus/typescript/async_interleaved`, and the Rust arm's `--focus` names a function that exists. | none; the cells are unchanged |
| R28 | The docs say: a store whose key cannot be created or read records unkeyed and says so once, before the build; a store root that resolves to nothing produces no trace and the converter's own error names it. | two sentences |
| R29 | E16 part A's Rust arm records under a dedicated `CARGO_TARGET_DIR` inside the work root, so H1's grep and H2's sweep reach the spool. | one cold build of the aliasing crate and the runtime (minutes) |
| R30 | §9's H1 re-measure clause covers H2 and H3 too: run 1 stays verbatim, run 2 is appended beside it, dated, and the record says which run is the first PASS. | a second 25 MB run and one more section |
| R31 | `refocus_rust._is_recorder_key` becomes an EXACT set of the names the three driver sources SET, pinned by a structural grep; the three user knobs are COMPARED. | a new driver variable added without the list fails the structural test loudly |
| R32 | Task 8's fix round folds four minors because run 2 reuses that instrument and record. | a slightly larger fix diff |
| R33 | Extends R31 to TypeScript: `refocus_typescript.is_recorder_key` is the exact set `ts/driver.py::_env` sets, pinned structurally. | a new driver variable fails the structural test loudly |
| R34 | **Amends R31**: `SENSORIUM_INNER_RUNNER` leaves the exclusion set (a changed runner chain is a world change) and the structural pin greps SET-sites only. | a user who chains a runner sees one more compared variable, which is the truth |
| R35 | `store/db.py:117`'s parent `mkdir` — the last default-mode creator inside the store — goes through the two-level 0700 idiom; the changelog says an existing store keeps the modes it was created with. | two lines |
| R36 | `CHANGELOG.md`'s `## 0.8.7` entry moves verbatim to `CHANGELOG-ARCHIVE-2.md` under a dated cut note, to stay under the 800-line gate. | none; entries move verbatim |
| R37 | `e16a.sh` rebuilds the release driver as its first phase and stamps the outcome and the binary's mtime into the raw record — a warning comment is not a check. | seconds when the build is fresh |
| R38 | Task 9's push and PR move AFTER the final whole-branch review, so the PR carries the reviewed branch; Task 9 does the debt section, these amendments and the green run. | none; the PR is Brice's to merge either way |

#### (c) Where the shipped code differs from §§1–12

Fourteen, documented at Task 7 and named here so a reader of the sections
above is not misled by them.

1. **§2.1's segment set.** Spec said 24 segment words with `PWD`/`OLDPWD` as
   non-firing examples; shipped 25 including `PWD`, gated on two or more
   segments, so both examples stay true by a different mechanism (**R10**).
   Where: `src/sensorium/redact.py`, and its Rust and TypeScript twins.
2. **An `EXACT` set exists.** Spec had no counterpart; shipped
   `{PGPASSWORD}`, firing regardless of segments, because segment-exact
   matching cannot see inside a compound word (**R10**). Where: the same
   three modules and `docs/trace-format/redaction-v1.json`.
3. **Key publication.** §3 said `O_CREAT|O_EXCL` at 0600 on the final name;
   shipped a per-pid temporary written whole, fsynced and hard-linked at the
   name, with an `os.replace` fallback and a re-read either way (**R15**).
   Where: `redact.Key.load_or_create`, `cargo-sensorium/src/redaction_key.rs`.
4. **The fixture's shape.** §2.5 said cases of `{"name", "value", "expect"}`
   plus a `"split"` list; shipped `{"split": [...], "names": [{"name",
   "fires", "knobs"?}], "content": []}` — no `value`/`expect`, and `content`
   empty because the content rule is PR B's. Where:
   `docs/trace-format/redaction-v1.json`.
5. **Who reads the fixture.** §2.5 said `cargo-sensorium`'s tests read it for
   the content rule; shipped readers are `tests/test_redact.py`,
   `rust/sensorium-rt/tests/redact.rs` and `typescript/test/redact.test.mjs`,
   and there is no content rule to test.
6. **No `redacted` object on a capture, and no `values` key.** §4.2 and
   §6.1's first example describe both; PR A redacts no captured values,
   `redaction.values` is absent from every trace and `info` prints no
   `values redacted:` clause. Where: pinned by `v42`'s `expect_absent`.
7. **`info`'s `env:` field has three forms, not one.** §6.1 showed only
   `(120 vars, 2 redacted: …)`; shipped the bare hash (no `redaction` key, or
   `mode: off`), `(N vars, 0 redacted)` for a measured zero, and the named
   form. Where: `refocus_world.env_of` / `info_cmd`.
8. **The keyed `redaction:` line can carry a mode note.** §3 says the
   loose-key note goes on that line, §6.1's block does not show it; shipped
   `(key mode 0644 -- expected 0600)` appended only when the store's key is
   loose AND is the key that took these digests. Where: `info_cmd`.
9. **The cap helper's name.** §6.1 names `_shown`; shipped
   `refocus_world._capped`.
10. **§6.2's table gains three rulings.** **R21** (a redacted session or
    harness variable keeps its set exemption) and **R22** (the `compared`
    count excludes the uncomparable) are not in the spec; **R19** (an
    uncomparable name never withholds) the spec does state. Where:
    `refocus_world._env_diff`, `refocus_env.RedactionPair`.
11. **The digest's input bytes differ per language.** §3 said "UTF-8 of the
    string as the recorder holds it"; shipped, Python hashes the
    surrogateescaped byte `os.environ` handed it (with a `replace` fallback,
    **R14**) while Rust and TypeScript hash the U+FFFD they stored in its
    place (`spool::sorted_env` is `to_string_lossy`) — so a non-UTF-8
    environment value digests differently across languages. Documented as an
    honest limit on the same per-recorder terms `env_hash` already carries.
12. **The header carries TWO siblings.** §4.3 describes one `redaction` key;
    shipped, the Rust proc header and the TypeScript BOOT write
    `env_redaction`/`envRedaction` beside it and the converter folds them.
    Where: `TYPESCRIPT-KEYS.md`, `rust/README.md`.
13. **Key order is not a wire promise.** Not stated in the spec; the Rust
    converter's `serde_json::Map` is a `BTreeMap`, so it alphabetises the
    `redaction` object while **R2**'s order is source-level. Documented in
    `docs/redaction.md`.
14. **§5.5's mode table missed the converter's own `traces/`.** Shipped 0700
    via `perms::dir_all` with a test (**R26**). Where: `convert/sqlite.rs`,
    `convert/runid.rs`.
15. **§5.5's opening sentence is categorical; the writers outside the store
    are not covered** (2026-09-14). §5.5 opens "Every file this slice's
    writers CREATE is 0600 and every directory 0700", which reads over the
    whole branch; shipped, the writers outside the store and the spools —
    `mirror.rs`, `rt_build.rs`, `fallback.rs`'s `<target>/sensorium/manifests`,
    and `ts/wrapper.py`'s files under the user's `node_modules` — are
    unchanged at default modes and are named in CARRIED-DEBT as outside this
    PR's promise. The mode TABLE below that sentence is right as it stands:
    every row in it shipped. Where: the topic sentence in `CHANGELOG.md`,
    `docs/redaction.md`, `rust/README.md` and `docs/CARRIED-DEBT.md` is
    scoped to the store and the spool directories.

#### (d) E16 part A's outcome

Run 1 (2026-09-14) read **DONE-WITH-STOP** — H1 PASS, H2 STOP (ten paths at
0664/0775), H3 STOP (the Rust branch's `SENSORIUM_`-prefix exclusion granted
a licence over a rotated token), H6 PASS. Run 2, measured from zero with a
fresh token after `6a719e4`, `1f60dd6`, `9d8f16a` and `e36d5dd`, read **DONE**
— H1, H2, H3, H6 all PASS; both readings are in
`docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md` §2, run 1
byte-untouched above run 2, with the per-cell statement of which run is the
first PASS.

### 2026-09-14 — PR B shipped: the plan's decisions, the controller's rulings, and where the code differs

PR B (`docs/superpowers/plans/2026-09-14-sensorium-redaction-b.md`, Tasks
0–12) is the second of the three. Nothing in §§1–12 above is edited; this
section says what shipped, what was ruled while it shipped, and every place
the code and the sections above disagree. Where they disagree, **the code as
landed is what the docs describe**.

#### (a) The plan's decisions B1–B28, as shipped

| # | as shipped |
|---|---|
| B1 | Wire v4's REDACTED-BY-NAME LINE tag is `4`, not §5.2's `3` (tag 3 has meant UNBOUND since wire v3, shipped 0.13.0). Shipped as written: `truncated` 0, the text the 16-hex digest or empty when unkeyed, LINE rows only; a v2/v3 reader refuses tag 4 as `not 0..=3`, a v4 reader refuses `5+`. |
| B2 | `by` reads `recorder` only where the runtime did the value half too (Rust wire ≥ 4 with a `redaction` header whose mode is on; `sensorium-ts` ≥ 0.6.0), `converter` wherever a converter applied a half the runtime should have. Shipped as written — and it is why a re-converted older spool now says `converter` where it said `recorder`. |
| B3 | `redaction.values` is counted by the trace's WRITER. **Amended by R10**: counted at the WRITE site (`redact_values.count`/`count_capture` over what is handed to `add_event`/`close_frame`; the tee counts a changed chunk; the two converters count as they build), not by the transforms with a roll-back. Absent under `mode: off`. |
| B4 | The per-kind whole-redaction rule, as written: `str`/`num`/`dbg` → the marker with a digest over the clipped text (`repr(v)` for a `num`); `obj` → the `repr` goes, `type`/`oid` stay; `seq`/`map` → the sample goes, `type`/`len`/`oid` stay, `digest: null`; `none`/`bool`/`unread` untouched. **Extended by R10** (an unrecognised kind is withheld WHOLE) and **carved by R17/R19** (`()`, `undefined`, `null` are never withheld). |
| B5 | The content rule reaches `str` values, `obj` reprs recursively through `seq`/`map` samples, `exc.msg` and output chunks one `write()` at a time. Shipped as written; the chunk boundary is documented as a limit. |
| B6 | Python's redaction state is one module-level `State` in `redact_values`, installed from `boot.run_target` after the key loads; `record/capture.py` is not changed. Shipped as written — `capture.py` has no diff on this branch. |
| B7 | The RETURN name rule reads the callee's LAST qualname segment; `<lambda>`, `<module>`, `<genexpr>`, `<anonymous>` never fire. Shipped as written, in all three hands. |
| B8 | A `map` sample pair whose KEY is a firing `str` has its VALUE withheld under that key's name — **Python only**. Shipped as written; documented as a limit for Rust and TypeScript, whose captures are rendered text. |
| B9 | Converters re-apply idempotently, values included: the content rule always runs (a marker is a fixed point, pinned by two fixture no-op rows); the CALL/LINE name rule runs in a converter only for a spool whose runtime did not, and never on a capture already carrying `redacted`; the RETURN name rule always runs in the Rust converter. Shipped as written. |
| B10 | `watch`: `expr.resolve` returns a `REDACTED` marker, `_name`/`_member`/`_length` raise `NotCaptured(name, REDACTED_REASON)`, `_render` prints `<redacted; no comparable value>`, and a predicate meeting only taken values ends at `NOTHING WAS CHECKED`, exit 3. Shipped with **R13**'s addition: `_guidance` gains a `REDACTED_REASON` arm naming `SENSORIUM_REDACT_ALLOW=<name>` as the re-record remedy. |
| B11 | `flow`: `flow_values.matches` is False for a name-redacted capture, so `--value` never sights one; `flow_cmd.resolve_object` refuses at `BAD_CALL` (exit 2) with `'{name}' at e{id} is redacted (by name) and has no identity or value to follow`. Shipped as written; **R20** settled which binding the corpus question names (`send:token`). |
| B12 | `fmt_value`: `<redacted #xxxxxxxx>` for a name-redacted `str`/`num`/`dbg` (or `<redacted>` unkeyed), `type[len]=<redacted>` for a container, `Type#oid` unchanged for an `obj`, a content hit as stored; `fmt_exc` prints the stored message. Shipped as written. |
| B13 | The five splits land first, in one task, verbatim with re-exports: `refocus_facts.py`, `flow_report.py`, `convert/discover.rs`, `redact_key.py`, `record/boot_io.py`. Shipped, with **R7** (`continuity_line` and `_MAX_NAMED_GAPS` travel with their only caller) and **R8** (`from __future__ import annotations` for `TYPE_CHECKING`-only names). |
| B14 | E16 part B's three probes live with the instrument at `tests/acceptance_e16/probes/{python,rust,typescript}/`, not §9's `probes/redaction/…`. Shipped as written. |
| B15 | H6-values' planted counts are derived by hand from the probe sources and pre-registered — Python 5, TypeScript 4, Rust 4, each traced to a named row. Shipped as written; the run read exactly 5, 4 and 4. |
| B16 | H1-values' Rust reading is exact: the token appears in the `.spool` files exactly **3** times, counted as occurrences. Shipped as written; the run read 3. |
| B17 | H5 reads `corpus/_bench`'s own statistic — best-of-5, not §9's "two medians" — baseline a worktree at `7dd25d2`, treatment this branch's head, same box, same session. Shipped as written; never gated. |
| B18 | The content rule's pre-check: one alternation of the literal prefixes every pattern starts with, run before any pattern, with a test pinning that every positive fixture case passes it. Shipped, and **amended by R21**: `_TRIGGER` folds case where the pattern it guards does. |
| B19 | The three corpus cases plant `SENSORIUM_CORPUS_TOKEN` (no content-rule shape), name every binding so the NAME rule fires, and print nothing; the runner sets the variable from a new top-level `env:` key in `questions.yaml`. Shipped as written. |
| B20 | The fixture's `content` rows are `{"pattern", "text", "after"}`, a negative row's `after` equal to its `text`, with `<redacted>` and `postgres://u:<redacted>@h/db` as the two no-ops. Shipped as written. |
| B21 | Exception messages are content-ruled in all three: Python at every `capture_exc(` site, the Rust converter at every `"msg"` it writes, TypeScript in `dbg.mjs::exc`. Shipped, with **R16**'s exception: an `err` RETURN's synthesised exit RAISE is withheld WHOLE under the value's digest, not content-ruled. |
| B22 | The TypeScript runtime reads its knobs and key once (`redact.current()`, lazily); `dbg.mjs` imports `content`/`current` from `redact.mjs`, which imports `node:crypto` only. Shipped as written. |
| B23 | `info`'s `values redacted: N` clause rides both the keyed and the UNKEYED `redaction:` line. Shipped as written. |
| B24 | The Rust runtime's tag-4 digest is over the CAPPED text, and an `unread` delta whose name fires stays tag 2. Shipped as written. |
| B25 | `docs/TRACE-FORMAT.md` is edited net-zero, its §5 sentence becoming a two-line pointer to `docs/redaction.md`. Shipped as written: 797 lines before, 797 after. |
| B26 | A `SENSORIUM_NO_REDACT` recording applies no value rule anywhere — recorder, converter or ingest — and its `redaction` stays A's two-key form with no `values`. Shipped as written. |
| B27 | The census is STATIC and runs at Task 0, over every binding name in `corpus/**`, every `args`/`deltas` key in the vectors and every `a`/`d` key in the ts-spool fixtures, against a committed `tests/fixtures/corpus-firing-names.txt`. Shipped as written — and it is what produced B28. |
| B28 | `KEY` fires only inside a name of two or more segments, as `PWD` does (a `_SOLO_EXEMPT` set `{PWD, KEY}` in all three rule modules). Added by the controller at Task 0 on the census's evidence (**R6**); rule v1 is AMENDED rather than bumped to v2, because no trace under the earlier spelling exists outside this box and CI. |

#### (b) The controller's rulings R1–R25

Each was ruled during execution and is in the plan's gitignored ledger with
its evidence. The third column is the cost the ruling was taken at.

| R | the ruling | cost if wrong |
|---|---|---|
| R1 | v42's `grep hunter2` question is DROPPED: `expect_absent: ["hunter2"]` rides every question that remains (the runner applies it per question), and a question whose only pin is a no-match line asserts nothing. | `grep`'s rendering of a marker goes unpinned by v42, but `frame`'s is the same `fmt_event` path |
| R2 | The H5 baseline worktree under `$E16_DIR` is an in-repo, reversible side effect, not a stop condition; it is removed in Task 12's chores. | one worktree to delete by hand |
| R3 | Every Rust corpus run in this plan uses a driver built from THIS worktree, that `target/release` first on `PATH`, never `~/.cargo/bin`. | a second red `main` |
| R4 | `main`'s hotfix (PR #41) is cherry-picked onto `feat/redaction-b` right after Task 0, so every task's whole-suite gate is green from there. | a trivial merge conflict on three yaml lines when #41 merges |
| R5 | An `unbound` row's NAME is never withheld — rule v1 redacts VALUES, and `unbound:key` stays `unbound:key`. | a binding's name in a trace, which the CALL/LINE rows show anyway |
| R6 | **§2.1 amended (plan decision B28)**: the segment `KEY` fires only in a name of two or more segments, on the census's evidence that 8 of its 17 firing bindings were a bare `key`. | one fixture row per language to revert, and a bare `key` local holding a secret stored as typed until then |
| R7 | `continuity_line` and `_MAX_NAMED_GAPS` move to `flow_report.py` with the four named functions — the brief's list was an under-count and the ≤720 target was the binding requirement. | none; a re-exported name |
| R8 | `from __future__ import annotations` in `flow_report.py` for `TYPE_CHECKING`-only names — a lazy import cannot serve an annotation and a module-level one is a hard cycle. | a runtime `NameError` if someone later evaluates those annotations, which the suite would show |
| R9 | `test_acceptance_e9_read`'s refusal pin reads `RT_VERSION` out of `spool.rs` instead of typing a version by hand. | a regex over one source line |
| R10 | **Amends B3**: `redaction.values` is counted at the WRITE site, and an unrecognised capture kind is withheld WHOLE (`k` kept, every other field dropped, `digest: None`), pinned by an exhaustiveness test over `capture.py`'s kind literals. | a count that is a pure function of the trace's contents, which is what B3 promised |
| R11 | **Pre-launch amendment to the pre-registration**, recorded beside the locked §1: the Python probe is recorded with `--focus main:handle`, because a bare `--focus handle` names a MODULE. | two of the five pre-registered rows never recorded, which H6-values would read as STOP |
| R12 | `corpus/stale_cache`'s `build_key` becomes `memo_id` rather than the expectation moving — the case's truth is a stale cache keyed by a string, and its questions are about the KEY's value. | one corpus program's function renamed |
| R13 | `watch._guidance` gains a `REDACTED_REASON` arm naming `SENSORIUM_REDACT_ALLOW=<name>`; without it a redacted name falls through to "this is scope, not capture depth", which is false. | one guidance sentence |
| R14 | v42 declares `object_identity: true` (else `flow --object` refuses at the capability gate, exit 3) and its `flow --value` question expects exit 1, zero sightings being NEGATIVE. | none; they are pins |
| R15 | `RT_VERSION`/`sensorium-rt` 0.7.0 move in Task 6 with the v4 reader and a driver rebuilt from the tree, not in Task 5; between the two a fresh driver cannot convert what the runtime writes — a SANCTIONED RED for `mechanics.sh` and `cargo-sensorium`'s real-driver e2e tests. | one task with a version number in its brief that lands one task later |
| R16 | On an `err` RETURN whose site's qualname fires, the synthesised exit RAISE's `exc.msg` is withheld WHOLE under the value's own digest, not content-ruled: an `Err` return IS the return value in Rust. The two are ONE withheld text seen twice, counted ONCE. Python is untouched. | one message's text lost where the content rule would have kept its shape |
| R17 | A synthesised `()` — and any RETURN text exactly `()` — is never withheld by name, marked or counted; the `unread` carve-out extended. | none; nothing is hidden by `()` |
| R18 | The TypeScript content rule runs AFTER the name rule, in `redact.mjs` beside it, not inside `dbg()`: the brief's order would have digested the constant `<redacted>` for a text the content rule had already replaced, giving two secrets one identity. | none; it is the brief that was wrong |
| R19 | A `dbg` text exactly `undefined` or `null` withholds nothing on ANY site (arg, delta, return) in BOTH hands — `redact.mjs::taken()` and `redact_values.named()`, which also exempts `()`. `NaN` and numbers stay under the rule. | none |
| R20 | The Python corpus case's `flow --object` question resolves `send:token` — `handle()` binds the token as a local, so `handle:token` names nothing; the refusal is the same B11 sentence at the CALL that carries the argument. | none |
| R21 | **Amends B18**: `_TRIGGER` folds case where the pattern it guards does — it was case-SENSITIVE while `authorization-header` is `(?i)`, so `BEARER <token>` skipped the table and was stored in plaintext. Fixed in all three languages with two uppercase fixture rows. | a leak on an uppercase header |
| R22 | Part B is measured into the SAME work root the pre-registration names, `store-b` beside `store-a`; the controller deletes `$E16_DIR/rust-target` WHOLE before launching (part A's build cache, which the `other` sweep walks), and everything else of A's stays. | one cold build of the probe crate |
| R23 | `mint` is a critical phase — an empty token would run every later phase on `""`. | none |
| R24 | Task 12's two review findings join the final whole-branch review's fix wave as ONE dispatch, rather than a round of their own for two one-line doc corrections. | none; a review seat |
| R25 | The fix wave CLOSES the `meta.children` path rather than only disclosing it: each element of a SPAWNED process's command line goes through `redact_values.text()` at the audit sink, an element that changed counts into `values`, and the limits inventory names it beside `argv`. | a content-ruled child argv where no name rule can apply — a command line has positions, not bindings, so there is no name to ask about |

#### (c) Where the shipped code differs from §§1–12

Twenty — nineteen documented at Task 9, the twentieth added by the final fix
wave — named here so a reader of the sections above is not misled by them.

1. **§5.2's LINE tag is `4`, not `3`.** Tag 3 has meant UNBOUND on a LINE
   row since wire v3 shipped in 0.13.0, one day before this spec was
   written; §5.2's verbatim block named 3 anyway. Shipped: tag 4, and the
   block in `spool.rs`'s doc comment and `rust/README.md` is v4's
   (**B1**). Where: `rust/sensorium-rt/src/line.rs`,
   `rust/cargo-sensorium/src/convert/spool/line.rs`.
2. **§4.3's `by` is the last hand that applied the rule; shipped it is the
   last hand that applied the VALUE half** (**B2**). A Rust v3 spool or a
   `sensorium-ts` 0.5.0 spool re-converted under this release reads
   `converter` where it read `recorder` — a visible change to a published
   key, stated in the CHANGELOG and in `docs/redaction.md`. Where:
   `convert/redaction.rs`, `src/sensorium/ts/redaction.py`.
3. **`redaction.values` is counted at the WRITE site, not by the rule's
   appliers** (**B3**, **R10**). §4.3 calls it "a witness count"; shipped,
   the witness is the writer — `count(payload)` over what is handed to
   `add_event`/`close_frame`, so a secret re-captured at every line of a
   loop counts once and a dropped payload cannot leave a count behind.
   Where: `src/sensorium/redact_values.py`, `convert/redaction.rs`,
   `src/sensorium/ts/redaction.py`.
4. **§4.2's per-kind rule is spelled out, and has two exemptions the spec
   has not.** §4.2 speaks of `v`/`repr` only; shipped, `seq`/`map` keep
   `type`/`len`/`oid` with `digest: null` (a container has no stored text
   to digest), `none`/`bool`/`unread` are untouched, an unrecognised kind
   is withheld WHOLE, and a value that says the program produced nothing —
   Rust's `()`, a `dbg` text of `undefined` or `null` — is never withheld
   on any site in any hand (**B4**, **R10**, **R17**, **R19**). Where:
   `redact_values.named`, `redact.mjs::taken`, `convert/redaction.rs`.
5. **§5.1's one `redact.py` is four modules.** The spec put the whole rule
   in `src/sensorium/redact.py` "under ~250 lines". Shipped:
   `redact.py` (the name rule, 304), `redact_key.py` (the key),
   `redact_content.py` (the content rule, 156) and `redact_values.py` (the
   value half and its module-level `State`, 388). `content(text)` returns
   `(str, bool)` from `redact_content`, not from `redact`.
6. **`capture_value` is not changed** (**B6**). §5.1 has it applying the
   content rule to every `str` and `repr` and the name rule in the map
   sampler; shipped, `record/capture.py` has no diff on this branch and
   every operation runs at the WRITE sites through `redact_values`, so a
   capture stays pure and one install point governs the rule.
7. **§5.2's `convert/redact.rs` is `convert/redact_content.rs`**, beside
   the `convert/redaction.rs` PR A already added; the content rule, the
   RETURN name rule and the `redaction` meta build are split across the
   two rather than gathered in one new file.
8. **§5.3's order: name THEN content** (**R18**). The spec puts the content
   rule "in `dbg.mjs`" and the name rule in `captures`/`ret`, which reads as
   content-first for a return; shipped, both halves run in `redact.mjs`
   beside each other, name first, so a text the content rule has already
   replaced is never digested as if it were the value. Where:
   `typescript/src/redact.mjs`.
9. **§5.4 is extended to values, with a never-re-digest rule** (**B9**).
   The spec's idempotence clause covers the env and says a marker is never
   re-redacted; shipped, the content rule always re-runs in both converters
   (a marker and a replaced text are fixed points, pinned by two fixture
   no-op rows), the CALL/LINE name rule runs in a converter only for a
   spool whose runtime did not and never on a capture already carrying
   `redacted`, and the RETURN name rule always runs in the Rust converter.
10. **§2.1's `KEY` fires only inside a longer name** (**B28**, **R6**) —
    a second `_SOLO_EXEMPT` member beside A's `PWD`, on the static census's
    evidence. A bare `key` is a cache key on almost every mapping-iterating
    function; every compound spelling still fires, and
    `SENSORIUM_REDACT_NAMES=key` restores it. Rule v1 is amended rather
    than bumped to v2 because no trace under the earlier spelling exists
    outside this box and CI; the identity rule in §2 binds from the first
    published release. Where: the three rule modules,
    `docs/trace-format/redaction-v1.json`.
11. **§2.5 said nothing about a content case's shape; shipped it is
    `{"pattern", "text", "after"}`** (**B20**), a negative row's `after`
    equal to its `text`. §2.5's `{"name", "value", "expect"}` case was
    already superseded by PR A's §13(c) item 4; this fills the `content`
    list A left empty. Where: `docs/trace-format/redaction-v1.json`.
12. **A pre-check runs in front of the patterns** (**B18**, **R21**). §12
    names it as a mitigation to apply "if H5 is large"; shipped, it was
    built in from the first commit of the rule — one alternation of the
    literal prefixes, case-folded where the pattern it guards is
    case-insensitive, with a test pinning that every positive fixture case
    passes it. Where: `redact_content.py`, `redact_content.rs`,
    `redact.mjs`.
13. **§6.1's `values redacted:` rides the UNKEYED line too** (**B23**).
    The spec prints it "only when the key is present"; shipped, values are
    redacted without digests as well, and a measured count is not
    conditional on a key. Where: `info_cmd`, vector `v42`.
14. **§6.3's `flow --value` refusal is the `--object` refusal** (**B11**).
    `--value` takes a LITERAL, not a binding, so the spec's sentence cannot
    attach where it says; shipped, `--value` simply never sights a
    name-redacted capture (a literal matching a marker would report every
    secret in the run as sightings of one value) and `--object` refuses at
    exit 2 with `'{name}' at e{id} is redacted (by name) and has no
    identity or value to follow`. Where: `flow_values.matches`,
    `flow_cmd.resolve_object`.
15. **§8's vector questions, as they landed** (**R1**, **R14**): the `grep`
    question is dropped — `expect_absent: ["hunter2"]` rides each of the six
    that remain, and a question whose only pin is a no-match line asserts
    nothing — `v42`
    declares `object_identity: true` so `flow --object` reaches its
    refusal rather than the capability gate, and the `flow --value`
    question expects **exit 1**, zero sightings being a negative answer.
    Where: `docs/trace-format/vectors/v42-redaction-render.json`.
16. **§8's census is STATIC** (**B27**). The spec runs rule v1 over the
    values in the fixture and corpus traces the suite builds; shipped,
    `tests/test_redact_census.py` scans SOURCE — every binding name in
    `corpus/**`, every `args`/`deltas` key in the vectors, every `a`/`d`
    key in the ts-spool fixtures — and asserts the firing set equals a
    committed `tests/fixtures/corpus-firing-names.txt`. It runs in seconds,
    it ran at Task 0 before any renderer existed, and it is what produced
    difference 10.
17. **§9's probes live with the instrument** (**B14**) at
    `tests/acceptance_e16/probes/{python,rust,typescript}/`, not at
    `probes/redaction/…`: `rust/probes` and `typescript/probes` are
    per-language probe suites with their own tooling, and these three
    belong to one instrument.
18. **H5's statistic is best-of-5, not a median** (**B17**). §9 says "the
    two medians"; `corpus/_bench/bench.py` reports best-of-`reps` and
    nothing else, so the reading is the two best-of-5 tables and the ratio
    per workload row. The measurement is `recorded/baseline` at `7dd25d2`
    against the same at HEAD, same box, back to back, never gated.
19. **§10's TypeScript HONESTY section is a file, with an index row and no
    stub.** The spec asks for "one section each … with a pointer"; shipped,
    the whole section is `typescript/HONESTY-REDACTION.md` and
    `typescript/HONESTY.md` carries row 13 of its index and nothing else —
    no `## 13.` heading in the body, which would have cost the four lines
    that file does not have. `rust/HONESTY.md` §14 is in place as written.
20. **`meta.children` is content-ruled, which §5.1 does not reach**
    (**R25**, the final whole-branch review's finding). §5.1 applies the
    rule to captures, exception messages and output chunks; shipped, each
    element of a SPAWNED process's command line takes the CONTENT rule at
    the Python recorder's audit sink and an element that changed counts into
    `redaction.values` at the write — `info` prints that list back verbatim,
    so it was a plaintext path out of the trace. The NAME rule does not run
    there: an argv has positions rather than bindings, and there is no name
    to ask about. Where: `src/sensorium/record/boot.py::_audit`,
    `::_content_ruled`.

One further limit, not a difference but not stated in §§1–12 either: **a
spool ingested into a store that did not record it names two keys.** The
trace's `key_id` is the RECORDER's, while the capture digests the converter
took are under the INGESTING store's key. In practice the driver mints the
store key it hands the runtime and the two are one; a spool carried between
stores is where they part. Documented in `docs/redaction.md`'s honest limits
and carried in CARRIED-DEBT.

#### (d) E16 part B's outcome

Measured **once**, 2026-09-14, 85.3 s wall clock, under `e16b.sh` after four
dry runs: **DONE** — H1-values **PASS** (20 gated files: every count 0 under
the store, in every Rust `<pid>.proc.json` and in the TypeScript spool, and
the Rust `.spool` files exactly **3** occurrences, the content window §5.2
names; 762 further files swept beside them, none holding the token),
H6-values **PASS** (python 5, rust 4, typescript 4, each redacting exactly
`SENSORIUM_E16_TOKEN`, against §1's amendment's hand-derived 5/4/4), and H5
**measured and not gated**: `HEAD over 7dd25d2` of 1.05–1.39 across the seven
workload rows, every ratio above 1. The reading is in
`docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md` §3, with
the per-file grep table, both bench tables verbatim, the census, and two
pre-launch amendments recorded beside §1's locked text (**R11**'s focus
spelling; the vitest copy's omission of `corpus/typescript/secret_in_env`).
H5's cost and its two named levers — a per-name memo for `fires()` and a
cheaper trigger — are a CARRIED-DEBT finding, which is what §9 says an
outlier is.

### 2026-09-15 — PR C designed: what §7 leaves open, decided before execution

Written the day the slice was opened (Brice: "yes and go", 2026-09-15 —
the slice is GO, and the live retrofit of this box's own store is
pre-authorised conditional on H4 passing on a copy), before any code, so
that what PR C is measured against is on record ahead of the instrument.
Plan `docs/superpowers/plans/2026-09-15-sensorium-redaction-c.md` carries
the tasks; this section carries the decisions, each of which amends §7
non-silently. A `### … — PR C shipped` section follows at the end, on the
pattern of A's and B's, with the rulings and every place the code differs.

#### (a) What the store held on the day, measured

Read once, 2026-09-15, over `~/.sensorium/traces` on the box §9's H4 names
(the numbers are H4's premise, not its reading; §4 of the record will hold
the reading):

| fact | value |
|---|---|
| traces | **273** (`*.db`), 274 MB, 819 files with their `-wal`/`-shm` sidecars |
| by recorder | 251 `sensorium-rt` format 4 · 18 Python format 1 · 1 Python format 2 · 3 `sensorium-ts` format 4 |
| `redaction` key | absent from **all 273** — every one predates the rule and holds plaintext |
| env names that fire rule v1 | `CLAUDE_CODE_MESSAGING_TOKEN` and `SSH_AUTH_SOCK`, in every trace |
| modes | every `.db`, `-wal` and `-shm` at **0644** |
| `env_hash` | reproduces from the stored `env` under its language's formula in **273 of 273** (Python: `sha256(json.dumps(env, sort_keys=True))[:16]`; Rust and TypeScript: `sha256("\n".join(sorted k=v)))[:16]`, the spelling `ts/invocation.py::env_hash` already holds) |
| `frames.unwind_exc` | 123 non-null rows across 14 traces |
| `meta.children` non-empty | 3 traces (Python) |
| in-flight files (`.<run>.db.tmp`, `incomplete: true`) | none |
| stale `redaction.key.<pid>.tmp` | none |

#### (b) The decisions C1–C20

| # | decision | why |
|---|---|---|
| C1 | **The environment pass is the NAME rule only** — whole value → `<redacted>`, digest under the store's key — never the content rule. §7 says "both operations" on the env; the shipped rule (A's R-series, `docs/redaction.md` § *The content rule*: "runs where a text is STORED, and never over the environment") runs the content rule over stored TEXT in all three recorders and never over an env value. A retrofit that did more to an old trace's environment than a recorder does to a new one would make two rules. | one rule, the shipped one; §7's sentence is the difference recorded |
| C2 | **The value pass reaches exactly what the writers reach:** every `events.payload` (`args`/`deltas` maps through `redact_values.named` per binding; `value` through `named_return` under the callee's last qualname segment, joined from `code_objects` by `code_id`; `exc`/`thrown` through `exc`; samples recursively through `value`), every `frames.unwind_exc` (an `exc` object, B21), every `output.data` row through `text` (one row = one `write()`, the tee's own boundary), and each element of `meta.children` through the content rule (R25). Untouched, as the recorders leave them: `argv`, `cwd`, `exe`, `cargo_args`, `harness_command`/`harness_args`, `sites`, `source_hashes`, `invocations.jsonl`. | parity with the writers; the honest limits already name what stays plaintext |
| C3 | **`env_hash` is recomputed by `lang`:** no `lang` key (format ≤ 3, Python) → the JSON formula; `rust`/`typescript` → the sorted `k=v` join. Before the rewrite the STORED hash must reproduce from the stored env under that formula, else the trace is refused and named (`env_hash does not reproduce under the <lang> formula`). | a retrofit that cannot reproduce the old hash cannot claim the new one is the same formula — a structural guard, computable in milliseconds (rigorous-experiments §1) |
| C4 | **Knobs are the CALLER's:** `SENSORIUM_REDACT_NAMES`/`SENSORIUM_REDACT_ALLOW` read from the command's own environment and stamped; **`SENSORIUM_NO_REDACT` is ignored** — running `redact` is the decision, and `mode` is always `"on"` (§7). The Rust converter's retrofit runs under NO knobs because the recording was made under none; the command differs because the caller is asking NOW, with their environment. | §7's "the caller asked" |
| C5 | **A trace already at `mode: "on"` is re-applied idempotently:** names already in `redaction.env` keep their digests and their marker (no digest of a marker — §5.4's reason); a name NOT in the table that fires under the caller's knobs is digested now under the store's key; captures already carrying `redacted` are returned as they are (`redact_values.named`/`value` already do); new hits get the store's key. A `mode: "on"` trace whose `key_id` is not the store's is **refused** (`digests under key <id>, the store's is <id>; nothing rewritten`) — never two keys in one stamp. A `mode: "off"` trace and a trace with no key are redacted in full and stamped `on` (§7). | idempotence; a stamp that names one key must be true of every digest under it |
| C6 | **`by: "retrofit"` always** on a trace the command rewrites, whatever hand came before (§4.3: the LAST hand). `values` in the stamp is what the trace HOLDS after the pass (B3's meaning: every capture carrying `redacted`, every output row and `unwind_exc`/`exc` with a content hit, every `children` element with a hit). The per-trace LINE prints what THIS run redacted (`values 12`), which equals the stamp on a pre-rule trace and is smaller on a re-application. | two questions, two numbers; `info` prints the stamp |
| C7 | **The rewrite is backup → rewrite → checkpoint → fsync → rename → sidecars unlinked.** The original is opened read-write (a WAL database needs a writable `-shm` even to read) and copied with `sqlite3.Connection.backup` into `.<run>.db.redact.<pid>.tmp` beside it, created `O_CREAT\|O_EXCL\|0o600` — the backup API carries committed-but-uncheckpointed WAL pages a byte copy would lose. The copy is rewritten in one transaction, `PRAGMA wal_checkpoint(TRUNCATE)`, closed, `fsync`ed, `os.replace`d over `<run>.db`, the directory `fsync`ed, then the ORIGINAL's `-wal`/`-shm` unlinked (they belong to the replaced inode; a reader that still holds it keeps it). A killed retrofit leaves the original whole and a tmp; a tmp whose pid is dead is swept at the next `redact` that reaches the trace, one whose pid is alive refuses the trace as `another redact is rewriting it`. | §7's copy → rewrite → fsync → rename, made exact; R37's lesson (a copy that is not the database is a different claim) |
| C8 | **In-flight traces are skipped and named:** a `<run>.db` whose `incomplete` is `true` (the Python recorder writes in place) — `run <id>: in flight (incomplete), skipped`; `.<run>.db.tmp` files (the converters' and the ingest's) are not `*.db` and are never enumerated. §12 named only the `.tmp` case. | rewriting a file another process holds open in WAL mode races it |
| C9 | **Refusals, each named on its own line and all exit 2 (the others continue):** newer `trace_format` (`db.open_trace`'s own refusal), a format-4 trace missing required meta (likewise), an unknown `lang` (likewise), a non-reproducing `env_hash` (C3), another key (C5), a live tmp (C7), a database SQLite cannot open. A bad `<run>` reference is `paths`' own error, exit 2 before any trace is touched. | §7's exit 2; every refusal a reader can act on |
| C10 | **`--dry-run` prints stdout byte-identical to the real run** — the same per-trace lines, the same summary — and one line on STDERR (`dry run: nothing was written`). H4's "the count line matches the dry run" is then a diff of two stdouts. Exit codes are the real run's (0 if anything WOULD change). | §7's "the same lines under --dry-run", made checkable |
| C11 | **Modes:** the rewritten file is 0600 by creation; a trace that needs no rewrite but sits at another mode is `chmod`ed to 0600 in place with its sidecars (`run <id>: nothing to redact; mode 644 -> 600`) and counts as CHANGED (exit 0). `--all` also sets `traces/` to 0700 and prints `traces/ mode 755 -> 700` on the summary when it did; `redact <run>` never touches the directory. `redaction.key`'s mode is `info`'s to report, not this command's to change. | §5.5: "changing a user's store permissions behind their back is the retrofit's job, done when asked" |
| C12 | **The line and summary spellings.** Per trace: `run <id>: env <n> redacted (<names, capped at 8 like info>); values <n>; mode 644 -> 600` · `run <id>: nothing to redact; mode 600` · `run <id>: in flight (incomplete), skipped` · `run <id>: REFUSED: <reason>`. Summary: `redacted <x> of <n> traces (<y> already clean, <s> skipped, <r> refused); spools under target/ and the TypeScript spool dirs are not reached` with `; swept <k> stale key tmp file(s)` and `; traces/ mode 755 -> 700` appended only when non-zero/true. `<id>` is the file stem, the spelling `runs` uses. Traces are processed in sorted run-id order, one line flushed per trace. | §7's example block, made exact |
| C13 | **The stale key tmp sweep** (A's R15 hazard, CARRIED-DEBT "PR C"): `redact_key.sweep_stale(root) -> list[Path]`, pure and never raising, unlinks every `redaction.key.<pid>.tmp` whose pid is not alive (`os.kill(pid, 0)` → `ProcessLookupError`; `PermissionError` counts as alive) and leaves the rest. Called once per `redact` invocation before any trace; counted on the summary line. Recorders do not sweep — a recorder deleting files at boot is a different threat model. | the debt names this command |
| C14 | **Code:** `src/sensorium/redact_store.py` (`plan(path, key, knobs) -> Plan` — the whole judgement in memory: changed payload rows, output rows, unwind rows, new `env`/`env_hash`/`redaction`/`children`, the counts, the refusal or the skip; `apply(plan)` — C7's mechanics; nothing else writes) and `src/sensorium/query/redact_cmd.py` (argparse, the lines, the exits, the sweep, `--all`'s directory mode), registered in `cli._QUERY_MODULES` after `refocus_cmd`. `plan` is what `--dry-run` runs alone. Neither module imports `record`. | one judgement, one writer; the dry run IS the plan |
| C15 | **Tests build the three trace shapes synthetically** (`TraceWriter`, `helpers.rust_trace`, `ts_traces.ts_trace`) with plaintext envs, payloads, output rows, `unwind_exc` and `children` planted, plus the committed format-1 fixture copied with a firing name added to its env; the CLI is exercised through `helpers.run_cli`; every predicate in C3, C5, C7–C11 is mutation-checked. One corpus case, `corpus/redact_retrofit` (Python), records under `env: {SENSORIUM_NO_REDACT: "1", SENSORIUM_CORPUS_TOKEN: …}` — the harness merges a case's `env:` last — and its questions run `redact $RUN --dry-run`, `redact $RUN`, then `info $RUN` (`by retrofit`) and `grep $RUN <name> --kind RETURN` (the marker, never the value); the harness's `expect_absent` sweep holds the token off every output. | the recorders' own test pattern; the corpus is the end-to-end proof |
| C16 | **E16 part C is its own instrument** — `tests/acceptance_e16/e16c.py`, `e16c.sh`, `e16c_cells.py`, `assemble_e16c.py`, `tests/test_acceptance_e16c_cells.py` — reusing part A's `_run`, `_grep_counts`, `_stat_tree`, `_sha8`, `Refused` and the phase/timer machinery. Phases: `preflight` (critical: the live store exists, `redaction.key` present, the venv's `sensorium` is this branch's), `copy` (critical: `cp -a` of `traces/` and `redaction.key` into `$E16_DIR/store-c/`, the token's VALUE read from one trace's `meta.env` under `CLAUDE_CODE_MESSAGING_TOKEN`, never printed, sha256 prefix recorded), `count-before` (critical: the number of `*.db` files, and the grep of the value over the copy must be non-zero in every trace — H4's premise), `dry-run`, `real`, `compare` (stdout equality), `grep-after`, `info` (every trace, exit code and the `by` word), `modes` (reported, not gated). H4 PASS iff: every trace's dry-run line names `CLAUDE_CODE_MESSAGING_TOKEN`; every grep count after is 0; every `info` exits 0; dry-run stdout == real stdout. The instrument's rehearsal (`E16_DRY=1`) runs the same phases on a FABRICATED store of three synthetic traces holding a `dry-` decoy, never on the live store's copy. Kill rules: each command 600 s, the part 30 min. | one instrument per part, on the house pattern; H4's four clauses read as four cells of one verdict |
| C17 | **The record** gains `## 4. Part C` holding `Not yet measured.` at Task 0, and §1 gains `### 2026-09-15 — Part C's pre-registration (amendment, beside the locked text above)` = the plan's `## Pre-registration (…)` block verbatim; `tests/test_acceptance_e16_lock.py` gains the fourth `SECTIONS` row and `test_part_c_begins_not_yet_measured_or_a_measured_heading`. H4's rule text is §9's, unchanged; the pin `273` is §9's expectation, and §4 records the count the copy actually held. | the lock pattern A and B established |
| C18 | **The live retrofit of `~/.sensorium` is NOT in the PR.** It runs on this box after the merge, with the reinstalled 0.17.0 tool, as a recorded chore — Brice's pre-authorisation is conditional on §4 reading H4 PASS, and a chore on one box is not a repository change. | destructive actions are Brice's; the condition is the record |
| C19 | **Versions:** Python **0.17.0**; `sensorium-rt`, `cargo-sensorium`, `sensorium-ts`, `sensorium-transform` untouched (no runtime, converter or probe changes). `TRACE_FORMAT` stays 4 (`by: "retrofit"` was §4.3's from PR A). The CHANGELOG (799 lines) takes the 0.17.0 entry only after `0.11.0` and `0.10.0` (162 lines) move to `CHANGELOG-ARCHIVE-2.md` (479 → 641) on the numbered-volume rule. README (796) is edited net-zero; `docs/query.md` (798) and `docs/TRACE-FORMAT.md` (797) are not touched — the command's documentation is `docs/redaction.md`'s new section *The retrofit: `sensorium redact`*, which replaces *Coming in later versions* and the limit "A trace that predates the rule is not covered by it". | the ceilings, measured |
| C20 | **What `redact` does not do, named:** it does not reach spools (§11), other stores (§11), `invocations.jsonl`, or the command lines §2 keeps; it does not re-key a store; it does not reverse anything (`seal` is §11's); it holds no lock across traces, so two concurrent `--all` runs contend per trace through C7's tmp and each refuses what the other holds. | §11, restated where a reader of C looks |

### 2026-09-16 — PR C shipped: the plan's decisions, the controller's rulings, and where the code differs

PR C (`docs/superpowers/plans/2026-09-15-sensorium-redaction-c.md`, Tasks
0–9) is the last of the three. Nothing in §§1–12 above is edited; this
section says what shipped, what was ruled while it shipped, and every place
the code and the sections above disagree. Where they disagree, **the code as
landed is what the docs describe**. The `PR C designed` section's C1–C20 are
the decisions this one reports against.

#### (a) The plan's decisions P1–P14, as shipped

| # | as shipped |
|---|---|
| P1 | `plan()` is the whole judgement and `--dry-run` is `plan()` alone. Shipped as written: `Plan` carries `path`, `run`, `lang`, `refused`, `skipped`, `env_names`, `values`, `meta`, `payloads`, `unwinds`, `outputs` and `mode_before`, with `rewrites`/`tightens`/`changes` derived from them; `apply()` touches no row the plan did not name, and the command's two modes are one loop with a single branch around `apply`. |
| P2 | The stamp's `values` is ADDITIVE — the previous stamp's count (0 when absent) plus what this run took. Shipped as written, and it is the first entry in (c): C6 as written says the stamp holds what the trace HOLDS, and a content hit leaves text rather than a marker, so the sum of the hands' counts is the honest number. `Plan.values` is THIS run's; `meta["redaction"]["values"]` is the sum. |
| P3 | The stale-key sweep and the `traces/` mode clause both run under `--dry-run`. Shipped as written — which is what makes C10's byte-identity unconditional rather than conditional on the flags, and E16's clause 4 a diff of two byte strings. **R12** named its two corners, in (c). |
| P4 | A value already equal to the marker is never digested. Shipped as written: `_env_pass` skips a stored value equal to `redact.REDACTED`, and `redact_values.named` already returns a capture carrying `redacted` untouched. |
| P5 | The stamp is rewritten only when something else changed OR the trace was not already `mode: "on"`. Shipped as written (`if writes or payloads or unwinds or outputs or not already_on`): an already-`on` trace whose pass finds nothing prints `nothing to redact` and is not rewritten, even where the caller's knobs differ from the recorded ones. |
| P6 | An UNKEYED `mode: "on"` trace under a keyed store proceeds — null digests stay null, new ones are the store's, the stamp becomes `keyed: true` with the store's `key_id`. Shipped as written. The nuance is not in `docs/redaction.md`, which is true as it stands (a Task 6 minor, in CARRIED-DEBT). |
| P7 | The RETURN name rule reads `code_objects.qualname` for the event's `code_id`; a RETURN with no `code_id` takes `value()` only. Shipped as written. |
| P8 | Events are walked in id order in one pass, unchanged rows are never written, and equality is on the PARSED object (`new != obj`), not the text. Shipped as written; the parsed-vs-text half has no discriminating test (a Task 2 minor, in CARRIED-DEBT). |
| P9 | The corpus case records under `env: {SENSORIUM_NO_REDACT: "1", SENSORIUM_CORPUS_TOKEN: …}` and cannot pin the env line's `N`. Shipped as written, with **R13** moving the case's `truth` prose off a count and onto the variable's name. |
| P10 | The token is not minted: it is read from the copy's own traces through a read-only connection, never printed, and the record cites `sha256[:8]`. Shipped, **amended by R15**: it is read from EVERY trace, not the first, because the store holds four distinct values of it. |
| P11 | The rehearsal (`E16_DRY=1`) runs on a FABRICATED store and never on the live store's copy. Shipped, **amended by R14**: the `dry-` decoy is planted only where the NAME rule reaches it. |
| P12 | The measurement's copy is `cp -a` of `traces/` and `redaction.key`, sidecars included, refused if anything is in flight. Shipped as written — 273 traces, 273 `-wal` and 273 `-shm` copied, none in flight, 0.155 s. |
| P13 | H4's four clauses are four rows of one cell, PASS iff all four, `273` reported beside the copy's count and never gated. Shipped as written, with **R17** making clause 4 compare BYTES and a STOP outrank a drop in the verdict's read sentence. |
| P14 | The live retrofit is a post-merge chore, not a task (C18), conditional on §4 reading H4 PASS. Shipped as written: the condition is met, the chore is not yet run, and CARRIED-DEBT carries it. |

#### (b) The controller's rulings R1–R17

Each was ruled during execution and is in the plan's gitignored ledger with
its evidence. The third column is the cost the ruling was taken at.

| R | the ruling | cost if wrong |
|---|---|---|
| R1 | (pre-flight) `--dry-run` must not create `redaction.key`: `run()` uses `Key.load(root)` under `--dry-run` and `Key.load_or_create(root)` on a real run, because §7 says a dry run changes nothing and a key file is a store change. | on a keyless store the dry run's stamp would be unkeyed and the real run's keyed; the printed lines carry no digest, so stdout identity (C10) holds either way |
| R2 | The CHANGELOG's volume-2 pointer line reads `(0.8.7–0.11.0)` — the plan's literal was wrong (volume 2 holds 0.8.7 from the sixth cut), and a reader-facing range must be true. | none beyond a one-line docs edit |
| R3 | Box paths in a PLAN file under `docs/superpowers/plans` are allowed — plan B carries the same; the constraint binds code, living docs and the record outside its pin table, and plans are dated history that name where a measurement ran. No change. | a plan that names a box path nobody else has, which the pin table already does on purpose |
| R4 | `sweep_stale`: a middle that is not a POSITIVE int is treated like a non-int name and left alone, and anything `os.kill` raises other than `ProcessLookupError` reads as ALIVE (the file is kept) — liveness of a name we cannot check is unknown, and keeping a file is the safe direction. | a garbage tmp with an impossible pid is never swept (harmless; named in no output) |
| R5 | The plan's "≤ 300 lines at this task" is met in intent at 301 — no further trimming; the binding limits are the 800 ceiling and "no new file past 600 at creation". | one line |
| R6 | `plan()` catches `OSError` around `db.open_trace`/`all_meta` and a `ValueError` from a corrupt meta JSON as refusals (`cannot open: …` / `meta is not JSON: …`), so no exception escapes a `--all` walk (C9). | a refusal line where a traceback would have been |
| R7 | Task 3's own concern is to be CLOSED, not parked — a stale `-wal` serving plaintext back is the loud failure this slice exists to prevent, so the directory fsync is wrapped and the sidecar unlink runs after a successful replace whatever the fsync does; the 450-line cap is relaxed to 480 for it (R5's spirit). | recorded by the ledger's dated addendum (2026-09-16) rather than with the ruling: thirty more lines in the module for a closed plaintext window; none otherwise |
| R8 | `run()` passes `Knobs.from_environ(os.environ)` as read; `plan()` already forces `off=False`, so the brief's second `replace(off=False)` in `run()` is dropped as duplication and its mutation retargeted to `test_off_knobs_are_ignored_and_the_stamp_is_on`. R1 stands. | none — C4 is enforced at the one place that produces the stamp |
| R9 | Task 4's two deviations are ACCEPTED: the summary prints on EVERY invocation (the reading of C12 that gives the sweep count a home), and `redacted N` excludes refused and skipped plans (which keeps the summary's arithmetic true). | one extra line on single-trace runs |
| R10 | The per-target `plan()` call is wrapped in the same `except (OSError, sqlite3.Error, ValueError)` as `apply`, yielding `REFUSED: cannot judge: <e>`, so C9's "the others continue" holds for the residual escapes sqlite discovers lazily; `_dir_mode`'s stat/chmod `OSError` becomes a printed note and never a traceback. | a refusal line where a traceback was |
| R11 | The exit is ANSWERED when the directory was (or would be) tightened even if no plan changed; the plan's exit rule is amended. | exit 0 on a run that only `chmod`'ed a directory, which the epilog already promises |
| R12 | C10's byte-identity has two named corners, folded in as wording repairs: a keyless store (the dry run reads a key where the real run mints one, so a C5 refusal's key id says `none` in the first and an id in the second) and two CONSECUTIVE invocations (the dry run's sweep consumes the litter the real run would have counted). `cli.py`'s docstring hole is deferred to the debt list. | recorded by the ledger's dated addendum (2026-09-16) rather than with the ruling: none — a docstring sentence and a test name |
| R13 | Task 5's prose minor rides with Task 6 (a docs task): the case's `truth` says "the env line names `SENSORIUM_CORPUS_TOKEN` among however many variables the launching shell made fire" rather than a count. | none |
| R14 | The rehearsal's fabricated store plants the `dry-` decoy only where the NAME rule reaches it — the env, a `str` RETURN under a code named `secret`, a LINE delta named `token` — and NOT in an output row or a `children` element, because the content rule cannot see `dry-` and those would survive the retrofit and read as residue. **P11 is amended accordingly.** | the rehearsal exercises fewer sites than the measurement; the measurement is what counts |
| R15 | **Pre-launch amendment, recorded BESIDE §1 on the house pattern** (the locked block stays as written; the measured section's *Amendments, beside §1* names it): the instrument sweeps EVERY distinct value of `CLAUDE_CODE_MESSAGING_TOKEN` found across the copy's traces — `count-before` records the number of distinct values and requires each trace to hold ITS OWN value at least once, `grep-after` requires every value at 0 in every file, and the record cites each value's sha8 and its count, never a value. Strictly stronger than the pre-registered single-value reading, and the only honest one for a store whose token rotated. | none — a single-valued store is the special case |
| R16 | `e16c.py` at 553 lines is accepted (the 400 was a hint; the ceiling is 800; part B's `e16b.py` is 537). | recorded by the ledger's dated addendum (2026-09-16) rather than with the ruling: none — a longer instrument file, still under the 800 gate |
| R17 | The fix round also takes four of Task 7's minors: clause 4 compares BYTES (capture bytes, decode only for parsing); a STOP outranks a drop in `h4`'s read sentence, naming both; a non-dict `env` is a `copy` refusal; a no-op conditional goes. The three docstring/test-pin repairs ride with them, the same functions being open. | none beyond the diff |

#### (c) Where the shipped code differs from §7 and C1–C20

Fifteen. Each is a place a reader of the sections above would be told
something the code does not do.

1. **C6's `values` is ADDITIVE** (decision **P2**). C6 says the stamp's
   `values` is "what the trace HOLDS after the pass … every capture
   carrying `redacted`, every output row and `unwind_exc`/`exc` with a
   content hit, every `children` element with a hit". A content hit leaves
   TEXT, not a marker, so that quantity is not recoverable from the trace;
   shipped, the stamp carries the PREVIOUS stamp's `values` plus this
   run's count, and the per-trace line prints this run's alone. Where:
   `redact_store._judge`, `docs/redaction.md`.
2. **C10's identity holds unconditionally, and has two corners**
   (**P3**, **R12**). The sweep and the `traces/` clause run in BOTH
   modes, so the two stdouts do not differ exactly when a reader is
   comparing them. Named rather than left to be discovered: on a store with
   no `redaction.key` the dry run READS a key where the real run MINTS one,
   so a C5 refusal naming the store's key says `none` in one and an id in
   the other; and across two CONSECUTIVE invocations the dry run's sweep
   consumes the litter the run after it would have counted. Where:
   `redact_cmd`'s docstring, `docs/redaction.md`.
3. **The summary prints on EVERY invocation** (**R9**). C12's summary sits
   under an `--all` example; shipped, `redact <run>` prints it too, because
   the sweep count has nowhere else to go. Where: `redact_cmd.run`.
4. **`redacted N` excludes refused and skipped plans** (**R9**). A plan
   whose `apply` raised carries both the rows it wanted to write and the
   sentence saying it could not; counting it as done AND refused would
   leave C12's four numbers unable to add up to the traces walked. Where:
   `redact_cmd.summary`, and its docstring says so.
5. **A judgement that RAISES is a refusal** (**R6**, **R10**). C9 names
   seven foreseen refusals; sqlite reads pages lazily, so a corrupt row, a
   payload that is not JSON or a file another process moved can surface
   from inside the walk. Shipped, `plan()` is wrapped in the command in the
   same `except (OSError, sqlite3.Error, ValueError)` as `apply`, printing
   `REFUSED: cannot judge: <e>`; `plan()` itself names `cannot open: …` and
   `meta is not JSON: …`. Where: `redact_cmd.run`, `redact_store.plan`.
6. **A tightened DIRECTORY alone exits 0** (**R11**). C11 makes a
   mode-only tightening a CHANGE for a trace and says nothing about a store
   of settled traces whose `traces/` was 0755. Shipped, the exit predicate
   is `dir_mode or any(p.changes)`: exit 1 there would tell a script the
   pass was a no-op on the run it had just tightened. Where:
   `redact_cmd.run`, and the parser epilog promises it.
7. **A dry run loads the key and never creates it** (**R1**). Neither §7
   nor C7 says which; shipped, `Key.load` under `--dry-run` and
   `Key.load_or_create` on a real run, a key file being a store change.
   Where: `redact_cmd.run`.
8. **`plan()` forces `off=False`, and the command does not repeat it**
   (**R8**). C4 says `SENSORIUM_NO_REDACT` is ignored without saying where.
   Shipped, at the one point the knobs enter the judgement — so the
   judgement is incapable of obeying it, and a stale export in somebody's
   shell profile cannot turn a retrofit into a no-op that still prints
   lines. Where: `redact_store.plan`, with `redact_cmd`'s docstring saying
   why it is not repeated.
9. **`sweep_stale` reads a non-positive middle as a name, not a pid**
   (**R4**). C13 says "every `redaction.key.<pid>.tmp` whose pid is not
   alive"; `os.kill` treats a negative number as a process GROUP, so a
   middle that is not a POSITIVE int is left alone exactly as `abc` is,
   and every exception but `ProcessLookupError` reads as ALIVE. Where:
   `redact_key.sweep_stale`, `_pid_alive`.
10. **The sidecar unlink is in a `finally` after the rename** (**R7**).
    C7's order is backup → rewrite → checkpoint → fsync → rename →
    sidecars; shipped, the directory fsync between the last two is wrapped,
    because a raise there (or a Ctrl-C, `except BaseException` catching it)
    would leave the displaced inode's `-wal` beside the rewritten file for
    the next reader to recover plaintext out of. The cleanup handler
    unlinks the tmp BEFORE its sidecars, so a failure in the second cannot
    leave the first. Where: `redact_store.apply`.
11. **The rehearsal plants the decoy at NAME-rule sites only** (**R14**,
    amending **P11**). The content rule cannot see `dry-`, so a decoy in an
    output row or a `children` element would survive the retrofit and make
    the rehearsal's `grep-after` read as residue. Where:
    `tests/acceptance_e16/e16c.py::fabricate`.
12. **The instrument sweeps a SET of token values** (**R15**, amending
    **P10** and §1's pre-registration). C16 and P13 read the token as one
    value from one trace; the store holds four, the token having rotated
    over its life, and the first `*.db` in sorted order carries the one
    held by 11 of 273 traces. Where: `e16c.py`'s `copy`, `count_before`
    and `grep_after`, and the record's *Amendments, beside §1*.
13. **File sizes accepted over the plan's hints** (**R5**, **R16**).
    `src/sensorium/redact_store.py` is 462 lines against a ≤300 hint at
    Task 2 and a 480 cap at Task 3; `tests/acceptance_e16/e16c.py` is 727
    against a 400 hint. The binding limits are the 800 ceiling and "no new
    file past 600 at creation", and both are met.
14. **C19's CHANGELOG arithmetic moved** (**R2**). The cut ran as
    designed — 0.11.0 and 0.10.0 out before the 0.17.0 entry was written —
    but `CHANGELOG-ARCHIVE-2.md` came to **644** rather than the planned
    641, the live file to **684**, the pointer range to **0.8.7–0.11.0**
    rather than the plan's 0.9.0, and the entry itself to 46 lines against
    a 40-line hint.
15. **The corpus case runs FIVE questions, not C15's four.** A second
    `redact $RUN` pass was added, pinning `nothing to redact; mode 600` at
    exit 1 — idempotence (**C5**, **P5**) proved end to end rather than
    only in a unit test. Where: `corpus/redact_retrofit/questions.yaml`.

#### (d) E16 part C's outcome

Measured **once**, 2026-09-16, 28.8 s wall clock, under `e16c.sh` after two
rehearsals on fabricated stores: **DONE** — **H4 PASS**, all four clauses,
on a `cp -a` COPY of `~/.sensorium/traces` and its `redaction.key`. The
copy held **273** traces against §9's 273; the live store was read and
never written, its own retrofit being a post-merge chore (**C18**).

| clause | what was read | word |
|---|---|---|
| 1 — every `*.db` has a dry-run line naming `CLAUDE_CODE_MESSAGING_TOKEN` | 273 traces, every one named in the dry run | **PASS** |
| 2 — every `grep -rc` count over the copy is 0 after the real run | 0 occurrences in 275 files | **PASS** |
| 3 — `info` exits 0 on every trace and reads `by retrofit` | 273/273 | **PASS** |
| 4 — the dry run's stdout is the real run's, byte for byte | `sha256` `f73437dcc1f03e5e` both | **PASS** |

The token was not minted (**P10**) and it is not one value: the traces held
**four** distinct values of that variable — `sha256[:8]` `41285dda` (254
traces), `61e4ad5f` (11), `876f167c` (5), `426ae10d` (3) — the token having
rotated over the store's life. Each was read from its own trace's
`meta.env` through a read-only connection, swept one at a time, never
printed and never written anywhere but `grep`'s own argument (**R15**). Both
passes exited 0 and printed the same summary: `redacted 273 of 273 traces
(0 already clean, 0 skipped, 0 refused); spools under target/ and the
TypeScript spool dirs are not reached; traces/ mode 775 -> 700` — the dry
run in 6.619 s, the real run in 7.982 s. Before the pass the copy held 273
`-wal` and 273 `-shm` files; after it, none, and 275 of 275 files at 0600
with `traces/` at 0700. The reading is in
`docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md` §4, with
the four-clause table, the count lines, the before-and-after table, the
phase timings and the dry runs' five findings, and **R15** recorded as an
amendment beside §1's locked text rather than edited into it.
