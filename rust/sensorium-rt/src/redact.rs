//! Rule v1: which NAMES hold a secret, the knobs that amend that judgement,
//! and the key the digests are taken under.
//!
//! This runtime stored the whole process environment in plaintext until this
//! slice, at 0644, so a trace of any program launched from a developer's shell
//! held whatever that shell was carrying. Rule v1 replaces such a value with
//! `<redacted>` at the WRITER, before anything reaches disk, and keeps an
//! HMAC-SHA256 of the plaintext beside it so a reader can still say "this
//! changed" without being told what it changed to.
//!
//! WHAT THIS IS NOT
//! ----------------
//! **Not a secret scanner.** The rule fires on a name's SEGMENTS, so a secret
//! in a variable called `x`, or one this set has never heard of, is stored as
//! typed. Matching is segment-exact, never substring: substring `KEY` would
//! fire on `MONKEY_PATCH` and substring `PASS` on `BYPASS_CACHE`.
//! `SENSORIUM_REDACT_NAMES` is the remedy for a name this misses and
//! `SENSORIUM_REDACT_ALLOW` for one it wrongly fires on, and both are recorded
//! so a reader sees what the recording was made under.
//!
//! THE FIXTURE
//! -----------
//! `docs/trace-format/redaction-v1.json` holds every `split` and `fires` case,
//! and the Python recorder's suite, the TypeScript recorder's suite and
//! `tests/redact.rs` read the SAME file. A case belongs there, not in a test
//! module: three implementations of one rule agree only on what all three are
//! asked.
//!
//! THE KEY
//! -------
//! This runtime only ever PARSES `SENSORIUM_REDACT_KEY`, which a driver hands
//! it. It never creates a key, never writes one and never reads a key file:
//! creating one means a directory, a temporary, a link and a race, and the
//! runtime is linked into somebody else's program. An absent, short, long or
//! non-hex value is simply unkeyed -- the names are still redacted, and the
//! header says `keyed: false` so nobody mistakes a missing digest for a value
//! that did not change.
//!
//! Public because the integration suite reads the shared fixture and drives
//! these functions directly; nothing outside this crate is expected to call
//! them.

use std::sync::OnceLock;

use crate::json::push_json_str;
use crate::sha256::{hex_prefix, Sha256};

/// The rule's identity, stamped in every header it touches. A later rule is
/// v2; v1 is never amended, because a trace that says `v1` has to mean one
/// thing forever.
pub const RULE: &str = "v1";

/// What a whole-redacted value reads as.
pub const REDACTED: &str = "<redacted>";

/// The hex key a driver hands a recorded process. DELETED from every recorded
/// environment rather than redacted: a digest of the key under the key is a
/// pointless row, and `keyed: true` already implies it.
pub const KEY_VAR: &str = "SENSORIUM_REDACT_KEY";

const OFF_VAR: &str = "SENSORIUM_NO_REDACT";
const NAMES_VAR: &str = "SENSORIUM_REDACT_NAMES";
const ALLOW_VAR: &str = "SENSORIUM_REDACT_ALLOW";

/// A segment here fires the rule. Every one of them has a firing case in the
/// fixture. The four compounds (`APIKEY`, `ACCESSKEY`, `SECRETKEY`,
/// `AUTHTOKEN`) exist because a name written as one word -- `apikey` -- splits
/// into one segment that none of `API`, `KEY` matches.
const SEGMENTS: [&str; 25] = [
    "KEY",
    "APIKEY",
    "TOKEN",
    "SECRET",
    "SECRETS",
    "PASSWORD",
    "PASSWD",
    "PASSPHRASE",
    "PASS",
    "AUTH",
    "AUTHORIZATION",
    "CREDENTIAL",
    "CREDENTIALS",
    "CREDS",
    "PRIVATE",
    "COOKIE",
    "COOKIES",
    "SIGNATURE",
    "BEARER",
    "JWT",
    "DSN",
    "ACCESSKEY",
    "SECRETKEY",
    "AUTHTOKEN",
    "PWD",
];

/// `PWD` fires only as a segment of a LONGER name: `MYSQL_PWD` and `DB_PWD`
/// are passwords, and `PWD` and `OLDPWD` are the shell's working directory, on
/// every machine that has ever run a shell.
const PWD: &str = "PWD";

/// Whole NORMALISED names that fire whatever their segments say. Segment-exact
/// matching cannot see inside a compound word: `PGPASSWORD` splits into the
/// single segment `PGPASSWORD`, which is neither `PG` nor `PASSWORD`. Short by
/// design: a name earns a place only when a census or a report shows it
/// matters, never on imagination.
const EXACT: [&str; 1] = ["PGPASSWORD"];

