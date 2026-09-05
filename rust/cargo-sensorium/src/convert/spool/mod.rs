//! Reading everything a `cargo sensorium` invocation left on disk: the spool
//! wire format, the three JSON siblings beside it, and the unit manifests.
//!
//! **Independent of `sensorium-rt/src/spool.rs`.** That module WRITES the
//! wire format; this one reads it, from the same doc comment reproduced in
//! `rust/HONESTY.md` and the task brief -- not by importing the writer's
//! constants. A bug in one side is not free to cancel a bug in the other, and
//! the fixtures this reader is tested against are hand-built bytes, never the
//! output of running the runtime.
//!
//! Wire format v3, verbatim -- and v2, which this reader still accepts whole
//! (design R1: "a v2 spool still converts"). v3 adds the two err-flow kinds
//! and the error type on an `err` RETURN; nothing else moved, so every v2
//! payload below is read by the same code path it always was:
//!
//! ```text
//! file header:  b"SNSR" u8 version(2|3) u8 flags u16 name_len u32 thread_serial u64 records_dropped
//!               u64 truncated  name_bytes   (28 bytes fixed, then name_bytes)
//! record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome_or_how  u16 payload_len  [payload]
//! kind:         0 unwritten tail (STOP here), 1 CALL, 2 RETURN, 3 PANIC, 4 RAISE, 5 HANDLED,
//!               255 THREAD_END
//! outcome:      RETURN only: 0 none, 1 ok, 2 err, 3 panic
//! how:          RAISE/HANDLED only, the same byte: 1 try, 2 sink_ok, 3 sink_unwrap_or,
//!               4 sink_let_underscore, 5 arm_propagate, 6 arm_handled, 7 arm_ambiguous.
//!               8 (exit) is the converter's own synthesised origin and NEVER appears here.
//! RETURN payload:  u8 tag (0 none, 1 debug text, 2 unread)  u8 truncated
//!                  then, ON OUTCOME 2 (err) AND VERSION 3 ONLY: u8 type_flags (bit0 present,
//!                  bit1 truncated)  u16 type_len  type UTF-8
//!                  then the value's UTF-8 text (rest)
//! RAISE/HANDLED payload:  u8 flags (bit0 msg present, bit1 msg truncated, bit2 type truncated,
//!                  bit3 type present)  u16 type_len  type UTF-8  msg UTF-8 (rest)
//! PANIC payload:   u16 loc_len  loc UTF-8  msg UTF-8 (rest)
//! ```

use std::collections::BTreeMap;
use std::path::Path;

use serde::Deserialize;

const HEADER_FIXED: usize = 28;
const RECORD_FIXED: usize = 24;

pub const KIND_UNWRITTEN: u8 = 0;
pub const KIND_CALL: u8 = 1;
pub const KIND_RETURN: u8 = 2;
pub const KIND_PANIC: u8 = 3;
pub const KIND_RAISE: u8 = 4;
pub const KIND_HANDLED: u8 = 5;
pub const KIND_THREAD_END: u8 = 255;

/// The wire versions this converter reads. v2 is rung 2's; v3 is rung 3's
/// (design R1). Both are read whole -- a v2 spool converts under this reader
/// exactly as it did under the v2-only one.
const VERSION_V2: u8 = 2;
const VERSION_V3: u8 = 3;

/// What an err-flow record says was DONE with the `Err` it saw (design R2),
/// carried in the record header's `outcome` byte.
///
/// Eight names, seven of which a runtime can write: [`How::Exit`] is the
/// converter's own, synthesised in front of a frame that closed `err` so a
/// chain born by returning has an origin record. Meeting it on the wire is a
/// malformed record, not a value -- [`How::from_wire`] is the only place that
/// judgement is made.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum How {
    Try,
    SinkOk,
    SinkUnwrapOr,
    SinkLetUnderscore,
    ArmPropagate,
    ArmHandled,
    ArmAmbiguous,
    /// Converter-synthesised: a frame closing `err`. Never on the wire.
    Exit,
}

impl How {
    /// The `how` byte, or `None` for one no runtime may write -- 0, `exit`
    /// (8), and anything above.
    #[must_use]
    pub fn from_wire(byte: u8) -> Option<How> {
        match byte {
            1 => Some(How::Try),
            2 => Some(How::SinkOk),
            3 => Some(How::SinkUnwrapOr),
            4 => Some(How::SinkLetUnderscore),
            5 => Some(How::ArmPropagate),
            6 => Some(How::ArmHandled),
            7 => Some(How::ArmAmbiguous),
            _ => None,
        }
    }

