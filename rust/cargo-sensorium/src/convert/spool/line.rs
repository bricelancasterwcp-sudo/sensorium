//! The LINE payload (wire kind 6), read back.
//!
//! **Independent of `sensorium-rt/src/line.rs`.** That module writes this
//! grammar; this one reads it, from the format block reproduced below (design
//! 2026-09-06 §3.4) -- never by importing the writer's code. The fixtures both
//! sides are tested against are hand-built bytes, so a bug shared by writer and
//! reader cannot cancel itself out.
//!
//! ```text
//! LINE payload:  u8 flags   bit0 = something dropped (the record is SHORT)
//!                u16 n      blocks present -- the deltas, then the names
//!                n × { u16 name_len, name UTF-8,
//!                      u8 tag (0 no value | 1 debug text | 2 unread
//!                              | 3 unbound: a name, no value),
//!                      u8 truncated,
//!                      [u16 text_len, text UTF-8]   -- only when tag = 1 }
//! ```
//!
//! The value block is the RETURN payload's, repeated with a name in front of
//! it, so a delta's converted shape is the one a Rust RETURN value already
//! carries: `{"k":"dbg","v":<text>,"trunc":<bool>}` and `{"k":"unread"}`.
//!
//! **Tag 3 is a name and not a value** (rt 0.5.0, design 2026-09-12 §5.3): a
//! block-like statement's row carries, after its deltas, the names whose scope
//! ended with it. One grammar, one loop -- each block names a binding and its
//! tag says whether the record is telling you what that statement WROTE or
//! that the binding is gone; the two readings go to the two lists below, and a
//! name the record puts on both is corruption, not a row to guess at.
//!
//! Every refusal here names the record's label and the offending FIELD, and
//! never yields a partial reading: a LINE row this reader had to guess at
//! would be a statement's locals invented out of corruption, which is the one
//! thing a locals tier may not do.

use serde_json::{json, Value};

use super::{TAG_DEBUG, TAG_NO_VALUE, TAG_UNREAD};

/// `bit0` of the flags byte: at least one block did not fit in the record and
/// was left out, along with every block after it -- a delta, or an unbound
/// name, whichever the budget stopped on.
const FLAG_DELTAS_DROPPED: u8 = 1 << 0;

/// The fourth tag: a name with no value, whose scope ended on this row.
///
/// `super`'s `TAG_NO_VALUE`/`TAG_DEBUG`/`TAG_UNREAD` are the RETURN value
/// block's, which a delta reuses; 3 is the LINE payload's alone, because a
/// returned value cannot go out of scope.
const TAG_UNBOUND: u8 = 3;

/// What [`read_value`] answers for a tag-3 block: no value at all.
///
/// `Value::Null` is a shape no capture takes -- every capture this reader
/// builds is an object with a `k` -- so the loop can tell the one reading from
/// the other without a second return type, and nothing carrying it ever
/// reaches a row.
const UNBOUND_MARKER: Value = Value::Null;

/// The payload's fixed head: `u8 flags`, `u16 n`.
const LINE_HEADER: usize = 3;