/// How many bytes a key is. Public because the DRIVER mints the file this
/// runtime only ever parses a hex form of (`cargo-sensorium/src/
/// redaction_key.rs`), and one number decides both: a driver that wrote 24
/// bytes would produce a store every recorder reads as unkeyed, with nothing
/// on either side saying why.
pub const KEY_BYTES: usize = 32;

/// SHA-256's block, which is HMAC's block.
const HMAC_BLOCK: usize = 64;

// ---------------------------------------------------------------------------
// The name rule
// ---------------------------------------------------------------------------

/// `name`'s uppercased segments: `apiKey` -> `[API, KEY]`, `SSH_AUTH_SOCK` ->
/// `[SSH, AUTH, SOCK]`, `XAUTHORITY` -> `[XAUTHORITY]`. Empty segments are
/// dropped, so `__init__` is `[INIT]` and `""` is `[]`.
///
/// The rule is SPECIFIED as two regex substitutions and then a split on runs of
/// non-alphanumerics (`src/sensorium/redact.py`). This crate has no regex
/// engine and will not grow one, so it walks the name once and decides each
/// boundary in place; `tests/redact.rs` runs both spellings over every name up
/// to five characters long out of an alphabet that has every class the two
/// patterns can tell apart, which is what says the rewrite kept the rule.
#[must_use]
pub fn split(name: &str) -> Vec<String> {
    let chars: Vec<char> = name.chars().collect();
    let mut out: Vec<String> = Vec::new();
    let mut current = String::new();
    for (i, c) in chars.iter().enumerate() {
        if !c.is_ascii_alphanumeric() {
            if !current.is_empty() {
                out.push(std::mem::take(&mut current));
            }
            continue;
        }
        if i > 0 && !current.is_empty() && starts_a_segment(&chars, i) {
            out.push(std::mem::take(&mut current));
        }
        current.push(c.to_ascii_uppercase());
    }
    if !current.is_empty() {
        out.push(current);
    }
    out
}

/// Whether `chars[i]` opens a new segment, by the two camelCase boundaries the
/// rule names, in that order.
fn starts_a_segment(chars: &[char], i: usize) -> bool {
    let (prev, cur) = (chars[i - 1], chars[i]);
    if !cur.is_ascii_uppercase() {
        return false;
    }
    // `apiKey` -> API KEY: a lowercase or a digit, then an uppercase.
    if prev.is_ascii_lowercase() || prev.is_ascii_digit() {
        return true;
    }
    // `HTTPToken` -> HTTP TOKEN: inside an uppercase RUN, the last uppercase
    // before a lowercase is where the next word begins.
    prev.is_ascii_uppercase() && chars.get(i + 1).is_some_and(char::is_ascii_lowercase)
}

/// The comparison form the two knobs use: the segments, joined. So `myco_dsn`,
/// `MYCO_DSN` and `mycoDsn` are one name to a user's list.
#[must_use]
pub fn normalise(name: &str) -> String {
    split(name).concat()
}

/// The three environment variables, as read once at record time.
///
/// `names` and `allow` are held NORMALISED and SORTED, so a comparison against
/// a variable's own normalised form is exact and case-blind at once, and the
/// header records one list for one set of knobs whatever order they were
/// written in.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Knobs {
    pub off: bool,
    pub names: Vec<String>,
    pub allow: Vec<String>,
}

impl Knobs {
    /// The knobs this process was started with.
    #[must_use]
    pub fn from_env() -> Knobs {
        let read = |var: &str| std::env::var_os(var).map(|v| v.to_string_lossy().into_owned());
        Knobs::from_values(
            read(OFF_VAR).as_deref(),
            read(NAMES_VAR).as_deref(),
            read(ALLOW_VAR).as_deref(),
        )
    }

    /// The same, from the three values themselves.
    ///
    /// Separate from [`Knobs::from_env`] so that a test can state a knob
    /// without setting a process-wide environment variable underneath every
    /// other test in the binary -- and so that the fixture's knob cases run
    /// through the same comma parsing a real recording does.
    #[must_use]
    pub fn from_values(off: Option<&str>, names: Option<&str>, allow: Option<&str>) -> Knobs {
        Knobs {
            // Reads like `SENSORIUM_NO_INVOCATION_LOG`: any non-empty value
            // other than `"0"` turns the rule off, and `=0`, empty and unset
            // all leave it on.
            off: matches!(off, Some(v) if !v.is_empty() && v != "0"),
            names: listed(names),
            allow: listed(allow),
        }
    }
}