    /// The name the manifest and the event payload both spell it by.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            How::Try => "try",
            How::SinkOk => "sink_ok",
            How::SinkUnwrapOr => "sink_unwrap_or",
            How::SinkLetUnderscore => "sink_let_underscore",
            How::ArmPropagate => "arm_propagate",
            How::ArmHandled => "arm_handled",
            How::ArmAmbiguous => "arm_ambiguous",
            How::Exit => "exit",
        }
    }

    /// A `how` that lets the `Err` OUT of the frame writes a RAISE; every
    /// other writes a HANDLED. The converter's own `exit` is a RAISE.
    #[must_use]
    pub fn is_raise(self) -> bool {
        matches!(self, How::Try | How::ArmPropagate | How::Exit)
    }

    /// A `how` that ABSORBS the `Err` and could therefore make its chain a
    /// SWALLOWED candidate (design R8). `arm_ambiguous` is HANDLED-class and
    /// deliberately NOT one of these.
    #[must_use]
    pub fn is_sink(self) -> bool {
        matches!(
            self,
            How::SinkOk | How::SinkUnwrapOr | How::SinkLetUnderscore | How::ArmHandled
        )
    }

    /// The record kind a `how` must have arrived under. A RAISE carrying a
    /// sink's `how` is corruption: the two facts are written from the same
    /// byte by the same call.
    #[must_use]
    pub fn wire_kind(self) -> u8 {
        if self.is_raise() {
            KIND_RAISE
        } else {
            KIND_HANDLED
        }
    }
}

/// A recorded error type as the reader uses it: match ergonomics may bind an
/// `Err(e) =>` arm's error by REFERENCE, so `&io::Error` and `io::Error` are
/// the same `E` seen from two sites (design R4). One leading `&` or `&mut ` is
/// removed -- one, not all: a type that is genuinely a reference to a
/// reference is not a binding artefact, and flattening it would invent a type
/// the program does not have.
#[must_use]
pub fn strip_ref(type_name: &str) -> &str {
    if let Some(rest) = type_name.strip_prefix("&mut ") {
        return rest;
    }
    type_name.strip_prefix('&').unwrap_or(type_name)
}

/// One complete record (`kind != 0`), exactly as the bytes say.
#[derive(Debug, Clone)]
pub struct RawRecord {
    pub seq: u64,
    pub ts_ns: u64,
    pub site: u32,
    pub kind: u8,
    pub outcome: u8,
    pub payload: Vec<u8>,
}

/// One `<pid>.<serial>.spool` file: its header and every complete record.
#[derive(Debug, Clone)]
pub struct SpoolFile {
    pub serial: u32,
    pub name: String,
    pub records_dropped: u64,
    pub truncated: u64,
    /// The header's wire version (2 or 3). Carried per FILE, not per process:
    /// it is what decides whether an `err` RETURN's payload holds the error
    /// type block, and a reader that guessed it from the process instead would
    /// misread a directory holding both.
    pub version: u8,
    pub records: Vec<RawRecord>,
}

