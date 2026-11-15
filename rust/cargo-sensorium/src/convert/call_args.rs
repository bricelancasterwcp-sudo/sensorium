//! A CALL's arguments, read from the LINE payload shape `enter_args` writes.
//!
//! An empty payload is the old `enter` record: the arguments were not read,
//! and the row says so. A payload that parsed is a read. `n = 0` is "read,
//! found no arguments". A short record keeps the arguments that fit and sets
//! `unread: ["locals"]` beside them.

use sensorium_rt::redact::Key;
use serde_json::{json, Map, Value};

use crate::convert::redaction;
use crate::convert::spool::line::parse_line_payload;

/// The `events.payload` object for one CALL.
///
/// # Errors
/// The payload is non-empty and is not a LINE-shaped argument block, or it
/// carries an unbound name (a call does not end a scope).
pub fn payload(
    label: &str,
    raw: &[u8],
    version: u8,
    rule: Option<&Key>,
    values_redacted: &mut usize,
) -> Result<Value, String> {
    if raw.is_empty() {
        return Ok(json!({"args": {}, "unread": ["locals"]}));
    }
    let parsed = parse_line_payload(label, raw, version)?;
    if !parsed.unbound.is_empty() {
        return Err(format!(
            "{label}: a CALL payload carries unbound names, which a call does not"
        ));
    }
    let mut args = Map::new();
    for (name, capture) in parsed.deltas {
        let capture = match rule {
            Some(key) => {
                let (capture, hit) = redaction::line_delta(&name, capture, version, key);
                *values_redacted += usize::from(hit);
                capture
            }
            None => capture,
        };
        args.insert(name, capture);
    }
    let mut obj = Map::new();
    obj.insert("args".to_owned(), Value::Object(args));
    if parsed.dropped {
        obj.insert("unread".to_owned(), json!(["locals"]));
    }
    Ok(Value::Object(obj))
}
