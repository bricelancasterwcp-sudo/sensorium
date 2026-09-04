//! Test support: run the `scenario` binary in its own process with its own
//! spool directory, and read the wire format back.
//!
//! **The parser here is written from the plan's wire-format block, not from
//! `src/spool.rs`.** A change to either side that the other does not follow has
//! to show up as a failing test rather than as two consistent mistakes. Nothing
//! in this file may be re-derived from the writer; the byte offsets below are
//! transcribed from:
//!
//! ```text
//! file header:  b"SNSR" u8 version=3 u8 flags=0 u16 name_len u32 thread_serial
//!               u64 records_dropped u64 truncated  name_bytes
//!               (fixed 28 bytes, then name_bytes; records start at 28 + name_len)
//! record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome_or_how  u16 payload_len
//!               [payload_len bytes]
//! kind:         0 = UNWRITTEN (the reader STOPS here), 1 = CALL, 2 = RETURN,
//!               3 = PANIC, 4 = RAISE, 5 = HANDLED, 255 = THREAD_END
//! outcome:      RETURN only: 0 none, 1 ok, 2 err, 3 panic; 0 on CALL, PANIC, THREAD_END
//! how:          RAISE/HANDLED only, in the same byte: 1 try, 2 sink_ok,
//!               3 sink_unwrap_or, 4 sink_let_underscore, 5 arm_propagate,
//!               6 arm_handled, 7 arm_ambiguous, 8 exit (converter-only, never on the wire)
//! site:         unit_id in bits 31..24, site index in bits 23..0
//! RETURN payload:  u8 tag (0 = no value, 1 = debug text follows, 2 = unread)
//!                  u8 truncated(0|1)
//!                  then ON OUTCOME 2 (err) ONLY: u8 type_flags (bit0 present, bit1 truncated)
//!                  u16 type_len, type UTF-8
//!                  then the value's UTF-8 text (rest)
//! RAISE/HANDLED payload:  u8 flags (bit0 msg present, bit1 msg truncated,
//!                  bit2 type truncated, bit3 type present)
//!                  u16 type_len, type UTF-8, then the Err's UTF-8 message (rest)
//! PANIC payload:   u16 loc_len, loc UTF-8 ("<file>:<line>:<col>" as the hook saw it),
//!                  then the message UTF-8 (rest)
//! ```
#![allow(dead_code)]

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicU32, Ordering};

pub const KIND_UNWRITTEN: u8 = 0;
pub const KIND_CALL: u8 = 1;
pub const KIND_RETURN: u8 = 2;
pub const KIND_PANIC: u8 = 3;
pub const KIND_RAISE: u8 = 4;
pub const KIND_HANDLED: u8 = 5;
pub const KIND_THREAD_END: u8 = 255;

pub const OUTCOME_NONE: u8 = 0;
pub const OUTCOME_OK: u8 = 1;
pub const OUTCOME_ERR: u8 = 2;
pub const OUTCOME_PANIC: u8 = 3;

pub const TAG_NO_VALUE: u8 = 0;
pub const TAG_DEBUG: u8 = 1;
pub const TAG_UNREAD: u8 = 2;

pub const HOW_TRY: u8 = 1;
pub const HOW_SINK_OK: u8 = 2;
pub const HOW_SINK_UNWRAP_OR: u8 = 3;
pub const HOW_SINK_LET_UNDERSCORE: u8 = 4;
pub const HOW_ARM_PROPAGATE: u8 = 5;
pub const HOW_ARM_HANDLED: u8 = 6;
pub const HOW_ARM_AMBIGUOUS: u8 = 7;

/// The two caps the wire block names, so a test can assert a cut length without
/// asking the writer what its own cap is.
pub const TYPE_CAP: usize = 120;
pub const MSG_CAP: usize = 200;

/// Fixed part of the file header, before the thread name.
pub const HEADER_FIXED: usize = 28;
/// Fixed part of a record, before its payload.
pub const RECORD_FIXED: usize = 24;

// ---------------------------------------------------------------------------
// Scratch directories
// ---------------------------------------------------------------------------

static COUNTER: AtomicU32 = AtomicU32::new(0);

/// Where scenario spool directories live. Derived from `CARGO_TARGET_DIR` when
/// the suite was invoked with one (this box runs every cargo command with it
/// pointed at the second disk), and from the system temp directory otherwise.
/// No box path is written down anywhere.
pub fn scenario_root() -> PathBuf {
    match std::env::var_os("CARGO_TARGET_DIR") {
        Some(t) if !t.is_empty() => PathBuf::from(t).join("rt-scenarios"),
        _ => std::env::temp_dir().join("sensorium-rt-scenarios"),
    }
}

