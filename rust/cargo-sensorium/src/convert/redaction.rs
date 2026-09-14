//! What a trace's `redaction` key says, and the rule applied to a proc header
//! too old to carry one.
//!
//! Two paths, and which one a header takes is decided by whether the RECORDER
//! already ran the rule:
//!
//! * **The recorder ran it** (`sensorium-rt 0.6.0` and later). The header's
//!   own `redaction` object is what the trace says, carried through untouched
//!   but for the two keys only the converter can fill in -- `env`, the name ->
//!   digest table the runtime wrote beside it, and `by`, the last hand that
//!   applied the rule. The stored environment and its `env_hash` are the
//!   recorder's and are not recomputed: the runtime hashed what it wrote, and
//!   a second hash taken here could only differ by being wrong.
//! * **The recorder did not** (`sensorium-rt 0.5.0` and earlier). Those spools
//!   hold the whole launching environment in plaintext, and a converter that
//!   passed them through would write today's trace with yesterday's secrets in
//!   it. The rule runs HERE instead, `by: "converter"`, and `env_hash` is
//!   recomputed because the environment being hashed has changed.
//!
//! Rule v1 itself is `sensorium_rt::redact` and is never respelled here: three
//! recorders and one converter apply one rule, and a second copy of the
//! segment list would be a fourth.

use std::collections::BTreeMap;

use sensorium_rt::redact::{self, Key, Knobs, Table};
use serde_json::{json, Map, Value};

use super::spool::ProcHeader;

/// What a trace records about its own environment: the environment to STORE,
/// the hash that identifies it, and the `redaction` object that says how it
/// came to look like that.
pub struct Applied {
    pub env: BTreeMap<String, String>,
    pub env_hash: String,
    pub redaction: Value,
}

/// The rule, as it stands for THIS header.
#[must_use]
pub fn apply(header: &ProcHeader, key: &Key) -> Applied {
    match &header.redaction {
        Some(recorded) => Applied {
            env: header.env.clone(),
            env_hash: header.env_hash.clone(),
            redaction: carried(recorded, &header.env_redaction),
        },
        None => retrofit(header, key),
    }
}

/// The recorder's object plus the two keys the converter owns.
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
fn carried(recorded: &Value, table: &BTreeMap<String, Option<String>>) -> Value {
    let Some(object) = recorded.as_object() else {
        return recorded.clone();
    };
    if object.get("mode").and_then(Value::as_str) != Some("on") {
        return recorded.clone();
    }
    let mut out = object.clone();
    out.insert("env".to_owned(), json!(table));
    out.insert("by".to_owned(), json!("recorder"));
    Value::Object(out)
}

