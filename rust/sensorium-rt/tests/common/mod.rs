//! Test support: run the `scenario` binary in its own process with its own
//! spool directory, and read the wire format back.
//!
//! **The parser here is written from the plan's wire-format block, not from
//! `src/spool.rs`.** A change to either side that the other does not follow has
//! to show up as a failing test rather than as two consistent mistakes. Nothing
//! in `common/spool.rs` may be re-derived from the writer; the byte offsets it
//! uses are transcribed from:
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

use std::path::{Path, PathBuf};
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

// The support code itself, one concern per file: the wire parser reads bytes,
// `run` starts subject processes, `json` reads the proc header. `mod.rs` keeps
// only the wire block above -- which every one of them is written against -- the
// constants it names, and the scratch directories, and re-exports the rest so a
// test still writes one `mod common;`.
mod json;
mod run;
mod spool;

#[allow(unused_imports)]
pub use json::Json;
#[allow(unused_imports)]
pub use run::{Run, Spec};
#[allow(unused_imports)]
pub use spool::{ErrSite, Record, SpoolFile};

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