pub struct TempDir {
    path: PathBuf,
}

impl TempDir {
    /// A path that does NOT exist yet: the inert tests assert the runtime never
    /// creates it.
    pub fn reserved(test: &str) -> TempDir {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let path = scenario_root().join(format!("{test}-{}-{n}", std::process::id()));
        let _ = std::fs::remove_dir_all(&path);
        std::fs::create_dir_all(path.parent().expect("scenario root has a parent"))
            .expect("creating the scenario root");
        TempDir { path }
    }

    /// The same, but the directory exists. Used as a sandbox root.
    pub fn created(test: &str) -> TempDir {
        let d = TempDir::reserved(test);
        std::fs::create_dir_all(&d.path).expect("creating the sandbox");
        d
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn exists(&self) -> bool {
        self.path.exists()
    }

    /// Every path under this directory, recursively.
    pub fn walk(&self) -> Vec<PathBuf> {
        fn go(dir: &Path, out: &mut Vec<PathBuf>) {
            let Ok(entries) = std::fs::read_dir(dir) else {
                return;
            };
            for e in entries.flatten() {
                let p = e.path();
                if p.is_dir() {
                    go(&p, out);
                }
                out.push(p);
            }
        }
        let mut out = Vec::new();
        go(&self.path, &mut out);
        out.sort();
        out
    }

    /// The assertion the inert tests need: the subject process wrote NOTHING
    /// anywhere it could reach without an absolute path of its own.
    pub fn assert_untouched(&self, what: &str) {
        let found = self.walk();
        assert!(
            found.is_empty(),
            "{what}: the run created {} path(s) under its sandbox {}: {found:?}",
            found.len(),
            self.path.display()
        );
    }

    /// Every `*.spool` file in the directory, ordered by thread serial.
    pub fn spools(&self) -> Vec<SpoolFile> {
        let mut out: Vec<SpoolFile> = std::fs::read_dir(&self.path)
            .unwrap_or_else(|e| panic!("reading {}: {e}", self.path.display()))
            .map(|e| e.expect("dir entry").path())
            .filter(|p| p.extension().map(|e| e == "spool").unwrap_or(false))
            .map(|p| SpoolFile::parse(&p))
            .collect();
        out.sort_by_key(|s| s.serial);
        out
    }

    pub fn spool(&self, serial: u32) -> SpoolFile {
        self.spools()
            .into_iter()
            .find(|s| s.serial == serial)
            .unwrap_or_else(|| panic!("no spool with serial {serial} in {}", self.path.display()))
    }

    pub fn spool_named(&self, name: &str) -> SpoolFile {
        self.spools()
            .into_iter()
            .find(|s| s.name == name)
            .unwrap_or_else(|| panic!("no spool named {name:?} in {}", self.path.display()))
    }

    pub fn proc_header_text(&self, pid: u32) -> String {
        let path = self.path.join(format!("{pid}.proc.json"));
        std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("reading {}: {e}", path.display()))
    }

    pub fn proc_header(&self, pid: u32) -> Json {
        Json::parse(&self.proc_header_text(pid))
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.path);
    }
}

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

// ---------------------------------------------------------------------------
// Running a scenario
// ---------------------------------------------------------------------------

pub struct Run {
    pub output: Output,
    pub pid: u32,
    pub stdout: String,
    pub stderr: String,
}

impl Run {
    /// The value the scenario printed as `<key> <value>`.
    pub fn says(&self, key: &str) -> String {
        self.stdout
            .lines()
            .find_map(|l| l.strip_prefix(&format!("{key} ")))
            .unwrap_or_else(|| panic!("scenario printed no {key:?} line; stdout: {}", self.stdout))
            .trim()
            .to_owned()
    }

    pub fn says_u64(&self, key: &str) -> u64 {
        self.says(key).parse().expect("a number")
    }
}

pub struct Spec<'a> {
    name: &'a str,
    args: Vec<&'a str>,
    dir: Option<&'a Path>,
    tier: Option<&'a str>,
    sandbox: Option<&'a Path>,
    env: Vec<(&'a str, String)>,
    allow_failure: bool,
}

