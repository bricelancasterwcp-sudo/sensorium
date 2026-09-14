//! What a trace's `redaction` key says, the rule applied to a proc header too
//! old to carry one, and rule v1 over every VALUE this converter writes.
//!
//! THE ENVIRONMENT HALF
//! --------------------
//! Two paths, and which one a header takes is decided by whether the RECORDER
//! already ran the rule over its environment:
//!
//! * **The recorder ran it** (`sensorium-rt 0.6.0` and later). The header's
//!   own `redaction` object is what the trace says, carried through untouched
//!   but for the keys only the converter can fill in -- `env`, the name ->
//!   digest table the runtime wrote beside it, `by`, the last hand that
//!   applied the rule, and `values`, the count below. The stored environment
//!   and its `env_hash` are the recorder's and are not recomputed: the runtime
//!   hashed what it wrote, and a second hash taken here could only differ by
//!   being wrong.
//! * **The recorder did not** (`sensorium-rt 0.5.0` and earlier). Those spools
//!   hold the whole launching environment in plaintext, and a converter that
//!   passed them through would write today's trace with yesterday's secrets in
//!   it. The rule runs HERE instead, and `env_hash` is recomputed because the
//!   environment being hashed has changed.
//!
//! THE VALUE HALF
//! --------------
//! Newer, and split the other way round -- by the WIRE rather than by the
//! header (design 2026-09-14, B2/B9):
//!
//! * **Wire v4** (`sensorium-rt 0.7.0` and later) redacts a LINE delta whose
//!   NAME fires the rule at the runtime's own writer, and the block arrives
//!   here already taken (tag 4). The converter's LINE name rule therefore does
//!   NOT run on such a spool -- it would be a second judgement on a value that
//!   is already a digest.
//! * **Wire 2 and 3** carry every captured value as the program had it, so the
//!   LINE name rule runs here.
//!
//! Two rules are the converter's on EVERY wire. The RETURN name rule, because
//! no runtime has a qualname at its exit probe to fire on (B7: the LAST
//! `::`-segment of the site's qualname is the name a returned value was asked
//! for by). And the CONTENT rule, because `sensorium-rt` stays dependency-free
//! and has no regex engine (`redact_content`), so every `dbg` text the
//! converter writes -- a RETURN value, a LINE delta, an exception message --
//! is scanned here, once.
//!
//! `by` is therefore the LAST hand that applied the rule, which is the
//! recorder only when the wire says the recorder did the value half too.
//!
//! Rule v1 itself is `sensorium_rt::redact` and is never respelled here: three
//! recorders and one converter apply one rule, and a second copy of the
//! segment list would be a fourth.

use std::collections::BTreeMap;
use std::sync::OnceLock;

use sensorium_rt::redact::{self, Key, Knobs, Table, REDACTED};
use serde_json::{json, Map, Value};

use super::redact_content;
use super::spool::ProcHeader;

/// The wire version from which a LINE delta may arrive already redacted, and
/// so the version from which the converter's own LINE name rule stands down.
///
/// A number of this module's own, as `errflow.rs` keeps its own `VERSION_V3`:
/// the two halves of this crate agree with the wire format, not with each
/// other's constants.
const VERSION_V4: u8 = 4;

/// Which rule took a value. The `redacted` object is exactly `{"by",
/// "digest"}` and nothing else, in every language that writes one (§4.2).
const BY_NAME: &str = "name";
const BY_CONTENT: &str = "content";

/// The whole of a Rust unit return, as `frames.rs` SYNTHESISES it off the
/// manifest: the wire carries no value at all for a frame the manifest says
/// returns `()`, and this text is the converter's own reading of that
/// silence (R17).
const UNIT: &str = "()";

/// The knobs the converter judges a NAME under: none of them.
///
/// `SENSORIUM_REDACT_NAMES` and `SENSORIUM_REDACT_ALLOW` are properties of the
/// RECORDING, and this converter is a different process on a possibly
/// different day -- reading its own environment for them would let a shell
/// that happens to carry one rewrite what a recording is said to have been
/// made under. `retrofit` below says the same thing about the environment
/// half, and for the same reason.
fn no_knobs() -> &'static Knobs {
    static NO_KNOBS: OnceLock<Knobs> = OnceLock::new();
    NO_KNOBS.get_or_init(|| Knobs::from_values(None, None, None))
}

