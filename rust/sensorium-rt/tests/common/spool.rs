//! The wire format, read back off the bytes.
//!
//! Transcribed from the format block in `mod.rs`, never re-derived from
//! `src/spool.rs`: a change on either side that the other does not follow has to
//! show up as a failing test rather than as two consistent mistakes.

use std::path::{Path, PathBuf};

use super::{
    HEADER_FIXED, KIND_HANDLED, KIND_PANIC, KIND_RAISE, KIND_RETURN, KIND_THREAD_END,
    KIND_UNWRITTEN, OUTCOME_ERR, RECORD_FIXED,
};

// ---------------------------------------------------------------------------
// The wire format, read back
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Record {
    pub seq: u64,
    pub ts_ns: u64,
    pub site: u32,
    pub kind: u8,
    pub outcome: u8,
    pub payload: Vec<u8>,
}

impl Record {
    pub fn unit_id(&self) -> u8 {
        (self.site >> 24) as u8
    }

    pub fn site_index(&self) -> u32 {
        self.site & 0x00ff_ffff
    }

    /// `(tag, truncated, text)` of a RETURN payload. On outcome 2 (`err`) the
    /// error-type block sits between the flags and the text, so the text starts
    /// past it; on every other outcome the payload is what wire v2 wrote.
    pub fn ret_value(&self) -> (u8, bool, String) {
        assert_eq!(self.kind, KIND_RETURN, "ret_value on a non-RETURN record");
        assert!(
            self.payload.len() >= 2,
            "a RETURN payload is at least the tag and the truncated flag, got {:?}",
            self.payload
        );
        let tag = self.payload[0];
        let trunc = self.payload[1];
        assert!(trunc <= 1, "truncated flag is 0 or 1, got {trunc}");
        let at = if self.outcome == OUTCOME_ERR {
            self.err_type_block().0
        } else {
            2
        };
        let text = String::from_utf8(self.payload[at..].to_vec())
            .unwrap_or_else(|e| panic!("RETURN text is not UTF-8: {e}"));
        (tag, trunc == 1, text)
    }

    /// `(end offset, type, truncated)` of an `err` RETURN's type block.
    fn err_type_block(&self) -> (usize, Option<String>, bool) {
        assert_eq!(
            self.outcome, OUTCOME_ERR,
            "only an err RETURN carries an error type"
        );
        assert!(
            self.payload.len() >= 5,
            "an err RETURN carries u8 tag, u8 truncated, u8 type_flags, u16 type_len, got {:?}",
            self.payload
        );
        let flags = self.payload[2];
        assert!(flags <= 3, "type_flags has two bits, got {flags:#b}");
        let len = u16::from_le_bytes(self.payload[3..5].try_into().unwrap()) as usize;
        let end = 5 + len;
        assert!(
            end <= self.payload.len(),
            "type_len {len} runs past the {}-byte payload",
            self.payload.len()
        );
        let text = String::from_utf8(self.payload[5..end].to_vec())
            .unwrap_or_else(|e| panic!("RETURN error type is not UTF-8: {e}"));
        let present = flags & 1 == 1;
        assert!(
            present || len == 0,
            "a type block that is not present cannot carry {len} bytes"
        );
        (end, present.then_some(text), flags & 2 == 2)
    }

    /// `(type, truncated)` of an `err` RETURN. `None` means the probe could not
    /// name the error type at all -- never "the type was empty".
    pub fn ret_err_type(&self) -> (Option<String>, bool) {
        let (_, text, truncated) = self.err_type_block();
        (text, truncated)
    }

    /// The `how`, type and message of a RAISE or HANDLED record.
    pub fn err_site(&self) -> ErrSite {
        assert!(
            self.kind == KIND_RAISE || self.kind == KIND_HANDLED,
            "err_site on a kind-{} record",
            self.kind
        );
        assert!(
            self.payload.len() >= 3,
            "a RAISE/HANDLED payload is at least u8 flags and u16 type_len, got {:?}",
            self.payload
        );
        let flags = self.payload[0];
        assert!(flags <= 0b1111, "flags has four bits, got {flags:#b}");
        let type_len = u16::from_le_bytes(self.payload[1..3].try_into().unwrap()) as usize;
        let end = 3 + type_len;
        assert!(
            end <= self.payload.len(),
            "type_len {type_len} runs past the {}-byte payload",
            self.payload.len()
        );
        let type_present = flags & 0b1000 != 0;
        assert!(
            type_present || type_len == 0,
            "an absent type cannot carry {type_len} bytes"
        );
        let type_name = String::from_utf8(self.payload[3..end].to_vec())
            .unwrap_or_else(|e| panic!("RAISE/HANDLED type is not UTF-8: {e}"));
        let msg = String::from_utf8(self.payload[end..].to_vec())
            .unwrap_or_else(|e| panic!("RAISE/HANDLED message is not UTF-8: {e}"));
        let msg_present = flags & 0b0001 != 0;
        assert!(
            msg_present || msg.is_empty(),
            "an absent message cannot carry {:?}",
            msg
        );
        ErrSite {
            how: self.outcome,
            type_name: type_present.then_some(type_name),
            msg: msg_present.then_some(msg),
            msg_truncated: flags & 0b0010 != 0,
            type_truncated: flags & 0b0100 != 0,
        }
    }