/// A LINE payload decoded: the statement's deltas, in the order the record
/// carries them, each already in its converted capture shape.
///
/// `deltas` is a `Vec` and not a map for one reason: the duplicate-name check
/// below has to see every reading before any of them is keyed, and that check
/// is the only thing standing between a corrupt record and a silently
/// overwritten delta.
///
/// The ROW's `deltas` object is name-keyed, and the record's order is NOT
/// preserved into it: this crate builds `serde_json` without `preserve_order`,
/// so its `Map` is a `BTreeMap` and a reader sees the deltas sorted by name.
/// Nothing downstream depends on the order the record carried -- a delta is
/// found by the binding it names.
#[derive(Debug)]
pub struct LinePayload {
    /// The record says it is short: `unread: ["locals"]` on the row.
    pub dropped: bool,
    pub deltas: Vec<(String, Value)>,
    /// The names whose scope ended on this row, in RECORD order -- which is
    /// the transformer's source order, and is preserved all the way to the
    /// row's `unbound` array and the `unbound:` list `frame` prints.
    ///
    /// Unlike `deltas`, this one is not keyed by anything downstream, so its
    /// order is the reading rather than an accident of how it is stored: the
    /// row says which of a statement's bindings died, in the order the
    /// statement introduced them.
    pub unbound: Vec<String>,
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
/// design amendment A7); an unknown tag; the same name twice in one record --
/// twice on one list, or once on each, which is a statement claiming to have
/// written what it unbinds (the deltas become one JSON object, so a duplicate
/// would silently overwrite a reading; the transformer mints one block per
/// binding a statement wrote or unbound, never two, and lists a name bound in
/// both a head pattern and an inner `let` once); or bytes left over after the
/// last block.
pub fn parse_line_payload(label: &str, payload: &[u8]) -> Result<LinePayload, String> {
    if payload.len() < LINE_HEADER {
        return Err(format!(
            "{label}: LINE payload is shorter than its {LINE_HEADER} fixed bytes"
        ));
    }
    let dropped = payload[0] & FLAG_DELTAS_DROPPED != 0;
    let n = u16::from_le_bytes([payload[1], payload[2]]);
    let mut at = LINE_HEADER;
    // `n` is UNVALIDATED here: a corrupt three-byte payload can claim 65_535
    // deltas. The smallest a delta block can be is four bytes (`u16 name_len`
    // with an empty name, `u8 tag`, `u8 truncated`), so the payload's own
    // length is the honest bound -- reserving `n` would let that three-byte
    // record allocate megabytes on its way to being refused.
    let mut deltas: Vec<(String, Value)> = Vec::with_capacity((n as usize).min(payload.len() / 4));
    // Not pre-sized: the names ride after the deltas and most rows carry none,
    // so the capacity `n` would reserve is the deltas' own, twice over.
    let mut unbound: Vec<String> = Vec::new();
    for i in 0..n {
        let name = read_name(label, payload, &mut at, i)?;
        let value = read_value(label, payload, &mut at, &name)?;
        let now_unbound = value == UNBOUND_MARKER;
        if let Some(was_unbound) = seen_as(&deltas, &unbound, &name) {
            return Err(duplicate_refusal(label, &name, was_unbound, now_unbound));
        }
        if now_unbound {
            unbound.push(name);
        } else {
            deltas.push((name, value));
        }
    }
    if at != payload.len() {
        return Err(format!(
            "{label}: LINE payload has {} bytes after its {n} blocks",
            payload.len() - at
        ));
    }
    Ok(LinePayload {
        dropped,
        deltas,
        unbound,
    })
}

/// Whether this record has already named `name`, and on which list -- `true`
/// for the unbound names, `false` for the deltas.
///
/// One walk over both, because the rule is one rule: a record names each
/// binding once, whichever thing it is saying about it.
fn seen_as(deltas: &[(String, Value)], unbound: &[String], name: &str) -> Option<bool> {
    if deltas.iter().any(|(seen, _)| seen == name) {
        return Some(false);
    }
    unbound.iter().any(|seen| seen == name).then_some(true)
}

/// The refusal for a repeated name, which is two different corruptions and so
/// two sentences: the same list twice (a reading that would overwrite another,
/// or a scope that ended twice), and one list each -- a statement claiming to
/// have written the binding it is also reporting dead.
fn duplicate_refusal(label: &str, name: &str, was_unbound: bool, now_unbound: bool) -> String {
    if was_unbound != now_unbound {
        return format!(
            "{label}: LINE payload names `{name}` as both a delta and an unbound name; a \
             statement cannot write what it unbinds"
        );
    }
    let what = if now_unbound { "unbound name" } else { "delta" };
    format!(
        "{label}: LINE payload names {what} `{name}` twice; one statement writes a binding once, \
         so a repeated name is corruption"
    )
}

/// `u16 name_len, name UTF-8`, advancing `at`.
fn read_name(label: &str, payload: &[u8], at: &mut usize, i: u16) -> Result<String, String> {
    // `block` and not `delta`: the tag has not been read yet, so this reader
    // does not yet know whether the block names a value or a dead binding.
    let len = read_u16(payload, at)
        .ok_or_else(|| format!("{label}: LINE payload's block {i} stops inside its name length"))?;
    let end = *at + len;
    if end > payload.len() {
        return Err(format!(
            "{label}: LINE payload's block {i} claims a {len}-byte name past the end of the payload"
        ));
    }
    let name = std::str::from_utf8(&payload[*at..end])
        .map_err(|e| format!("{label}: LINE payload's block {i} name is not UTF-8: {e}"))?
        .to_owned();
    *at = end;
    Ok(name)
}

/// `u8 tag, u8 truncated, [u16 text_len, text]`, advancing `at`, as the
/// converted capture the row carries -- or [`UNBOUND_MARKER`], which is this
/// block saying it carries no value because the binding is gone.
fn read_value(label: &str, payload: &[u8], at: &mut usize, name: &str) -> Result<Value, String> {
    if *at + 2 > payload.len() {
        return Err(format!(
            "{label}: LINE payload's block `{name}` stops before its tag"
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
        // The truncated byte is the writer's here too, and a name is never
        // truncated -- a name that does not fit drops its block whole and sets
        // bit0 -- so nothing of this block but its name reaches the row.
        TAG_UNBOUND => Ok(UNBOUND_MARKER),
        TAG_NO_VALUE => Err(format!(
            "{label}: LINE payload's delta `{name}` carries tag 0 (no value), which is legal in \
             the grammar and no runtime writes for a delta"
        )),
        other => Err(format!(
            "{label}: LINE payload's delta `{name}` carries tag {other}, which is not 0..=3"
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