/// What a trace records about its own environment: the environment to STORE,
/// the hash that identifies it, and the `redaction` object that says how it
/// came to look like that.
pub struct Applied {
    pub env: BTreeMap<String, String>,
    pub env_hash: String,
    pub redaction: Value,
}

/// The rule, as it stands for THIS header.
///
/// `wire` is the highest wire version any of this process's threads wrote,
/// and `values` is how many captures and messages the walk withheld
/// ([`crate::convert::frames::ProcessResult::values_redacted`]).
#[must_use]
pub fn apply(header: &ProcHeader, key: &Key, wire: u8, values: usize) -> Applied {
    match &header.redaction {
        Some(recorded) => Applied {
            env: header.env.clone(),
            env_hash: header.env_hash.clone(),
            redaction: carried(recorded, &header.env_redaction, wire, values),
        },
        None => retrofit(header, key, values),
    }
}

/// Whether the VALUE half of the rule runs over this process's records.
///
/// B26: a recording made with `SENSORIUM_NO_REDACT` set says so in its header
/// (`mode: "off"`), and a converter that redacted its values anyway would
/// publish a trace whose own `redaction` key -- carried through untouched, by
/// R2 -- says the opposite of what the rows hold. The same answer covers a
/// `redaction` that is not an object and a mode this converter does not know,
/// for [`carried`]'s reason: the converter acts only on a statement it
/// understands. A header with no `redaction` at all is a recording from
/// before the rule, and the rule runs (that is what [`retrofit`] is).
#[must_use]
pub fn values_rule_runs(header: &ProcHeader) -> bool {
    let Some(recorded) = &header.redaction else {
        return true;
    };
    recorded
        .as_object()
        .and_then(|o| o.get("mode"))
        .and_then(Value::as_str)
        == Some("on")
}

/// The recorder's object plus the keys the converter owns.
///
/// `mode: "off"` passes through EXACTLY as written -- two keys and no more.
/// The runtime writes that form deliberately (`redact::redaction_json`): a
/// header that named a key or a knob list while claiming to have applied
/// nothing would invite a reader to believe the plaintext beside it had been
/// considered, and an `env` table on an object whose mode is off would be a
/// table of nothing at all. Anything that is not an object, and any mode this
/// converter does not know, takes the same untouched path for the same
/// reason: the converter reports what the recording says, and adds only to a
/// statement it understands.
///
/// `by` is B2's: the RECORDER is the last hand only when it did the value
/// half as well, which is what a wire of 4 or better says. On a v2 or v3
/// spool the recorder redacted the environment and the CONVERTER redacted the
/// values, so the converter is the later hand and says so.
fn carried(
    recorded: &Value,
    table: &BTreeMap<String, Option<String>>,
    wire: u8,
    values: usize,
) -> Value {
    let Some(object) = recorded.as_object() else {
        return recorded.clone();
    };
    if object.get("mode").and_then(Value::as_str) != Some("on") {
        return recorded.clone();
    }
    let mut out = object.clone();
    out.insert("env".to_owned(), json!(table));
    out.insert("by".to_owned(), json!(by(wire)));
    out.insert("values".to_owned(), json!(values));
    Value::Object(out)
}

/// The last hand that applied rule v1 to this recording (B2).
fn by(wire: u8) -> &'static str {
    if wire >= VERSION_V4 {
        "recorder"
    } else {
        "converter"
    }
}