    /// `(location, message)` of a PANIC payload. The length field covers the
    /// location only; the message is whatever is left, so a message that
    /// contains no length of its own cannot be confused for one.
    pub fn panic_value(&self) -> (String, String) {
        assert_eq!(self.kind, KIND_PANIC, "panic_value on a non-PANIC record");
        assert!(
            self.payload.len() >= 2,
            "a PANIC payload is at least its u16 loc_len, got {:?}",
            self.payload
        );
        let loc_len = u16::from_le_bytes(self.payload[0..2].try_into().unwrap()) as usize;
        let end = 2 + loc_len;
        assert!(
            end <= self.payload.len(),
            "loc_len {loc_len} runs past the {}-byte payload",
            self.payload.len()
        );
        let loc = String::from_utf8(self.payload[2..end].to_vec())
            .unwrap_or_else(|e| panic!("PANIC location is not UTF-8: {e}"));
        let msg = String::from_utf8(self.payload[end..].to_vec())
            .unwrap_or_else(|e| panic!("PANIC message is not UTF-8: {e}"));
        (loc, msg)
    }
}

/// A RAISE or HANDLED record, unpacked. `None` is *absent*, never empty.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ErrSite {
    pub how: u8,
    pub type_name: Option<String>,
    pub msg: Option<String>,
    pub msg_truncated: bool,
    pub type_truncated: bool,
}

#[derive(Debug)]
pub struct SpoolFile {
    pub path: PathBuf,
    pub version: u8,
    pub flags: u8,
    pub serial: u32,
    pub name: String,
    pub records_dropped: u64,
    pub truncated: u64,
    pub records: Vec<Record>,
    /// Byte length of the whole file.
    pub file_len: usize,
    /// Offset the reader stopped at: either a `kind == 0` record or EOF.
    pub stopped_at: usize,
    /// True when every byte from `stopped_at` to EOF is zero.
    pub tail_is_zero: bool,
    /// True when the reader stopped because it met `kind == 0` (rather than EOF).
    pub stopped_on_unwritten: bool,
}

impl SpoolFile {
    pub fn parse(path: &Path) -> SpoolFile {
        let bytes =
            std::fs::read(path).unwrap_or_else(|e| panic!("reading {}: {e}", path.display()));
        let d = path.display();
        assert!(
            bytes.len() >= HEADER_FIXED,
            "{d}: {} bytes is shorter than the {HEADER_FIXED}-byte fixed header",
            bytes.len()
        );
        assert_eq!(&bytes[0..4], b"SNSR", "{d}: bad magic");
        let version = bytes[4];
        let flags = bytes[5];
        let name_len = u16::from_le_bytes(bytes[6..8].try_into().unwrap()) as usize;
        let serial = u32::from_le_bytes(bytes[8..12].try_into().unwrap());
        let records_dropped = u64::from_le_bytes(bytes[12..20].try_into().unwrap());
        let truncated = u64::from_le_bytes(bytes[20..28].try_into().unwrap());
        let head = HEADER_FIXED + name_len;
        assert!(bytes.len() >= head, "{d}: truncated thread name");
        let name = String::from_utf8(bytes[HEADER_FIXED..head].to_vec())
            .unwrap_or_else(|e| panic!("{d}: thread name is not UTF-8: {e}"));

        let mut records = Vec::new();
        let mut at = head;
        let mut stopped_on_unwritten = false;
        while at + RECORD_FIXED <= bytes.len() {
            let c = &bytes[at..at + RECORD_FIXED];
            let kind = c[20];
            if kind == KIND_UNWRITTEN {
                stopped_on_unwritten = true;
                break;
            }
            let payload_len = u16::from_le_bytes(c[22..24].try_into().unwrap()) as usize;
            let end = at + RECORD_FIXED + payload_len;
            assert!(
                end <= bytes.len(),
                "{d}: record at {at} claims a {payload_len}-byte payload that runs past EOF"
            );
            records.push(Record {
                seq: u64::from_le_bytes(c[0..8].try_into().unwrap()),
                ts_ns: u64::from_le_bytes(c[8..16].try_into().unwrap()),
                site: u32::from_le_bytes(c[16..20].try_into().unwrap()),
                kind,
                outcome: c[21],
                payload: bytes[at + RECORD_FIXED..end].to_vec(),
            });
            at = end;
        }
        let tail_is_zero = bytes[at..].iter().all(|b| *b == 0);
        SpoolFile {
            path: path.to_path_buf(),
            version,
            flags,
            serial,
            name,
            records_dropped,
            truncated,
            records,
            file_len: bytes.len(),
            stopped_at: at,
            tail_is_zero,
            stopped_on_unwritten,
        }
    }

    pub fn header_len(&self) -> usize {
        HEADER_FIXED + self.name.len()
    }

    pub fn of_kind(&self, kind: u8) -> Vec<Record> {
        self.records
            .iter()
            .filter(|r| r.kind == kind)
            .cloned()
            .collect()
    }

    pub fn has_thread_end(&self) -> bool {
        self.records.iter().any(|r| r.kind == KIND_THREAD_END)
    }

    /// The one RETURN record for `site_index`, asserting there is exactly one.
    pub fn the_return(&self, site_index: u32) -> Record {
        self.the_record(KIND_RETURN, site_index)
    }

    /// The one record of `kind` at `site_index`, asserting there is exactly one.
    pub fn the_record(&self, kind: u8, site_index: u32) -> Record {
        let mut hits: Vec<Record> = self
            .of_kind(kind)
            .into_iter()
            .filter(|r| r.site_index() == site_index)
            .collect();
        assert_eq!(
            hits.len(),
            1,
            "expected exactly one kind-{kind} record at site {site_index}, found {}: {hits:?}",
            hits.len()
        );
        hits.pop().unwrap()
    }

    /// Every RAISE and HANDLED record, in wire order, as `(kind, site, unpacked)`.
    pub fn err_sites(&self) -> Vec<(u8, u32, ErrSite)> {
        self.records
            .iter()
            .filter(|r| r.kind == KIND_RAISE || r.kind == KIND_HANDLED)
            .map(|r| (r.kind, r.site_index(), r.err_site()))
            .collect()
    }
}