/// Read and parse one spool file's bytes, for the label an error names.
///
/// # Errors
/// A short magic/version, a header past the end of the file, a payload that
/// runs past the end of the file, or a `seq` that does not strictly increase
/// from one record to the next within this file (`rust/HONESTY.md` §4: within
/// one thread's own spool, `seq` is written in strictly increasing order by
/// construction, so anything else is corruption, not a race).
pub fn parse_spool_bytes(label: &str, bytes: &[u8]) -> Result<SpoolFile, String> {
    if bytes.len() < HEADER_FIXED {
        return Err(format!(
            "{label}: {} bytes is shorter than the 28-byte header",
            bytes.len()
        ));
    }
    if &bytes[0..4] != b"SNSR" {
        return Err(format!("{label}: bad magic (not a sensorium spool file)"));
    }
    let version = bytes[4];
    if version != VERSION_V2 && version != VERSION_V3 {
        return Err(format!(
            "{label}: wire format version {version}, this converter reads versions 2 and 3"
        ));
    }
    let name_len = u16::from_le_bytes([bytes[6], bytes[7]]) as usize;
    let serial = u32::from_le_bytes([bytes[8], bytes[9], bytes[10], bytes[11]]);
    let records_dropped = u64::from_le_bytes(bytes[12..20].try_into().unwrap());
    let truncated = u64::from_le_bytes(bytes[20..28].try_into().unwrap());
    let header_len = HEADER_FIXED + name_len;
    if bytes.len() < header_len {
        return Err(format!(
            "{label}: header claims a {name_len}-byte name past the end of the file"
        ));
    }
    let name = String::from_utf8(bytes[HEADER_FIXED..header_len].to_vec())
        .map_err(|e| format!("{label}: thread name is not UTF-8: {e}"))?;

    let mut records = Vec::new();
    let mut pos = header_len;
    let mut last_seq: Option<u64> = None;
    while pos + RECORD_FIXED <= bytes.len() {
        let kind = bytes[pos + 20];
        if kind == KIND_UNWRITTEN {
            break;
        }
        let seq = u64::from_le_bytes(bytes[pos..pos + 8].try_into().unwrap());
        let ts_ns = u64::from_le_bytes(bytes[pos + 8..pos + 16].try_into().unwrap());
        let site = u32::from_le_bytes(bytes[pos + 16..pos + 20].try_into().unwrap());
        let outcome = bytes[pos + 21];
        let payload_len = u16::from_le_bytes([bytes[pos + 22], bytes[pos + 23]]) as usize;
        let payload_start = pos + RECORD_FIXED;
        let payload_end = payload_start + payload_len;
        if payload_end > bytes.len() {
            return Err(format!(
                "{label}: record at seq {seq} claims a {payload_len}-byte payload past the end of \
                 the file"
            ));
        }
        if let Some(prev) = last_seq {
            if seq <= prev {
                return Err(format!(
                    "{label}: seq goes backwards at position {pos} ({prev} then {seq})"
                ));
            }
        }
        last_seq = Some(seq);
        records.push(RawRecord {
            seq,
            ts_ns,
            site,
            kind,
            outcome,
            payload: bytes[payload_start..payload_end].to_vec(),
        });
        pos = payload_end;
    }

    Ok(SpoolFile {
        serial,
        name,
        records_dropped,
        truncated,
        version,
        records,
    })
}

/// `<dir>/<pid>.<serial>.spool`.
///
/// # Errors
/// A filesystem failure, or [`parse_spool_bytes`]'s.
pub fn read_spool_file(path: &Path) -> Result<SpoolFile, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    parse_spool_bytes(&path.display().to_string(), &bytes)
}

/// unit_id in bits 31..24, site index in bits 23..0 (0 on PANIC and
/// THREAD_END, where no site applies).
#[must_use]
pub fn unpack_site(site: u32) -> (u8, u32) {
    ((site >> 24) as u8, site & 0x00ff_ffff)
}

/// A RETURN payload's tag byte.
pub const TAG_NO_VALUE: u8 = 0;
pub const TAG_DEBUG: u8 = 1;
pub const TAG_UNREAD: u8 = 2;

/// `u8 tag, u8 truncated, [type block,] UTF-8 text` decoded.
#[derive(Debug)]
pub struct ReturnPayload {
    pub tag: u8,
    pub truncated: bool,
    pub text: String,
    /// The `Result`'s error type, on a v3 `err` RETURN whose type block said it
    /// was there. `None` covers three different facts a caller must not
    /// conflate: this is not an `err` RETURN, this is a v2 spool that carries
    /// no type block at all, or the ladder could not name the type -- which is
    /// why [`ReturnPayload::typed_err`] answers the second one separately.
    pub err_type: Option<String>,
    pub err_type_truncated: bool,
}

/// Decode a RETURN payload. `err_type_block` says whether the two fixed bytes
/// are followed by the error type block -- true only for an `err` outcome on a
/// v3 spool, which is the only place the runtime writes one.
///
/// # Errors
/// A payload shorter than its two fixed bytes, a type block that runs past the
/// payload, or non-UTF-8 text.
pub fn parse_return_payload(
    label: &str,
    payload: &[u8],
    err_type_block: bool,
) -> Result<ReturnPayload, String> {
    if payload.len() < 2 {
        return Err(format!(
            "{label}: RETURN payload is shorter than its 2 fixed bytes"
        ));
    }
    let mut at = 2;
    let mut err_type = None;
    let mut err_type_truncated = false;
    if err_type_block {
        if payload.len() < 5 {
            return Err(format!(
                "{label}: an err RETURN payload is shorter than its 5 fixed bytes"
            ));
        }
        let flags = payload[2];
        let type_len = u16::from_le_bytes([payload[3], payload[4]]) as usize;
        if payload.len() < 5 + type_len {
            return Err(format!(
                "{label}: RETURN payload's type_len {type_len} runs past the payload"
            ));
        }
        let text = std::str::from_utf8(&payload[5..5 + type_len])
            .map_err(|e| format!("{label}: RETURN error type is not UTF-8: {e}"))?;
        if flags & 1 != 0 {
            err_type = Some(strip_ref(text).to_owned());
        } else if type_len != 0 {
            return Err(format!(
                "{label}: RETURN payload declares no error type but carries {type_len} bytes of one"
            ));
        }
        err_type_truncated = flags & 2 != 0;
        at = 5 + type_len;
    }
    let text = String::from_utf8(payload[at..].to_vec())
        .map_err(|e| format!("{label}: RETURN payload text is not UTF-8: {e}"))?;
    Ok(ReturnPayload {
        tag: payload[0],
        truncated: payload[1] != 0,
        text,
        err_type,
        err_type_truncated,
    })
}

