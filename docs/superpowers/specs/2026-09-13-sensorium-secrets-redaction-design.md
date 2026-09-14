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

#### (d) E16 part A's outcome

Run 1 (2026-09-14) read **DONE-WITH-STOP** — H1 PASS, H2 STOP (ten paths at
0664/0775), H3 STOP (the Rust branch's `SENSORIUM_`-prefix exclusion granted
a licence over a rotated token), H6 PASS. Run 2, measured from zero with a
fresh token after `6a719e4`, `1f60dd6`, `9d8f16a` and `e36d5dd`, read **DONE**
— H1, H2, H3, H6 all PASS; both readings are in
`docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md` §2, run 1
byte-untouched beneath run 2, with the per-cell statement of which run is the
first PASS.
