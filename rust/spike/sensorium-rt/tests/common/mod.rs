//! THROWAWAY SPIKE CODE. Test support: run the `scenario` binary in its own
//! process with its own spool directory, and read the wire format back.
//!
//! The parser here is written from the brief's wire-format block, not from
//! `spool.rs`, so a change to either side that the other does not follow shows
//! up as a test failure rather than as two consistent mistakes.
#![allow(dead_code)]

use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU32, Ordering};

pub const KIND_CALL: u8 = 1;
pub const KIND_RETURN: u8 = 2;
pub const KIND_THREAD_END: u8 = 255;
pub const OUTCOME_NONE: u8 = 0;
pub const OUTCOME_PANIC: u8 = 3;
pub const RECORD_LEN: usize = 24;

// ---------------------------------------------------------------------------
// A throwaway temp directory
// ---------------------------------------------------------------------------

static COUNTER: AtomicU32 = AtomicU32::new(0);

pub struct TempDir {
    path: PathBuf,
}

impl TempDir {
    /// A path that does NOT exist yet: the inert tests assert the runtime never
    /// creates it.
    pub fn reserved() -> TempDir {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "sensorium-rt-spike-{}-{}-{}",
            std::process::id(),
            n,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.subsec_nanos())
                .unwrap_or(0)
        ));
        let _ = std::fs::remove_dir_all(&path);
        TempDir { path }
    }

    /// The same, but the directory exists. Used as a sandbox root.
    pub fn created() -> TempDir {
        let d = TempDir::reserved();
        std::fs::create_dir_all(&d.path).expect("creating the sandbox");
        d
    }

    pub fn path(&self) -> &Path {
        &self.path
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

    pub fn exists(&self) -> bool {
        self.path.exists()
    }

    /// Every `*.spool` file in the directory, keyed by thread serial.
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

    pub fn proc_header(&self, pid: u32) -> String {
        let path = self.path.join(format!("{pid}.proc.json"));
        std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("reading {}: {e}", path.display()))
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Record {
    pub seq: u64,
    pub ts_ns: u64,
    pub site: u32,
    pub kind: u8,
    pub outcome: u8,
    pub reserved: u16,
}

impl Record {
    pub fn unit_id(&self) -> u8 {
        (self.site >> 24) as u8
    }
    pub fn site_index(&self) -> u32 {
        self.site & 0x00ff_ffff
    }
}

#[derive(Debug)]
pub struct SpoolFile {
    pub path: PathBuf,
    pub version: u8,
    pub serial: u32,
    pub name: String,
    pub records: Vec<Record>,
    /// Header + records; a spool whose length is not header + 24k is malformed.
    pub len: usize,
}

impl SpoolFile {
    pub fn parse(path: &Path) -> SpoolFile {
        let bytes = std::fs::read(path).unwrap_or_else(|e| panic!("reading {}: {e}", path.display()));
        let d = path.display();
        assert!(
            bytes.len() >= 11,
            "{d}: {} bytes is shorter than the fixed header",
            bytes.len()
        );
        assert_eq!(&bytes[0..4], b"SNSR", "{d}: bad magic");
        let version = bytes[4];
        let serial = u32::from_le_bytes(bytes[5..9].try_into().unwrap());
        let name_len = u16::from_le_bytes(bytes[9..11].try_into().unwrap()) as usize;
        let head = 11 + name_len;
        assert!(bytes.len() >= head, "{d}: truncated thread name");
        let name = String::from_utf8(bytes[11..head].to_vec())
            .unwrap_or_else(|e| panic!("{d}: thread name is not UTF-8: {e}"));
        let body = &bytes[head..];
        assert_eq!(
            body.len() % RECORD_LEN,
            0,
            "{d}: {} record bytes is not a multiple of {RECORD_LEN}",
            body.len()
        );
        let records = body
            .chunks_exact(RECORD_LEN)
            .map(|c| Record {
                seq: u64::from_le_bytes(c[0..8].try_into().unwrap()),
                ts_ns: u64::from_le_bytes(c[8..16].try_into().unwrap()),
                site: u32::from_le_bytes(c[16..20].try_into().unwrap()),
                kind: c[20],
                outcome: c[21],
                reserved: u16::from_le_bytes(c[22..24].try_into().unwrap()),
            })
            .collect();
        SpoolFile {
            path: path.to_path_buf(),
            version,
            serial,
            name,
            records,
            len: bytes.len(),
        }
    }

    pub fn header_len(&self) -> usize {
        11 + self.name.len()
    }

    pub fn kinds(&self, kind: u8) -> Vec<Record> {
        self.records.iter().copied().filter(|r| r.kind == kind).collect()
    }

    pub fn has_thread_end(&self) -> bool {
        self.records.iter().any(|r| r.kind == KIND_THREAD_END)
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

/// Run `scenario <name> [args]` with `SENSORIUM_SPOOL` pointing at `dir` (or
/// unset when `dir` is `None`) and `SENSORIUM_TIER` set from `tier`.
pub fn run(name: &str, args: &[&str], dir: Option<&Path>, tier: Option<&str>) -> Run {
    run_inner(name, args, dir, tier, None, false)
}

/// For scenarios that end on a signal (`abort`), where a non-zero status is the
/// point rather than a failure.
pub fn run_allow_failure(name: &str, dir: Option<&Path>) -> Run {
    run_inner(name, &[], dir, None, None, true)
}

/// The same, but with the child's working directory, `TMPDIR` and `HOME` all
/// pointed at a fresh empty tree.
///
/// "Writes no file" is not falsifiable by watching one named directory: a
/// recorder that fell back to a default path would leave that directory
/// untouched and still write a spool. The sandbox is where such a fallback
/// would land, so `assert_untouched` on the returned directory is the real
/// assertion. (Both of this crate's inert tests survived their mutations until
/// this existed.)
pub fn run_sandboxed(
    name: &str,
    args: &[&str],
    dir: Option<&Path>,
    tier: Option<&str>,
) -> (TempDir, Run) {
    let sandbox = TempDir::created();
    let run = run_inner(name, args, dir, tier, Some(sandbox.path()), false);
    (sandbox, run)
}

fn run_inner(
    name: &str,
    args: &[&str],
    dir: Option<&Path>,
    tier: Option<&str>,
    sandbox: Option<&Path>,
    allow_failure: bool,
) -> Run {
    let mut cmd = Command::new(env!("CARGO_BIN_EXE_scenario"));
    if let Some(s) = sandbox {
        cmd.current_dir(s);
        cmd.env("TMPDIR", s);
        cmd.env("HOME", s);
    }
    cmd.arg(name);
    cmd.args(args);
    cmd.env_remove("SENSORIUM_SPOOL");
    cmd.env_remove("SENSORIUM_TIER");
    if let Some(d) = dir {
        cmd.env("SENSORIUM_SPOOL", d);
    }
    if let Some(t) = tier {
        cmd.env("SENSORIUM_TIER", t);
    }
    let output = cmd.output().expect("running the scenario binary");
    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
    let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
    if !allow_failure {
        assert!(
            output.status.success(),
            "scenario {name} failed: {:?}\nstdout: {stdout}\nstderr: {stderr}",
            output.status
        );
    }
    let pid = stdout
        .lines()
        .find_map(|l| l.strip_prefix("pid "))
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or_else(|| panic!("scenario {name} did not print its pid; stdout: {stdout}"));
    Run {
        output,
        pid,
        stdout,
        stderr,
    }
}

/// The common case: a scenario recording at the default tier.
pub fn run_recording(name: &str) -> (TempDir, Run) {
    let dir = TempDir::reserved();
    let run = run(name, &[], Some(dir.path()), None);
    (dir, run)
}