/// A RAISE/HANDLED payload decoded: what the site saw of the `Err`.
///
/// `type_name: None` and `msg: None` are UNREAD, never empty -- the flags byte
/// is what separates a `Debug` impl that rendered nothing from one the ladder
/// could not reach at all, and this struct keeps the two apart.
#[derive(Debug)]
pub struct ErrFlowPayload {
    pub type_name: Option<String>,
    pub type_truncated: bool,
    pub msg: Option<String>,
    pub msg_truncated: bool,
}

const ERR_FLAG_MSG_PRESENT: u8 = 1 << 0;
const ERR_FLAG_MSG_TRUNCATED: u8 = 1 << 1;
const ERR_FLAG_TYPE_TRUNCATED: u8 = 1 << 2;
const ERR_FLAG_TYPE_PRESENT: u8 = 1 << 3;

/// # Errors
/// A payload shorter than its three fixed bytes, a `type_len` past the end of
/// it, non-UTF-8 text, or a flags byte that disagrees with the bytes that
/// follow it (a type or a message the flags say is absent, present anyway).
pub fn parse_errflow_payload(label: &str, payload: &[u8]) -> Result<ErrFlowPayload, String> {
    if payload.len() < 3 {
        return Err(format!(
            "{label}: RAISE/HANDLED payload is shorter than its 3 fixed bytes"
        ));
    }
    let flags = payload[0];
    let type_len = u16::from_le_bytes([payload[1], payload[2]]) as usize;
    if payload.len() < 3 + type_len {
        return Err(format!(
            "{label}: RAISE/HANDLED payload's type_len {type_len} runs past the payload"
        ));
    }
    let type_text = std::str::from_utf8(&payload[3..3 + type_len])
        .map_err(|e| format!("{label}: RAISE/HANDLED error type is not UTF-8: {e}"))?;
    let msg_text = std::str::from_utf8(&payload[3 + type_len..])
        .map_err(|e| format!("{label}: RAISE/HANDLED message is not UTF-8: {e}"))?;
    let type_present = flags & ERR_FLAG_TYPE_PRESENT != 0;
    let msg_present = flags & ERR_FLAG_MSG_PRESENT != 0;
    if !type_present && type_len != 0 {
        return Err(format!(
            "{label}: RAISE/HANDLED payload declares no type but carries {type_len} bytes of one"
        ));
    }
    if !msg_present && !msg_text.is_empty() {
        return Err(format!(
            "{label}: RAISE/HANDLED payload declares no message but carries {} bytes of one",
            msg_text.len()
        ));
    }
    Ok(ErrFlowPayload {
        type_name: type_present.then(|| strip_ref(type_text).to_owned()),
        type_truncated: flags & ERR_FLAG_TYPE_TRUNCATED != 0,
        msg: msg_present.then(|| msg_text.to_owned()),
        msg_truncated: flags & ERR_FLAG_MSG_TRUNCATED != 0,
    })
}

/// The `how` an err-flow record's header byte carries.
///
/// # Errors
/// A byte no runtime writes (0, the converter-only `exit`, or anything above),
/// or one whose class disagrees with the record's own kind -- both are written
/// from the same call by the same `how`, so a RAISE bearing a sink's `how` is
/// corruption rather than a shape.
pub fn parse_how(label: &str, kind: u8, byte: u8) -> Result<How, String> {
    let how = How::from_wire(byte).ok_or_else(|| {
        format!("{label}: err-flow record's how byte {byte} is not one a runtime may write (1..=7)")
    })?;
    if how.wire_kind() != kind {
        return Err(format!(
            "{label}: how {} belongs to record kind {}, not {kind}",
            how.as_str(),
            how.wire_kind()
        ));
    }
    Ok(how)
}

