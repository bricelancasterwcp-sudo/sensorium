//! The LINE payload (wire kind 6), read back.
//!
//! **Independent of `sensorium-rt/src/line.rs`.** That module writes this
//! grammar; this one reads it, from the format block reproduced below (design
//! 2026-09-06 §3.4) -- never by importing the writer's code. The fixtures both
//! sides are tested against are hand-built bytes, so a bug shared by writer and
//! reader cannot cancel itself out.
//!
//! ```text
//! LINE payload:  u8 flags   bit0 = deltas dropped (the record is SHORT)
//!                u16 n      deltas present
//!                n × { u16 name_len, name UTF-8,
//!                      u8 tag (0 no value | 1 debug text | 2 unread),
//!                      u8 truncated,
//!                      [u16 text_len, text UTF-8]   -- only when tag = 1 }
//! ```
//!
//! The value block is the RETURN payload's, repeated with a name in front of
//! it, so a delta's converted shape is the one a Rust RETURN value already
//! carries: `{"k":"dbg","v":<text>,"trunc":<bool>}` and `{"k":"unread"}`.
//!
//! Every refusal here names the record's label and the offending FIELD, and
//! never yields a partial reading: a LINE row this reader had to guess at
//! would be a statement's locals invented out of corruption, which is the one
//! thing a locals tier may not do.

use serde_json::{json, Value};

use super::{TAG_DEBUG, TAG_NO_VALUE, TAG_UNREAD};

/// `bit0` of the flags byte: at least one delta did not fit in the record and
/// was left out, along with every delta after it.
const FLAG_DELTAS_DROPPED: u8 = 1 << 0;

/// The payload's fixed head: `u8 flags`, `u16 n`.
const LINE_HEADER: usize = 3;

/// A LINE payload decoded: the statement's deltas, in the order the record
/// carries them, each already in its converted capture shape.
///
/// `deltas` is a `Vec` and not a map because ORDER is the record's, and the
/// caller is what turns it into the payload's `deltas` object -- after this
/// reader has refused a duplicate name, which is the only way that object can
/// lose a reading.
#[derive(Debug)]
pub struct LinePayload {
    /// The record says it is short: `unread: ["locals"]` on the row.
    pub dropped: bool,
    pub deltas: Vec<(String, Value)>,
}

/// Decode a LINE payload.
///
/// Bits of the flags byte other than `bit0` are not read: the runtime writes
/// only that one, and a bit a future runtime adds is a fact this converter has
/// nothing to say about -- the same treatment the err-flow reader gives its own
/// flags byte.
///
/// # Errors
/// A payload shorter than its three fixed bytes; a name, a text or a delta
/// block that runs past the payload; a name that is not UTF-8; a text that is
/// not UTF-8; `tag == 0` (legal in the grammar, unwritable by the runtime --
/// design amendment A7); an unknown tag; the same name twice in one record
/// (the deltas become one JSON object, so a duplicate would silently overwrite
/// a reading, and the transformer mints one delta per binding a statement
/// wrote, never two); or bytes left over after the last delta.
pub fn parse_line_payload(label: &str, payload: &[u8]) -> Result<LinePayload, String> {
    if payload.len() < LINE_HEADER {
        return Err(format!(
            "{label}: LINE payload is shorter than its {LINE_HEADER} fixed bytes"
        ));
    }
    let dropped = payload[0] & FLAG_DELTAS_DROPPED != 0;
    let n = u16::from_le_bytes([payload[1], payload[2]]);
    let mut at = LINE_HEADER;
    let mut deltas: Vec<(String, Value)> = Vec::with_capacity(n as usize);
    for i in 0..n {
        let name = read_name(label, payload, &mut at, i)?;
        let value = read_value(label, payload, &mut at, &name)?;
        if deltas.iter().any(|(seen, _)| *seen == name) {
            return Err(format!(
                "{label}: LINE payload names delta `{name}` twice; one statement writes a binding \
                 once, so a repeated name is corruption"
            ));
        }
        deltas.push((name, value));
    }
    if at != payload.len() {
        return Err(format!(
            "{label}: LINE payload has {} bytes after its {n} deltas",
            payload.len() - at
        ));
    }
    Ok(LinePayload { dropped, deltas })
}

/// `u16 name_len, name UTF-8`, advancing `at`.
fn read_name(label: &str, payload: &[u8], at: &mut usize, i: u16) -> Result<String, String> {
    let len = read_u16(payload, at)
        .ok_or_else(|| format!("{label}: LINE payload's delta {i} stops inside its name length"))?;
    let end = *at + len;
    if end > payload.len() {
        return Err(format!(
            "{label}: LINE payload's delta {i} claims a {len}-byte name past the end of the payload"
        ));
    }
    let name = std::str::from_utf8(&payload[*at..end])
        .map_err(|e| format!("{label}: LINE payload's delta {i} name is not UTF-8: {e}"))?
        .to_owned();
    *at = end;
    Ok(name)
}

/// `u8 tag, u8 truncated, [u16 text_len, text]`, advancing `at`, as the
/// converted capture the row carries.
fn read_value(label: &str, payload: &[u8], at: &mut usize, name: &str) -> Result<Value, String> {
    if *at + 2 > payload.len() {
        return Err(format!(
            "{label}: LINE payload's delta `{name}` stops before its tag"
        ));
    }
    let (tag, truncated) = (payload[*at], payload[*at + 1] != 0);
    *at += 2;
    match tag {
        TAG_DEBUG => {
            let len = read_u16(payload, at).ok_or_else(|| {
                format!("{label}: LINE payload's delta `{name}` stops inside its text length")
            })?;
            let end = *at + len;
            if end > payload.len() {
                return Err(format!(
                    "{label}: LINE payload's delta `{name}` claims a {len}-byte text past the end \
                     of the payload"
                ));
            }
            let text = std::str::from_utf8(&payload[*at..end]).map_err(|e| {
                format!("{label}: LINE payload's delta `{name}` text is not UTF-8: {e}")
            })?;
            *at = end;
            Ok(json!({"k": "dbg", "v": text, "trunc": truncated}))
        }
        // The truncated byte is the WRITER's, and only a text can be cut: an
        // unread value has nothing to truncate, so the byte is not read into
        // the row -- `{"k":"unread"}` is the shape a RETURN already uses.
        TAG_UNREAD => Ok(json!({"k": "unread"})),
        TAG_NO_VALUE => Err(format!(
            "{label}: LINE payload's delta `{name}` carries tag 0 (no value), which is legal in \
             the grammar and no runtime writes for a delta"
        )),
        other => Err(format!(
            "{label}: LINE payload's delta `{name}` carries tag {other}, which is not 0..=2"
        )),
    }
}

/// A little-endian `u16` at `at`, advancing it -- `None` when the two bytes are
/// not both there.
fn read_u16(payload: &[u8], at: &mut usize) -> Option<usize> {
    if *at + 2 > payload.len() {
        return None;
    }
    let v = u16::from_le_bytes([payload[*at], payload[*at + 1]]) as usize;
    *at += 2;
    Some(v)
}