impl<'a> Spec<'a> {
    pub fn new(name: &'a str) -> Spec<'a> {
        Spec {
            name,
            args: Vec::new(),
            dir: None,
            tier: None,
            sandbox: None,
            env: Vec::new(),
            allow_failure: false,
        }
    }

    pub fn arg(mut self, a: &'a str) -> Self {
        self.args.push(a);
        self
    }

    pub fn spool(mut self, d: &'a Path) -> Self {
        self.dir = Some(d);
        self
    }

    pub fn tier(mut self, t: &'a str) -> Self {
        self.tier = Some(t);
        self
    }

    pub fn sandbox(mut self, s: &'a Path) -> Self {
        self.sandbox = Some(s);
        self
    }

    pub fn env(mut self, k: &'a str, v: impl Into<String>) -> Self {
        self.env.push((k, v.into()));
        self
    }

    pub fn allow_failure(mut self) -> Self {
        self.allow_failure = true;
        self
    }

    fn command(&self) -> Command {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_scenario"));
        if let Some(s) = self.sandbox {
            cmd.current_dir(s);
            cmd.env("TMPDIR", s);
            cmd.env("HOME", s);
        }
        cmd.arg(self.name);
        cmd.args(&self.args);
        cmd.env_remove("SENSORIUM_SPOOL");
        cmd.env_remove("SENSORIUM_TIER");
        cmd.env_remove("SENSORIUM_TEST_SPOOL_LIMIT");
        if let Some(d) = self.dir {
            cmd.env("SENSORIUM_SPOOL", d);
        }
        if let Some(t) = self.tier {
            cmd.env("SENSORIUM_TIER", t);
        }
        for (k, v) in &self.env {
            cmd.env(k, v);
        }
        cmd
    }

    pub fn run(self) -> Run {
        let output = self
            .command()
            .output()
            .expect("running the scenario binary");
        let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        if !self.allow_failure {
            assert!(
                output.status.success(),
                "scenario {} failed: {:?}\nstdout: {stdout}\nstderr: {stderr}",
                self.name,
                output.status
            );
        }
        let pid = stdout
            .lines()
            .find_map(|l| l.strip_prefix("pid "))
            .and_then(|s| s.trim().parse().ok())
            .unwrap_or_else(|| {
                panic!(
                    "scenario {} did not print its pid; stdout: {stdout}",
                    self.name
                )
            });
        Run {
            output,
            pid,
            stdout,
            stderr,
        }
    }

    /// Start the scenario, wait for it to create `ready`, then SIGKILL it.
    /// Returns its pid.
    pub fn run_and_kill(self, ready: &Path) -> u32 {
        let mut child = self
            .command()
            .stdout(Stdio::piped())
            .spawn()
            .expect("spawning the scenario binary");
        let pid = child.id();
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(20);
        while !ready.exists() {
            assert!(
                std::time::Instant::now() < deadline,
                "the scenario never signalled ready at {}",
                ready.display()
            );
            if let Ok(Some(st)) = child.try_wait() {
                panic!("the scenario exited ({st:?}) before signalling ready");
            }
            std::thread::sleep(std::time::Duration::from_millis(5));
        }
        // SIGKILL, which no destructor and no handler can intercept.
        child.kill().expect("SIGKILL");
        let st = child.wait().expect("reaping the scenario");
        assert!(
            !st.success(),
            "a SIGKILLed process cannot exit successfully"
        );
        pid
    }
}

// ---------------------------------------------------------------------------
// A minimal JSON reader, for the proc header
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(BTreeMap<String, Json>),
}

impl Json {
    pub fn parse(s: &str) -> Json {
        let b = s.as_bytes();
        let mut at = 0usize;
        let v = parse_value(b, &mut at);
        skip_ws(b, &mut at);
        assert_eq!(
            at,
            b.len(),
            "trailing bytes after the JSON value: {:?}",
            &s[at..]
        );
        v
    }

    pub fn get(&self, key: &str) -> &Json {
        match self {
            Json::Obj(m) => m
                .get(key)
                .unwrap_or_else(|| panic!("no key {key:?} in {:?}", m.keys().collect::<Vec<_>>())),
            other => panic!("get({key:?}) on a non-object: {other:?}"),
        }
    }

    pub fn opt(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Obj(m) => m.get(key),
            other => panic!("opt({key:?}) on a non-object: {other:?}"),
        }
    }

    pub fn str(&self) -> &str {
        match self {
            Json::Str(s) => s,
            other => panic!("expected a string, got {other:?}"),
        }
    }

    pub fn u64(&self) -> u64 {
        match self {
            Json::Num(n) => *n as u64,
            other => panic!("expected a number, got {other:?}"),
        }
    }

    pub fn arr(&self) -> &[Json] {
        match self {
            Json::Arr(a) => a,
            other => panic!("expected an array, got {other:?}"),
        }
    }

    pub fn obj(&self) -> &BTreeMap<String, Json> {
        match self {
            Json::Obj(m) => m,
            other => panic!("expected an object, got {other:?}"),
        }
    }

    pub fn bool(&self) -> bool {
        match self {
            Json::Bool(b) => *b,
            other => panic!("expected a bool, got {other:?}"),
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Json::Null)
    }
}