/// Rule v1 over a header that predates it, under the STORE's key.
///
/// No knobs, for [`no_knobs`]'s reason: an old recording was made under none,
/// and that is what the object below records.
fn retrofit(header: &ProcHeader, key: &Key, values: usize) -> Applied {
    // Sorted, because `BTreeMap` is: R13 wants one environment to give one
    // table byte for byte, and `redact_env` preserves the order it is handed.
    let env: Vec<(String, String)> = header
        .env
        .iter()
        .map(|(name, value)| (name.clone(), value.clone()))
        .collect();
    let (stored, table) = redact::redact_env(env, key, no_knobs());
    Applied {
        // The hash is an identity for what the trace HOLDS, and what it holds
        // is no longer what the recorder hashed.
        env_hash: redact::env_hash(&stored),
        env: stored.into_iter().collect(),
        redaction: json!({
            "rule": redact::RULE,
            "mode": "on",
            "keyed": key.keyed(),
            "key_id": key.key_id(),
            "names": [],
            "allow": [],
            "env": table_json(&table),
            // Not `by(wire)`: a header with no `redaction` at all was written
            // by a runtime that applied no half of the rule, whatever wire it
            // wrote, and the converter is the only hand this trace has had.
            "by": "converter",
            "values": values,
        }),
    }
}

fn table_json(table: &Table) -> Value {
    let mut out = Map::new();
    for (name, digest) in table {
        out.insert(name.clone(), json!(digest));
    }
    Value::Object(out)
}

// ---------------------------------------------------------------------------
// The value half: one capture, one message
// ---------------------------------------------------------------------------

/// One LINE delta, under the binding's own name.
///
/// Three readings, in order:
///
/// * A capture that ALREADY carries `redacted` is a tag-4 block the RUNTIME
///   took (wire v4, B9). No rule runs over it -- there is a digest where the
///   text was, and nothing left to judge -- and the `true` is B3's count of
///   it, made here because this is the one place the converter meets it.
/// * Below v4 the converter's own NAME rule fires, because no runtime of that
///   era judged a delta's name.
/// * Otherwise the CONTENT rule, which runs on every wire.
#[must_use]
pub fn line_delta(name: &str, value: Value, wire: u8, key: &Key) -> (Value, bool) {
    if value.get("redacted").is_some() {
        return (value, true);
    }
    if wire < VERSION_V4 && is_dbg(&value) && redact::fires(name, no_knobs()) {
        return taken(value, key);
    }
    text_value(value)
}

/// One RETURN value, under the LAST `::`-segment of the site's qualname (B7):
/// `demo::get_token` is asked for by the name `get_token`, which is the name
/// the rule judges.
///
/// Runs on EVERY wire: the runtime's exit probe has no qualname to fire on,
/// so this judgement has never been made before the value reaches here.
///
/// Only a `dbg` capture is taken, and two of those are carved out because
/// they withhold nothing to begin with:
///
/// * `{"k":"unread"}` -- taking it would cost a reader the fact that the
///   value could not be read and hide no secret.
/// * The unit value (R17). `frames.rs` synthesises `()` off the MANIFEST for
///   a frame whose signature returns nothing; the wire carries no value at
///   all. Withholding it would put `<redacted>` where a reader can see there
///   was nothing to take, add a `trunc: false` key that shape never carried,
///   publish a digest of the constant `"()"` -- which positively identifies
///   the "secret" it stands for -- and count a value nobody lost. Spelled
///   over the TEXT rather than over the synthesis site, so a `-> ()` a future
///   runtime ever does put on the wire takes the same carve-out.
#[must_use]
pub fn return_value(qualname: &str, value: Value, key: &Key) -> (Value, bool) {
    if value.get("redacted").is_none()
        && is_dbg(&value)
        && !is_unit(&value)
        && redact::fires(last_segment(qualname), no_knobs())
    {
        return taken(value, key);
    }
    text_value(value)
}

/// §2.2's CONTENT rule over a capture's own text, and whether it CHANGED.
///
/// A span operation, never a whole one: `postgres://u:<redacted>@h/db` keeps
/// the sentence around the secret, so the `redacted` object carries no digest
/// -- a partial cannot honestly commit to the whole. A capture already
/// carrying `redacted` is returned as it arrived: it was taken by name, there
/// is no text left to scan, and a second `redacted` object would claim an
/// operation that never happened.
#[must_use]
pub fn text_value(value: Value) -> (Value, bool) {
    if value.get("redacted").is_some() || !is_dbg(&value) {
        return (value, false);
    }
    let after = value.get("v").and_then(Value::as_str).and_then(|text| {
        let (after, hit) = redact_content::content(text);
        hit.then(|| after.into_owned())
    });
    let Some(after) = after else {
        return (value, false);
    };
    let mut out = value;
    out["v"] = json!(after);
    // `trunc` stays as it was: the text WAS clipped, and a span inside what
    // survived the clip was replaced.
    out["redacted"] = content_mark();
    (out, true)
}