/// Rule v1 over a header that predates it, under the STORE's key.
///
/// No knobs. `SENSORIUM_REDACT_NAMES` and `SENSORIUM_REDACT_ALLOW` are
/// properties of the recording, and this converter is a different process on
/// a possibly different day -- reading its own environment for them would let
/// a shell that happens to carry one rewrite what an old recording is said to
/// have been made under. An old recording was made under none, and that is
/// what the object below records.
fn retrofit(header: &ProcHeader, key: &Key) -> Applied {
    // Sorted, because `BTreeMap` is: R13 wants one environment to give one
    // table byte for byte, and `redact_env` preserves the order it is handed.
    let env: Vec<(String, String)> = header
        .env
        .iter()
        .map(|(name, value)| (name.clone(), value.clone()))
        .collect();
    let (stored, table) = redact::redact_env(env, key, &Knobs::from_values(None, None, None));
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
            "by": "converter",
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

#[cfg(test)]
mod tests {
    use super::*;

    /// A proc header from its JSON, so every test here also exercises the two
    /// `#[serde(default)]` fields the way a real header reaches the reader.
    fn header(extra: &str) -> ProcHeader {
        let json = format!(
            r#"{{"pid":1,"ppid":0,"exe":"/w/t/x","argv":["x"],"cwd":"/w",
                 "start_ns":1,"start_realtime_ns":2,
                 "env":{{"MY_API_KEY":"s3cret","PATH":"/usr/bin"}},
                 "env_hash":"0123456789abcdef","units":{{}},"refused":null,
                 "rt_version":"sensorium-rt 0.6.0"{extra}}}"#
        );
        serde_json::from_str(&json).unwrap_or_else(|e| panic!("{e}: {json}"))
    }

    fn key() -> Key {
        Key::from_hex(Some(&"ab".repeat(32)))
    }

    /// The recorder's object, carried whole, plus the table it wrote beside it
    /// and the hand that applied the rule.
    #[test]
    fn a_recorded_redaction_is_carried_through_with_its_table_and_by_recorder() {
        let h = header(
            r#","env_redaction":{"MY_API_KEY":"aabbccddeeff0011"},
                "redaction":{"rule":"v1","mode":"on","keyed":true,
                             "key_id":"0a1b2c3d","names":[],"allow":[]}"#,
        );
        let out = apply(&h, &key());
        assert_eq!(
            out.redaction,
            json!({"rule": "v1", "mode": "on", "keyed": true,
                   "key_id": "0a1b2c3d", "names": [], "allow": [],
                   "env": {"MY_API_KEY": "aabbccddeeff0011"},
                   "by": "recorder"})
        );
        // The recorder's environment and hash, untouched: it hashed what it
        // wrote, and the converter's key is not the key those digests were
        // taken under to begin with.
        assert_eq!(out.env["MY_API_KEY"], "s3cret");
        assert_eq!(out.env_hash, "0123456789abcdef");
    }

    /// R2. `mode: "off"` is two keys, and the converter adds neither of its
    /// own: an `env` table on a recording that redacted nothing would be an
    /// empty table read as "the rule ran and found nothing", and a `by` would
    /// name a hand that did not act.
    #[test]
    fn a_recording_made_with_the_rule_off_passes_through_exactly_as_written() {
        let h = header(r#","redaction":{"rule":"v1","mode":"off"}"#);
        let out = apply(&h, &key());
        assert_eq!(out.redaction, json!({"rule": "v1", "mode": "off"}));
        assert_eq!(out.env["MY_API_KEY"], "s3cret");
        assert_eq!(out.env_hash, "0123456789abcdef");
    }

    /// A header from `sensorium-rt 0.5.0` or earlier: no `redaction` key at
    /// all, and a plaintext secret in `env`. The converter applies the rule
    /// rather than writing the plaintext into today's trace.
    #[test]
    fn a_header_from_before_the_rule_is_redacted_by_the_converter() {
        let out = apply(&header(""), &key());
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
    }

    /// The hash follows what the trace HOLDS. A converter that carried the
    /// recorder's `env_hash` over a retrofitted environment would publish an
    /// identity for a plaintext environment no longer in the trace, and two
    /// runs whose secrets differed would read as the same world.
    #[test]
    fn the_retrofitted_env_hash_is_taken_over_the_environment_that_is_stored() {
        let out = apply(&header(""), &key());
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
        assert_eq!(apply(&other, &key()).env_hash, out.env_hash);
    }

    /// An unkeyed store still redacts. The name is what the rule fires on, and
    /// the missing digest is recorded as `null` rather than omitted -- a
    /// reader must be able to tell "redacted, no digest" from "not redacted".
    #[test]
    fn an_unkeyed_converter_redacts_and_says_the_digest_is_absent() {
        let out = apply(&header(""), &Key::from_hex(None));
        assert_eq!(out.env["MY_API_KEY"], "<redacted>");
        assert_eq!(out.redaction["keyed"], false);
        assert_eq!(out.redaction["key_id"], Value::Null);
        assert_eq!(out.redaction["env"], json!({"MY_API_KEY": null}));
    }
}