fn skip_ws(b: &[u8], at: &mut usize) {
    while *at < b.len() && matches!(b[*at], b' ' | b'\t' | b'\n' | b'\r') {
        *at += 1;
    }
}

fn expect(b: &[u8], at: &mut usize, c: u8) {
    assert_eq!(
        b.get(*at).copied(),
        Some(c),
        "expected {:?} at byte {at}",
        c as char
    );
    *at += 1;
}

fn parse_value(b: &[u8], at: &mut usize) -> Json {
    skip_ws(b, at);
    match b.get(*at).copied().expect("unexpected end of JSON") {
        b'{' => parse_obj(b, at),
        b'[' => parse_arr(b, at),
        b'"' => Json::Str(parse_str(b, at)),
        b't' => {
            *at += 4;
            Json::Bool(true)
        }
        b'f' => {
            *at += 5;
            Json::Bool(false)
        }
        b'n' => {
            *at += 4;
            Json::Null
        }
        _ => parse_num(b, at),
    }
}

fn parse_obj(b: &[u8], at: &mut usize) -> Json {
    expect(b, at, b'{');
    let mut m = BTreeMap::new();
    skip_ws(b, at);
    if b.get(*at) == Some(&b'}') {
        *at += 1;
        return Json::Obj(m);
    }
    loop {
        skip_ws(b, at);
        let k = parse_str(b, at);
        skip_ws(b, at);
        expect(b, at, b':');
        let v = parse_value(b, at);
        m.insert(k, v);
        skip_ws(b, at);
        match b.get(*at).copied() {
            Some(b',') => *at += 1,
            Some(b'}') => {
                *at += 1;
                return Json::Obj(m);
            }
            other => panic!("expected ',' or '}}' at byte {at}, got {other:?}"),
        }
    }
}

fn parse_arr(b: &[u8], at: &mut usize) -> Json {
    expect(b, at, b'[');
    let mut a = Vec::new();
    skip_ws(b, at);
    if b.get(*at) == Some(&b']') {
        *at += 1;
        return Json::Arr(a);
    }
    loop {
        a.push(parse_value(b, at));
        skip_ws(b, at);
        match b.get(*at).copied() {
            Some(b',') => *at += 1,
            Some(b']') => {
                *at += 1;
                return Json::Arr(a);
            }
            other => panic!("expected ',' or ']' at byte {at}, got {other:?}"),
        }
    }
}

fn parse_str(b: &[u8], at: &mut usize) -> String {
    expect(b, at, b'"');
    let mut out = String::new();
    loop {
        let c = b.get(*at).copied().expect("unterminated string");
        *at += 1;
        match c {
            b'"' => return out,
            b'\\' => {
                let e = b.get(*at).copied().expect("dangling escape");
                *at += 1;
                match e {
                    b'"' => out.push('"'),
                    b'\\' => out.push('\\'),
                    b'/' => out.push('/'),
                    b'b' => out.push('\u{8}'),
                    b'f' => out.push('\u{c}'),
                    b'n' => out.push('\n'),
                    b'r' => out.push('\r'),
                    b't' => out.push('\t'),
                    b'u' => {
                        let hex = std::str::from_utf8(&b[*at..*at + 4]).expect("hex");
                        *at += 4;
                        let cp = u32::from_str_radix(hex, 16).expect("hex escape");
                        out.push(char::from_u32(cp).unwrap_or('\u{fffd}'));
                    }
                    other => panic!("unknown escape \\{}", other as char),
                }
            }
            _ => {
                // Copy the whole UTF-8 sequence this byte starts.
                let start = *at - 1;
                let extra = match c {
                    0x00..=0x7f => 0,
                    0xc0..=0xdf => 1,
                    0xe0..=0xef => 2,
                    _ => 3,
                };
                *at += extra;
                out.push_str(std::str::from_utf8(&b[start..*at]).expect("UTF-8 in a JSON string"));
            }
        }
    }
}

fn parse_num(b: &[u8], at: &mut usize) -> Json {
    let start = *at;
    while *at < b.len() && matches!(b[*at], b'0'..=b'9' | b'-' | b'+' | b'.' | b'e' | b'E') {
        *at += 1;
    }
    let s = std::str::from_utf8(&b[start..*at]).expect("number");
    Json::Num(
        s.parse()
            .unwrap_or_else(|e| panic!("bad number {s:?}: {e}")),
    )
}