/// One exception message, with the CONTENT rule over it (B21).
///
/// A message is a sentence the program wrote, not a value with an identity,
/// so a hit is marked on the `exc` object itself and carries no digest. The
/// caller writes that mark, because the `exc` object is built in two
/// different places and neither of them is here.
#[must_use]
pub fn exc_msg(msg: String) -> (String, bool) {
    let after = {
        let (after, hit) = redact_content::content(&msg);
        hit.then(|| after.into_owned())
    };
    match after {
        Some(after) => (after, true),
        None => (msg, false),
    }
}

/// B4's Rust half: the whole value, gone, and a digest of the text it held.
///
/// `trunc` is forced FALSE rather than dropped -- it is always present on a
/// `dbg` capture, and a reader that met it missing would have to guess
/// whether the formatter had been cut short. Nothing was clipped here: it was
/// taken. The digest is `null` on an unkeyed store, which a reader must be
/// able to tell from "not redacted", and is over the text the trace WOULD
/// have held (already clipped by the recorder), so it can be compared against
/// a trace that only ever stores the clipped form.
fn taken(value: Value, key: &Key) -> (Value, bool) {
    let digest = value
        .get("v")
        .and_then(Value::as_str)
        .and_then(|text| key.digest(text));
    let mut out = value;
    out["v"] = json!(REDACTED);
    out["trunc"] = json!(false);
    out["redacted"] = name_mark(&json!(digest));
    (out, true)
}

/// The `redacted` object a NAME hit leaves, under a digest ALREADY taken.
///
/// Public because R16 marks a second row with the first row's digest: the
/// origin RAISE synthesised in front of an `err` RETURN repeats that RETURN's
/// text, and the two must carry one digest, not two hashes of two different
/// spellings of one value.
#[must_use]
pub fn name_mark(digest: &Value) -> Value {
    json!({"by": BY_NAME, "digest": digest})
}

/// The `redacted` object a CONTENT hit leaves: the operation replaced a span,
/// so there is no digest of a whole to record.
#[must_use]
pub fn content_mark() -> Value {
    json!({"by": BY_CONTENT, "digest": Value::Null})
}

/// Whether this capture is the unit value the converter synthesises (R17).
fn is_unit(value: &Value) -> bool {
    value.get("v").and_then(Value::as_str) == Some(UNIT)
}

/// The name a returned value was asked for by (B7): `demo::get_token` ->
/// `get_token`, `demo::run::{{closure}}#0` -> `{{closure}}#0`.
///
/// A qualname that ends in the separator, or is empty, comes back whole:
/// there is no segment to judge, and `""` fires on nothing anyway, so this is
/// the honest reading rather than a special case.
fn last_segment(qualname: &str) -> &str {
    match qualname.rsplit("::").next() {
        Some(last) if !last.is_empty() => last,
        _ => qualname,
    }
}