/// A comma list, trimmed, empties dropped, each entry normalised, sorted and
/// deduplicated. An entry that normalises to nothing (`","`, `"-"`) is dropped
/// too -- an empty string in the list would match a nameless value.
fn listed(raw: Option<&str>) -> Vec<String> {
    let mut out: Vec<String> = raw
        .unwrap_or("")
        .split(',')
        .map(|part| normalise(part.trim()))
        .filter(|n| !n.is_empty())
        .collect();
    out.sort();
    out.dedup();
    out
}

/// Whether the name rule fires on `name`.
///
/// Allow first, and it WINS over `names` -- a user's statement about their own
/// variable outranks their own list. Then `EXACT`, then the segments.
/// `knobs.off` is not read here: turning the whole rule off is
/// [`redact_env`]'s business, one level up, so that this function stays the
/// answer to "is this a secret-shaped name".
#[must_use]
pub fn fires(name: &str, knobs: &Knobs) -> bool {
    let segments = split(name);
    let normalised = segments.concat();
    // A LINEAR scan, not a binary search over the sorted fields. `Knobs` is a
    // public struct with public fields, and a `Knobs` some other hand built
    // with an unsorted list would make a binary search miss -- silently, and
    // the price of a miss here is a plaintext secret on disk. The lists are
    // two or three entries long.
    if knobs.allow.iter().any(|a| a == &normalised) {
        return false;
    }
    if knobs.names.iter().any(|n| n == &normalised) {
        return true;
    }
    if EXACT.contains(&normalised.as_str()) {
        return true;
    }
    let multi = segments.len() > 1;
    segments
        .iter()
        .any(|s| SEGMENTS.contains(&s.as_str()) && (multi || s.as_str() != PWD))
}

// ---------------------------------------------------------------------------
// The key and the digest
// ---------------------------------------------------------------------------

/// The store's redaction key: 32 bytes, or none of them.
///
/// Never fails, on any path. `None` is the whole of the unkeyed state --
/// `keyed`, `key_id` and `digest` all read from it.
pub struct Key(Option<[u8; KEY_BYTES]>);

impl Key {
    /// The key `SENSORIUM_REDACT_KEY` carries, if it carries one.
    #[must_use]
    pub fn from_env() -> Key {
        Key::from_hex(
            std::env::var_os(KEY_VAR)
                .and_then(|v| v.into_string().ok())
                .as_deref(),
        )
    }

    /// Exactly 64 hex characters and nothing else: a key that arrived down a
    /// wire between two implementations is checked for the shape it was
    /// promised in, and anything else is unkeyed rather than an error -- a
    /// recorder that refused to record over a malformed knob would cost the
    /// whole run.
    #[must_use]
    pub fn from_hex(text: Option<&str>) -> Key {
        let Some(text) = text else {
            return Key(None);
        };
        if text.len() != 2 * KEY_BYTES {
            return Key(None);
        }
        let hex = text.as_bytes();
        let mut material = [0u8; KEY_BYTES];
        for (i, byte) in material.iter_mut().enumerate() {
            match (nibble(hex[2 * i]), nibble(hex[2 * i + 1])) {
                (Some(hi), Some(lo)) => *byte = (hi << 4) | lo,
                _ => return Key(None),
            }
        }
        Key(Some(material))
    }

    /// The key as its raw bytes -- what a driver that MINTED one, or read one
    /// out of `<store>/redaction.key`, is holding.
    ///
    /// Anything but exactly [`KEY_BYTES`] is unkeyed, for the reason
    /// [`Key::from_hex`] treats a malformed hex string that way: a truncated
    /// or padded key file is somebody else's file, and a recorder that
    /// refused to record over it would cost the whole run.
    #[must_use]
    pub fn from_bytes(material: &[u8]) -> Key {
        match <[u8; KEY_BYTES]>::try_from(material) {
            Ok(bytes) => Key(Some(bytes)),
            Err(_) => Key(None),
        }
    }

    /// The 64-character form [`Key::from_hex`] reads, or `None` when there is
    /// no key -- exactly what [`KEY_VAR`] carries between a driver and the
    /// process it records.
    ///
    /// The inverse of `from_hex` and spelled beside it on purpose: the two are
    /// the whole of the hop between two processes, and a driver that formatted
    /// the hex itself would be the second spelling of a wire format.
    #[must_use]
    pub fn to_hex(&self) -> Option<String> {
        let material = self.0.as_ref()?;
        let mut out = String::with_capacity(2 * KEY_BYTES);
        for byte in material {
            out.push(HEX_DIGITS[(byte >> 4) as usize] as char);
            out.push(HEX_DIGITS[(byte & 0xf) as usize] as char);
        }
        Some(out)
    }