/// `u16 loc_len, loc UTF-8, msg UTF-8` decoded.
pub struct PanicPayload {
    pub loc: String,
    pub msg: String,
}

/// # Errors
/// A payload shorter than its `loc_len` claims, or non-UTF-8 text.
pub fn parse_panic_payload(label: &str, payload: &[u8]) -> Result<PanicPayload, String> {
    if payload.len() < 2 {
        return Err(format!(
            "{label}: PANIC payload is shorter than its 2-byte loc_len"
        ));
    }
    let loc_len = u16::from_le_bytes([payload[0], payload[1]]) as usize;
    if payload.len() < 2 + loc_len {
        return Err(format!(
            "{label}: PANIC payload's loc_len {loc_len} runs past the payload"
        ));
    }
    let loc = String::from_utf8(payload[2..2 + loc_len].to_vec())
        .map_err(|e| format!("{label}: PANIC location is not UTF-8: {e}"))?;
    let msg = String::from_utf8(payload[2 + loc_len..].to_vec())
        .map_err(|e| format!("{label}: PANIC message is not UTF-8: {e}"))?;
    Ok(PanicPayload { loc, msg })
}

// ---------------------------------------------------------------------------
// The JSON siblings
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct RefusedAt {
    pub at: String,
}

/// `<spool>/<pid>.proc.json`.
#[derive(Debug, Deserialize)]
pub struct ProcHeader {
    /// The filename already names this pid, and the converter always reads
    /// the two in lockstep; kept because it is the wire's own field and a
    /// consumer that opens the JSON directly (a test, a future tool) should
    /// not have to trust the filename instead.
    #[allow(dead_code)]
    pub pid: u32,
    pub ppid: u32,
    pub exe: String,
    pub argv: Vec<String>,
    pub cwd: String,
    pub start_ns: u64,
    pub start_realtime_ns: u64,
    #[serde(default)]
    pub env: BTreeMap<String, String>,
    pub env_hash: String,
    /// `"<unit_id>"` (decimal) -> metadata.
    pub units: BTreeMap<String, String>,
    pub refused: Option<RefusedAt>,
    pub rt_version: String,
    /// The Rust-only capability keys the RUNTIME declared (design R9). Passed
    /// through into the trace's `capabilities` untouched -- what a rung-2 spool
    /// is missing here is a record, not an opinion, so a header with no
    /// `capabilities` object reads as an empty map and every key it would have
    /// carried is absent.
    #[serde(default)]
    pub capabilities: BTreeMap<String, bool>,
}

impl ProcHeader {
    /// # Errors
    /// A filesystem or JSON failure.
    pub fn read(path: &Path) -> Result<ProcHeader, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a valid proc header: {e}", path.display()))
    }

    /// Registered units, ordered by their numeric unit id.
    #[must_use]
    pub fn units_in_order(&self) -> Vec<String> {
        let mut ids: Vec<(u32, &String)> = self
            .units
            .iter()
            .filter_map(|(k, v)| k.parse::<u32>().ok().map(|id| (id, v)))
            .collect();
        ids.sort_by_key(|(id, _)| *id);
        ids.into_iter().map(|(_, v)| v.clone()).collect()
    }
}

/// `<spool>/<pid>.runner.json`.
#[derive(Debug, Deserialize)]
pub struct RunnerRecord {
    pub exit_status: Option<i32>,
    pub signal: Option<i32>,
    pub wall_start_ts: f64,
    pub wall_end_ts: f64,
}

impl RunnerRecord {
    /// # Errors
    /// A filesystem or JSON failure.
    pub fn read(path: &Path) -> Result<RunnerRecord, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a valid runner record: {e}", path.display()))
    }
}

/// `<spool>/invocation.json`.
#[derive(Debug, Deserialize)]
pub struct InvocationRecord {
    pub invocation: String,
    pub cargo_args: Vec<String>,
    pub toolchain: String,
    pub rustc_path: String,
    pub profile: String,
    pub workspace_root: String,
    pub target_dir: String,
    pub tool_hash: String,
    pub driver_version: String,
}

impl InvocationRecord {
    /// # Errors
    /// A filesystem or JSON failure.
    pub fn read(path: &Path) -> Result<InvocationRecord, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a valid invocation record: {e}", path.display()))
    }
}

#[cfg(test)]
mod tests;