/// Whether this capture is the text-shaped one. The Rust converter writes
/// exactly two capture kinds, `dbg` and `unread`, and only the first holds a
/// text for either operation to act on.
fn is_dbg(value: &Value) -> bool {
    value.get("k").and_then(Value::as_str) == Some("dbg")
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A proc header from its JSON, so every test here also exercises the two
    /// `#[serde(default)]` fields the way a real header reaches the reader.
    ///
    /// `sensorium-rt 0.6.0` is the RECORDED version, and it stays that: 0.6.0
    /// is the runtime that redacted an environment and wrote wire v3, which is
    /// exactly the older-runtime case most of these tests are about. The one
    /// that is about 0.7.0 says so ([`header_rt`]).
    fn header(extra: &str) -> ProcHeader {
        header_rt("sensorium-rt 0.6.0", extra)
    }

    fn header_rt(rt_version: &str, extra: &str) -> ProcHeader {
        let json = format!(
            r#"{{"pid":1,"ppid":0,"exe":"/w/t/x","argv":["x"],"cwd":"/w",
                 "start_ns":1,"start_realtime_ns":2,
                 "env":{{"MY_API_KEY":"s3cret","PATH":"/usr/bin"}},
                 "env_hash":"0123456789abcdef","units":{{}},"refused":null,
                 "rt_version":"{rt_version}"{extra}}}"#
        );
        serde_json::from_str(&json).unwrap_or_else(|e| panic!("{e}: {json}"))
    }

    fn key() -> Key {
        Key::from_hex(Some(&"ab".repeat(32)))
    }

    /// The `redaction` object a recorder that ran BOTH halves wrote -- rule
    /// v1's env half and, on wire v4, its value half too.
    const RECORDED: &str = r#","env_redaction":{"MY_API_KEY":"aabbccddeeff0011"},
                "redaction":{"rule":"v1","mode":"on","keyed":true,
                             "key_id":"0a1b2c3d","names":[],"allow":[]}"#;

    /// The recorder's object, carried whole, plus the table it wrote beside it,
    /// the hand that applied the rule and the count of what was withheld.
    ///
    /// Wire 4: `sensorium-rt 0.7.0` redacted the values on the wire as well as
    /// the environment, so the recorder is the last hand.
    #[test]
    fn a_recorded_redaction_is_carried_through_with_its_table_and_by_recorder() {
        let h = header_rt("sensorium-rt 0.7.0", RECORDED);
        let out = apply(&h, &key(), 4, 3);
        assert_eq!(
            out.redaction,
            json!({"rule": "v1", "mode": "on", "keyed": true,
                   "key_id": "0a1b2c3d", "names": [], "allow": [],
                   "env": {"MY_API_KEY": "aabbccddeeff0011"},
                   "by": "recorder", "values": 3})
        );
        // The recorder's environment and hash, untouched: it hashed what it
        // wrote, and the converter's key is not the key those digests were
        // taken under to begin with.
        assert_eq!(out.env["MY_API_KEY"], "s3cret");
        assert_eq!(out.env_hash, "0123456789abcdef");
    }

    /// B2, the other half of the same header: `sensorium-rt 0.6.0` wrote this
    /// object and wire v3, so it redacted the ENVIRONMENT and left every
    /// captured value as the program had it. The converter did the value half,
    /// and `by` names the LAST hand -- a `recorder` here would tell a reader
    /// that nothing touched these rows after the recording.
    #[test]
    fn the_same_header_on_a_v3_spool_says_the_converter_was_the_last_hand() {
        let h = header(RECORDED);
        let out = apply(&h, &key(), 3, 1);
        assert_eq!(out.redaction["by"], "converter");
        assert_eq!(out.redaction["values"], 1);
        // ...and nothing else about the recorder's own statement moved.
        assert_eq!(out.redaction["key_id"], "0a1b2c3d");
        assert_eq!(
            out.redaction["env"],
            json!({"MY_API_KEY": "aabbccddeeff0011"})
        );
    }

    /// The four combinations of (wire 3 | 4) x (a header with | without a
    /// `redaction` object), in one table: only one of them is the recorder's.
    #[test]
    fn by_names_the_recorder_only_when_the_wire_says_it_did_the_value_half() {
        for (wire, extra, expected) in [
            (4u8, RECORDED, "recorder"),
            (3, RECORDED, "converter"),
            // No `redaction` at all: a runtime that applied no half of the
            // rule, whatever wire it happened to write.
            (4, "", "converter"),
            (3, "", "converter"),
        ] {
            let out = apply(&header(extra), &key(), wire, 0);
            assert_eq!(
                out.redaction["by"], expected,
                "wire {wire}, extra {extra:?}"
            );
        }
    }

    /// R2. `mode: "off"` is two keys, and the converter adds none of its own:
    /// an `env` table on a recording that redacted nothing would be an empty
    /// table read as "the rule ran and found nothing", a `by` would name a
    /// hand that did not act, and a `values: 0` would be a count of something
    /// nobody measured.
    #[test]
    fn a_recording_made_with_the_rule_off_passes_through_exactly_as_written() {
        let h = header(r#","redaction":{"rule":"v1","mode":"off"}"#);
        let out = apply(&h, &key(), 3, 0);
        assert_eq!(out.redaction, json!({"rule": "v1", "mode": "off"}));
        assert_eq!(out.env["MY_API_KEY"], "s3cret");
        assert_eq!(out.env_hash, "0123456789abcdef");
    }

    /// B26's other half, and the reason the count above is always 0 there: the
    /// walk asks this before it runs any value rule at all.
    #[test]
    fn the_value_rule_stands_down_for_every_recording_but_an_on_one() {
        assert!(
            values_rule_runs(&header("")),
            "a header from before the rule"
        );
        assert!(values_rule_runs(&header(RECORDED)));
        for off in [
            r#","redaction":{"rule":"v1","mode":"off"}"#,
            // A mode this converter does not know, and a `redaction` that is
            // not an object at all -- `carried` passes both through untouched,
            // so redacting values under them would contradict the key beside
            // them.
            r#","redaction":{"rule":"v2","mode":"partial"}"#,
            r#","redaction":"v1""#,
        ] {
            assert!(!values_rule_runs(&header(off)), "{off}");
        }
    }

    /// A header from `sensorium-rt 0.5.0` or earlier: no `redaction` key at
    /// all, and a plaintext secret in `env`. The converter applies the rule
    /// rather than writing the plaintext into today's trace.
    #[test]
    fn a_header_from_before_the_rule_is_redacted_by_the_converter() {
        let out = apply(&header(""), &key(), 3, 0);
        assert_eq!(out.env["MY_API_KEY"], "<redacted>");
        assert_eq!(out.env["PATH"], "/usr/bin", "an ordinary name is stored");
        assert_eq!(out.redaction["by"], "converter");
        assert_eq!(out.redaction["mode"], "on");
        assert_eq!(out.redaction["keyed"], true);
        assert_eq!(out.redaction["key_id"], json!(key().key_id().unwrap()));
        assert_eq!(out.redaction["names"], json!([]));
        assert_eq!(out.redaction["allow"], json!([]));
        assert_eq!(
            out.redaction["env"],
            json!({"MY_API_KEY": key().digest("s3cret").unwrap()})
        );
        // And the count rides this form too: the converter ran both halves.
        assert_eq!(apply(&header(""), &key(), 3, 7).redaction["values"], 7);
    }

    /// The hash follows what the trace HOLDS. A converter that carried the
    /// recorder's `env_hash` over a retrofitted environment would publish an
    /// identity for a plaintext environment no longer in the trace, and two
    /// runs whose secrets differed would read as the same world.
    #[test]
    fn the_retrofitted_env_hash_is_taken_over_the_environment_that_is_stored() {
        let out = apply(&header(""), &key(), 3, 0);
        let stored: Vec<(String, String)> = out
            .env
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect();
        assert_eq!(out.env_hash, redact::env_hash(&stored));
        assert_ne!(out.env_hash, "0123456789abcdef");
        // And it does not follow the secret: the whole point of hashing the
        // redacted form is that two shells differing only in their tokens
        // record the same world.
        let mut other = header("");
        other
            .env
            .insert("MY_API_KEY".to_owned(), "a different secret".to_owned());
        assert_eq!(apply(&other, &key(), 3, 0).env_hash, out.env_hash);
    }

    /// An unkeyed store still redacts. The name is what the rule fires on, and
    /// the missing digest is recorded as `null` rather than omitted -- a
    /// reader must be able to tell "redacted, no digest" from "not redacted".
    #[test]
    fn an_unkeyed_converter_redacts_and_says_the_digest_is_absent() {
        let out = apply(&header(""), &Key::from_hex(None), 3, 0);
        assert_eq!(out.env["MY_API_KEY"], "<redacted>");
        assert_eq!(out.redaction["keyed"], false);
        assert_eq!(out.redaction["key_id"], Value::Null);
        assert_eq!(out.redaction["env"], json!({"MY_API_KEY": null}));
    }

    // -- the value half ---------------------------------------------------

    /// A `dbg` capture as both the RETURN reader and the LINE reader build
    /// one.
    fn dbg(text: &str) -> Value {
        json!({"k": "dbg", "v": text, "trunc": false})
    }

    /// B7: the rule judges the LAST `::`-segment of the qualname, because that
    /// is the name the value was asked for by. Reading the whole path would
    /// fire on every function in a module called `auth`, and miss nothing it
    /// was meant to catch.
    #[test]
    fn a_return_value_is_judged_by_the_last_segment_of_its_qualname() {
        let (out, hit) = return_value("demo::get_token", dbg("\"abc\""), &key());
        assert!(hit);
        assert_eq!(
            out,
            json!({"k": "dbg", "v": "<redacted>", "trunc": false,
                   "redacted": {"by": "name",
                                "digest": key().digest("\"abc\"").unwrap()}})
        );
        // The same text under a module whose NAME fires and a function whose
        // name does not: the segment judged is the function's.
        let (out, hit) = return_value("token::render", dbg("\"abc\""), &key());
        assert!(!hit, "{out}");
        assert_eq!(out, dbg("\"abc\""));
    }

    /// The rule takes the whole value and leaves a digest of the text the
    /// trace would otherwise have held -- so `diff` and `watch` can still say
    /// "the same value" without printing it. `trunc` is written FALSE rather
    /// than dropped: nothing was clipped, it was taken.
    #[test]
    fn a_taken_return_keeps_its_kind_and_says_nothing_was_clipped() {
        let (out, hit) = return_value(
            "get_token",
            json!({"k": "dbg", "v": "s", "trunc": true}),
            &key(),
        );
        assert!(hit);
        assert_eq!(out["trunc"], json!(false));
        assert_eq!(out["k"], "dbg");
    }

    /// An unkeyed store takes the value and records `null` where the digest
    /// would be -- never omits the field, which a reader would have to read as
    /// "not redacted".
    #[test]
    fn an_unkeyed_store_takes_the_value_and_records_no_digest() {
        let (out, hit) = return_value("get_token", dbg("s"), &Key::from_hex(None));
        assert!(hit);
        assert_eq!(out["redacted"], json!({"by": "name", "digest": null}));
    }

    /// R17. A unit-returning frame's `()` is the CONVERTER's own reading off
    /// the manifest -- the wire carries no value for it at all -- and it
    /// withholds nothing. Taking it would put `<redacted>` where a reader can
    /// see there was nothing to take, publish a digest of the constant `"()"`
    /// that positively identifies what it stands for, and count a value nobody
    /// lost. `fn refresh_token(&mut self)` is the shape this is about.
    #[test]
    fn a_unit_return_under_a_firing_name_is_never_withheld() {
        let (out, hit) = return_value("demo::refresh_token", dbg(UNIT), &key());
        assert!(!hit, "a value that hides nothing is not one of `values`");
        assert_eq!(out, dbg(UNIT), "no marker, no mark, no `trunc` that moved");
        // The carve-out is over the TEXT, so a `()` that ever did come off the
        // wire takes it too -- and it is a carve-out and not a hole: any other
        // text under the same name is still taken.
        assert!(return_value("demo::refresh_token", dbg("Session { id: 1 }"), &key()).1);
    }

    /// A value the probe could not read at all withholds nothing already, so
    /// the name rule leaves it alone: taking it would cost a reader the fact
    /// that the value was unreadable and hide no secret.
    #[test]
    fn an_unread_return_under_a_firing_name_is_left_as_it_is() {
        let (out, hit) = return_value("get_token", json!({"k": "unread"}), &key());
        assert!(!hit);
        assert_eq!(out, json!({"k": "unread"}));
    }

    /// B9: below wire v4 the converter judges a delta's name, because no
    /// runtime of that era did.
    #[test]
    fn a_line_delta_on_an_older_wire_is_judged_by_its_binding_name() {
        let (out, hit) = line_delta("token", dbg("\"abc\""), 3, &key());
        assert!(hit);
        assert_eq!(out["v"], "<redacted>");
        assert_eq!(out["redacted"]["by"], "name");
    }

    /// ...and from v4 it does NOT, because the runtime already did. A delta
    /// that arrives as plain text on a v4 spool is one the runtime judged and
    /// did not fire on, and a second judgement here would contradict the
    /// recording rather than add to it.
    #[test]
    fn a_line_delta_on_wire_four_is_left_to_the_recorders_judgement() {
        let (out, hit) = line_delta("token", dbg("\"abc\""), 4, &key());
        assert!(!hit, "{out}");
        assert_eq!(out, dbg("\"abc\""));
    }

    /// B3's one awkward count: a tag-4 block the RUNTIME wrote is a value this
    /// trace withholds, so it counts -- once, here, where the converter meets
    /// it. No rule runs over it: there is a digest where the text was.
    #[test]
    fn a_delta_the_recorder_already_took_is_counted_once_and_untouched() {
        let already = json!({"k": "dbg", "v": "<redacted>", "trunc": false,
                             "redacted": {"by": "name", "digest": "aabbccddeeff0011"}});
        let (out, hit) = line_delta("token", already.clone(), 4, &key());
        assert!(hit, "a withheld value the trace holds is one of `values`");
        assert_eq!(out, already, "nothing is judged twice");
        // And the content rule, which is what a delta falls through to, says
        // the same: no second `redacted` object, and no second count.
        let (out, hit) = text_value(already.clone());
        assert!(!hit);
        assert_eq!(out, already);
    }

    /// §2.3's span operation: the sentence around the secret is kept, and the
    /// mark carries no digest -- a partial cannot honestly commit to a whole.
    #[test]
    fn the_content_rule_replaces_the_span_and_keeps_what_is_around_it() {
        let (out, hit) = text_value(dbg(
            r#"Headers { authorization: "Bearer sk-abcdefghijklmnop" }"#,
        ));
        assert!(hit);
        assert_eq!(
            out["v"],
            r#"Headers { authorization: "Bearer <redacted>" }"#
        );
        assert_eq!(out["redacted"], json!({"by": "content", "digest": null}));
    }

    /// A text with nothing secret-shaped in it comes back as it arrived --
    /// byte for byte, and with no `redacted` object claiming an operation that
    /// found nothing.
    #[test]
    fn a_text_the_content_rule_does_not_fire_on_is_untouched() {
        let (out, hit) = text_value(dbg("Cfg { retries: 3 }"));
        assert!(!hit);
        assert_eq!(out, dbg("Cfg { retries: 3 }"));
    }

    /// The rule is a fixed point over the marker it writes, which is what lets
    /// it run on every text the converter writes without counting twice.
    #[test]
    fn a_text_already_carrying_the_marker_is_not_a_second_hit() {
        let out = text_value(dbg("postgres://u:<redacted>@h/db"));
        assert_eq!(out, (dbg("postgres://u:<redacted>@h/db"), false));
    }

    /// B21: an exception message takes the CONTENT rule and nothing else --
    /// it is a sentence the program wrote, not a value with an identity.
    #[test]
    fn an_exception_message_takes_the_content_rule() {
        let (msg, hit) = exc_msg("auth failed for ghp_abcdefghijklmnopqrstuvwxyz".to_owned());
        assert!(hit);
        assert_eq!(msg, "auth failed for <redacted>");
        assert_eq!(
            exc_msg("auth failed".to_owned()),
            ("auth failed".to_owned(), false)
        );
    }

    #[test]
    fn the_last_segment_of_a_qualname_is_the_name_a_value_was_asked_for_by() {
        assert_eq!(last_segment("demo::get_token"), "get_token");
        assert_eq!(last_segment("get_token"), "get_token");
        assert_eq!(last_segment("a::b::{{closure}}#0"), "{{closure}}#0");
        // Nothing to judge: the whole name comes back rather than an empty
        // one, and fires on nothing either way.
        assert_eq!(last_segment("demo::"), "demo::");
        assert_eq!(last_segment(""), "");
    }
}
