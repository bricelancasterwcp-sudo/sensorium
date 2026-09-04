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
//! Wire format v2, verbatim:
//!
//! ```text
//! file header:  b"SNSR" u8 version=2 u8 flags u16 name_len u32 thread_serial u64 records_dropped
//!               u64 truncated  name_bytes   (28 bytes fixed, then name_bytes)
//! record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome  u16 payload_len  [payload]
//! kind:         0 unwritten tail (STOP here), 1 CALL, 2 RETURN, 3 PANIC, 255 THREAD_END
//! RETURN payload:  u8 tag (0 none, 1 debug text, 2 unread)  u8 truncated  UTF-8 text
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
pub const KIND_THREAD_END: u8 = 255;

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
    if version != 2 {
        return Err(format!(
            "{label}: wire format version {version}, this converter reads version 2"
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

/// `u8 tag, u8 truncated, UTF-8 text` decoded.
pub struct ReturnPayload {
    pub tag: u8,
    pub truncated: bool,
    pub text: String,
}

/// # Errors
/// A payload shorter than its two fixed bytes, or non-UTF-8 text.
pub fn parse_return_payload(label: &str, payload: &[u8]) -> Result<ReturnPayload, String> {
    if payload.len() < 2 {
        return Err(format!(
            "{label}: RETURN payload is shorter than its 2 fixed bytes"
        ));
    }
    let text = String::from_utf8(payload[2..].to_vec())
        .map_err(|e| format!("{label}: RETURN payload text is not UTF-8: {e}"))?;
    Ok(ReturnPayload {
        tag: payload[0],
        truncated: payload[1] != 0,
        text,
    })
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

// ---------------------------------------------------------------------------
// Unit manifests
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RetKind {
    Unit,
    Value,
    Never,
}

#[derive(Debug, Deserialize)]
pub struct ManifestSite {
    pub site: u32,
    pub qualname: String,
    pub firstlineno: u32,
    pub ret: RetKind,
}

/// `<target>/sensorium/manifests/<metadata>.json`, read back. A separate type
/// from `sensorium_transform::Manifest`, which is serialise-only.
#[derive(Debug, Deserialize)]
pub struct Manifest {
    /// The manifest's own filename already names this (its stem is the
    /// metadata); kept for the same reason as [`ProcHeader::pid`].
    #[allow(dead_code)]
    pub unit: String,
    pub crate_name: String,
    #[serde(default)]
    pub files: BTreeMap<String, Vec<ManifestSite>>,
    #[serde(default)]
    pub skipped: Vec<serde_json::Value>,
    #[serde(default)]
    pub spawns: Vec<serde_json::Value>,
    #[serde(default)]
    pub source_hashes: BTreeMap<String, String>,
    pub fell_back: bool,
    pub fallback_reason: Option<String>,
    #[serde(default)]
    pub unreached_files: Vec<String>,
    /// The workspace the wrapper compiled this unit under
    /// (`SENSORIUM_WS`). `#[serde(default)]` so a manifest written before
    /// this field existed deserialises as `""` -- treated as "not in scope
    /// of any invocation" by `manifest_in_scope`, and counted in the meta
    /// key `manifests_unscoped` rather than silently excluded with no trace.
    #[serde(default)]
    pub workspace_root: String,
}

/// One site, as the converter needs it: which file it is in (the manifest's
/// own key -- workspace-relative), and everything the manifest says about it.
pub struct SiteInfo {
    pub file: String,
    pub qualname: String,
    pub firstlineno: u32,
    pub ret: RetKind,
}

impl Manifest {
    /// # Errors
    /// A filesystem or JSON failure, or a file key naming a path under
    /// `sensorium/mirror` -- a manifest that names the internal mirror tree
    /// instead of the workspace-relative source is a hard error naming the
    /// manifest file, not a value this converter passes through.
    pub fn read(path: &Path) -> Result<Manifest, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        let m: Manifest = serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a valid manifest: {e}", path.display()))?;
        for rel in m
            .files
            .keys()
            .chain(m.unreached_files.iter())
            .chain(m.source_hashes.keys())
        {
            if rel.contains("sensorium/mirror") {
                return Err(format!(
                    "{}: names a mirror path {rel:?}, not a workspace-relative one",
                    path.display()
                ));
            }
        }
        Ok(m)
    }

    /// Flatten `files` into a lookup by the unit-relative site index the wire
    /// format's `site` word carries.
    #[must_use]
    pub fn sites_by_index(&self) -> BTreeMap<u32, SiteInfo> {
        let mut out = BTreeMap::new();
        for (file, sites) in &self.files {
            for s in sites {
                out.insert(
                    s.site,
                    SiteInfo {
                        file: file.clone(),
                        qualname: s.qualname.clone(),
                        firstlineno: s.firstlineno,
                        ret: s.ret,
                    },
                );
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn header(name: &str, records_dropped: u64, truncated: u64) -> Vec<u8> {
        let mut b = vec![0u8; HEADER_FIXED];
        b[0..4].copy_from_slice(b"SNSR");
        b[4] = 2;
        b[5] = 0;
        b[6..8].copy_from_slice(&(name.len() as u16).to_le_bytes());
        b[8..12].copy_from_slice(&7u32.to_le_bytes());
        b[12..20].copy_from_slice(&records_dropped.to_le_bytes());
        b[20..28].copy_from_slice(&truncated.to_le_bytes());
        b.extend_from_slice(name.as_bytes());
        b
    }

    fn record(seq: u64, ts_ns: u64, site: u32, kind: u8, outcome: u8, payload: &[u8]) -> Vec<u8> {
        let mut b = Vec::new();
        b.extend_from_slice(&seq.to_le_bytes());
        b.extend_from_slice(&ts_ns.to_le_bytes());
        b.extend_from_slice(&site.to_le_bytes());
        b.push(kind);
        b.push(outcome);
        b.extend_from_slice(&(payload.len() as u16).to_le_bytes());
        b.extend_from_slice(payload);
        b
    }

    #[test]
    fn a_header_with_no_records_parses_to_an_empty_stream() {
        let bytes = header("main", 0, 0);
        let s = parse_spool_bytes("t", &bytes).unwrap();
        assert_eq!(s.serial, 7);
        assert_eq!(s.name, "main");
        assert!(s.records.is_empty());
    }

    #[test]
    fn a_torn_tail_kind_zero_stops_the_reader_without_erroring() {
        let mut bytes = header("t", 0, 0);
        bytes.extend(record(0, 100, 1, KIND_CALL, 0, &[]));
        bytes.extend(vec![0u8; RECORD_FIXED]); // kind 0: the unwritten tail
        let s = parse_spool_bytes("t", &bytes).unwrap();
        assert_eq!(s.records.len(), 1);
    }

    #[test]
    fn seq_going_backwards_is_a_named_error() {
        let mut bytes = header("t", 0, 0);
        bytes.extend(record(5, 1, 0, KIND_CALL, 0, &[]));
        bytes.extend(record(3, 2, 0, KIND_CALL, 0, &[]));
        let err = parse_spool_bytes("t.spool", &bytes).unwrap_err();
        assert!(err.contains("t.spool"), "{err}");
        assert!(err.contains("backwards"), "{err}");
    }

    #[test]
    fn a_bad_magic_is_refused() {
        let bytes = vec![0u8; HEADER_FIXED];
        let err = parse_spool_bytes("x", &bytes).unwrap_err();
        assert!(err.contains("magic"), "{err}");
    }

    #[test]
    fn a_return_payload_decodes_tag_truncated_and_text() {
        let p = parse_return_payload("t", &[1, 1, b'O', b'k']).unwrap();
        assert_eq!(p.tag, TAG_DEBUG);
        assert!(p.truncated);
        assert_eq!(p.text, "Ok");
    }

    #[test]
    fn a_panic_payload_splits_loc_and_msg_on_loc_len() {
        let mut bytes = 3u16.to_le_bytes().to_vec();
        bytes.extend_from_slice(b"a.rs");
        bytes.extend_from_slice(b"boom");
        // loc_len = 3 but "a.rs" is 4 bytes: loc = "a.r", msg = "sboom".
        let p = parse_panic_payload("t", &bytes).unwrap();
        assert_eq!(p.loc, "a.r");
        assert_eq!(p.msg, "sboom");
    }

    #[test]
    fn units_in_order_sorts_by_numeric_id_not_by_string() {
        let mut units = BTreeMap::new();
        units.insert("10".to_owned(), "ten".to_owned());
        units.insert("2".to_owned(), "two".to_owned());
        let header = ProcHeader {
            pid: 1,
            ppid: 0,
            exe: String::new(),
            argv: vec![],
            cwd: String::new(),
            start_ns: 0,
            start_realtime_ns: 0,
            env: BTreeMap::new(),
            env_hash: String::new(),
            units,
            refused: None,
            rt_version: String::new(),
        };
        assert_eq!(
            header.units_in_order(),
            vec!["two".to_owned(), "ten".to_owned()]
        );
    }

    #[test]
    fn a_manifest_naming_a_mirror_path_is_refused() {
        let dir = std::env::temp_dir().join(format!("manifest-mirror-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.json");
        std::fs::write(
            &path,
            r#"{"unit":"a","crate_name":"c","crate_type":"lib","files":{"target/sensorium/mirror/a/src/lib.rs":[]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,"fallback_reason":null,"unreached_files":[]}"#,
        )
        .unwrap();
        let err = Manifest::read(&path).unwrap_err();
        assert!(err.contains("mirror path"), "{err}");
    }

    #[test]
    fn sites_by_index_flattens_across_files() {
        let dir = std::env::temp_dir().join(format!("manifest-sites-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.json");
        std::fs::write(
            &path,
            r#"{"unit":"a","crate_name":"c","crate_type":"lib",
               "files":{"a/lib.rs":[{"site":0,"qualname":"root","firstlineno":1,"ret":"unit"}],
                        "a/m.rs":[{"site":1,"qualname":"one","firstlineno":2,"ret":"value"}]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,"fallback_reason":null,"unreached_files":[]}"#,
        )
        .unwrap();
        let m = Manifest::read(&path).unwrap();
        let sites = m.sites_by_index();
        assert_eq!(sites[&0].qualname, "root");
        assert_eq!(sites[&0].file, "a/lib.rs");
        assert_eq!(sites[&1].ret, RetKind::Value);
    }

    /// The wrapper writes `unreached_reasons` (why a file the walk reached was
    /// still not rewritten) and this converter has nothing to say about it: the
    /// trace format carries no such key. That only works because this struct
    /// does NOT deny unknown fields -- add `#[serde(deny_unknown_fields)]` and
    /// every manifest the current wrapper writes becomes unreadable, taking the
    /// whole unit's sites down with it.
    #[test]
    fn a_manifest_key_this_converter_has_no_field_for_is_ignored_not_refused() {
        let dir = std::env::temp_dir().join(format!("manifest-unknown-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.json");
        std::fs::write(
            &path,
            r#"{"unit":"a","crate_name":"c","crate_type":"lib",
               "files":{"a/lib.rs":[{"site":0,"qualname":"root","firstlineno":1,"ret":"unit"}]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,"fallback_reason":null,
               "unreached_files":["a/bad.rs"],
               "unreached_reasons":{"a/bad.rs":"spawn site outside any named item"}}"#,
        )
        .unwrap();
        let m = Manifest::read(&path).expect("a manifest with an extra key still reads");
        assert_eq!(m.unreached_files, ["a/bad.rs"]);
        assert_eq!(m.sites_by_index()[&0].qualname, "root");
    }
}