    #[must_use]
    pub fn keyed(&self) -> bool {
        self.0.is_some()
    }

    /// `SHA-256(key)`, first 8 hex: whether two traces' digests are comparable
    /// at all.
    #[must_use]
    pub fn key_id(&self) -> Option<String> {
        let material = self.0.as_ref()?;
        let mut h = Sha256::new();
        h.update(material);
        Some(hex_prefix(&h.finish(), 8))
    }

    /// `HMAC-SHA256(key, text)`, first 16 hex -- an equality identity, not a
    /// commitment -- or `None` when there is no key.
    ///
    /// The UTF-8 bytes of the value as this runtime holds it. A `String`
    /// cannot hold a lone surrogate, and an environment value that was not
    /// UTF-8 was already replaced character by character on its way in
    /// (`to_string_lossy`), so what is hashed here is exactly what is stored.
    #[must_use]
    pub fn digest(&self, text: &str) -> Option<String> {
        let material = self.0.as_ref()?;
        Some(hex_prefix(&hmac_sha256(material, text.as_bytes()), 16))
    }
}

/// The digits [`Key::to_hex`] writes and [`nibble`] reads back. Lowercase,
/// which is the only form this format writes hex in.
const HEX_DIGITS: &[u8; 16] = b"0123456789abcdef";

fn nibble(c: u8) -> Option<u8> {
    match c {
        b'0'..=b'9' => Some(c - b'0'),
        b'a'..=b'f' => Some(c - b'a' + 10),
        b'A'..=b'F' => Some(c - b'A' + 10),
        _ => None,
    }
}

/// HMAC-SHA256 (RFC 2104) over this crate's own SHA-256.
///
/// A key longer than the block is hashed first and a shorter one is
/// zero-padded to it; `inner = H(k ^ 0x36 || msg)` and the digest is
/// `H(k ^ 0x5c || inner)`. `tests/redact.rs` holds it to two RFC 4231 vectors,
/// one for each key length branch: an implementation that is merely
/// self-consistent passes neither.
#[must_use]
pub fn hmac_sha256(key: &[u8], msg: &[u8]) -> [u8; 32] {
    let mut padded = [0u8; HMAC_BLOCK];
    if key.len() > HMAC_BLOCK {
        let mut h = Sha256::new();
        h.update(key);
        padded[..32].copy_from_slice(&h.finish());
    } else {
        padded[..key.len()].copy_from_slice(key);
    }

    let mut ipad = [0x36u8; HMAC_BLOCK];
    let mut opad = [0x5cu8; HMAC_BLOCK];
    for ((i, o), k) in ipad.iter_mut().zip(opad.iter_mut()).zip(padded.iter()) {
        *i ^= k;
        *o ^= k;
    }

    let mut inner = Sha256::new();
    inner.update(&ipad);
    inner.update(msg);
    let inner = inner.finish();

    let mut outer = Sha256::new();
    outer.update(&opad);
    outer.update(&inner);
    outer.finish()
}

// ---------------------------------------------------------------------------
// The environment
// ---------------------------------------------------------------------------

/// One row per name the rule fired on: the name, and its digest when there was
/// a key to take one under.
pub type Table = Vec<(String, Option<String>)>;

/// (the environment to STORE, the name -> digest table for the header).
///
/// A new vector either way, minus [`KEY_VAR`]. With the rule off that deletion
/// is the only thing that happens, and the header's `mode: "off"` says so, so
/// a reader knows the plaintext was recorded on purpose.
///
/// The table comes out in the ORDER THE ENVIRONMENT ARRIVED IN, and the only
/// caller hands it over sorted (`spool::sorted_env`), which is what satisfies
/// R13 -- one environment gives one table, byte for byte, whichever language
/// wrote it. Keep that caller sorted; sorting again here would hide the day it
/// stops being.
#[must_use]
pub fn redact_env(
    env: Vec<(String, String)>,
    key: &Key,
    knobs: &Knobs,
) -> (Vec<(String, String)>, Table) {
    let mut stored: Vec<(String, String)> = Vec::with_capacity(env.len());
    let mut table = Table::new();
    for (name, value) in env {
        if name == KEY_VAR {
            continue;
        }
        if !knobs.off && fires(&name, knobs) {
            table.push((name.clone(), key.digest(&value)));
            stored.push((name, REDACTED.to_owned()));
        } else {
            stored.push((name, value));
        }
    }
    (stored, table)
}

/// `sha256` over `"\n".join(f"{k}={v}")` for the sorted environment, first 16
/// hex characters.
///
/// **Deliberately not the Python recorder's formula.** `src/sensorium/record/
/// boot.py` hashes `json.dumps(env, sort_keys=True)`; this hashes the plan's
/// `"{k}={v}"` join. Ruled 2026-09-02: `env_hash` is a per-recorder identity,
/// compared only between traces from the same recorder, and no command
/// compares one across languages. Each is stable within its own language,
/// which is the whole of what the key is for.
///
/// Here, beside [`redact_env`], because the hash is taken over what that
/// function RETURNS -- the environment the trace will hold, not the one the
/// process was started with. `spool::write_proc_header` takes it that way, and
/// so does the converter when it applies the rule to a header written before
/// the rule existed (`cargo-sensorium/src/convert/redaction.rs`): two callers,
/// one formula, because a second spelling is a store whose traces stop
/// comparing.
#[must_use]
pub fn env_hash(env: &[(String, String)]) -> String {
    let mut h = Sha256::new();
    for (i, (k, v)) in env.iter().enumerate() {
        if i > 0 {
            h.update(b"\n");
        }
        h.update(k.as_bytes());
        h.update(b"=");
        h.update(v.as_bytes());
    }
    hex_prefix(&h.finish(), 16)
}

/// The header's `redaction` object, in the format's key order.
///
/// Off is TWO keys and no more: a header that named a key or a knob list while
/// claiming to have applied nothing would invite a reader to believe the
/// plaintext beside it had been considered. The converter adds `env` and `by`
/// to this object later; the runtime writes what the runtime knows.
#[must_use]
pub fn redaction_json(key: &Key, knobs: &Knobs) -> String {
    let mut out = String::with_capacity(128);
    out.push_str("{\"rule\":");
    push_json_str(&mut out, RULE);
    if knobs.off {
        out.push_str(",\"mode\":\"off\"}");
        return out;
    }
    out.push_str(",\"mode\":\"on\",\"keyed\":");
    out.push_str(if key.keyed() { "true" } else { "false" });
    out.push_str(",\"key_id\":");
    match key.key_id() {
        Some(id) => push_json_str(&mut out, &id),
        None => out.push_str("null"),
    }
    out.push_str(",\"names\":");
    push_json_list(&mut out, &knobs.names);
    out.push_str(",\"allow\":");
    push_json_list(&mut out, &knobs.allow);
    out.push('}');
    out
}

// ---------------------------------------------------------------------------
// The header's redaction plumbing
// ---------------------------------------------------------------------------

/// The redaction knobs and the key, read ONCE per process.
///
/// The header is rewritten at every unit registration -- 77 times on a
/// bloomery invocation -- and a rule that re-read its own knobs each time
/// would let a program that edits its own environment mid-run produce a trace
/// whose header contradicts the values already in it.
fn knobs() -> &'static Knobs {
    static KNOBS: OnceLock<Knobs> = OnceLock::new();
    KNOBS.get_or_init(Knobs::from_env)
}

fn key() -> &'static Key {
    static KEY: OnceLock<Key> = OnceLock::new();
    KEY.get_or_init(Key::from_env)
}

/// [`redact_env`] under this process's own key and knobs: the environment to
/// STORE, and the table its siblings are written from.
///
/// Paired with [`push_header_siblings`], and split from it only because
/// `env_hash` goes between the two -- the hash is taken over the environment
/// this returns, and the siblings are written after it.
pub(crate) fn redact_process_env(env: Vec<(String, String)>) -> (Vec<(String, String)>, Table) {
    redact_env(env, key(), knobs())
}

/// `,"env_redaction":{..},"redaction":{..}` -- the two header keys that say
/// what the rule did, appended after `env_hash`.
///
/// The table is written in the order it arrived in, which is sorted because
/// `spool::sorted_env` sorts (R13).
pub(crate) fn push_header_siblings(json: &mut String, table: &Table) {
    json.push_str(",\"env_redaction\":{");
    for (i, (name, digest)) in table.iter().enumerate() {
        if i > 0 {
            json.push(',');
        }
        push_json_str(json, name);
        json.push(':');
        match digest {
            Some(d) => push_json_str(json, d),
            None => json.push_str("null"),
        }
    }
    json.push_str("},\"redaction\":");
    json.push_str(&redaction_json(key(), knobs()));
}

fn push_json_list(out: &mut String, items: &[String]) {
    out.push('[');
    for (i, item) in items.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        push_json_str(out, item);
    }
    out.push(']');
}
