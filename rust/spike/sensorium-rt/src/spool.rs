//! THROWAWAY SPIKE CODE. The on-disk wire format and the per-thread spool file.
//!
//! Wire format (verbatim from the plan's Task 1 brief; a Python converter is
//! written against it, so nothing here may drift):
//!
//! ```text
//! file header:  b"SNSR" u8 version=1  u32 thread_serial  u16 name_len  name_bytes
//! record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome  u16 reserved=0
//! kind:         1 = CALL, 2 = RETURN, 255 = THREAD_END
//! outcome:      0 = none, 3 = panic   (1 = ok and 2 = err are reserved for rung 2)
//! site:         unit_id in bits 31..24, site index in bits 23..0
//! proc header:  {"pid":int,"ppid":int,"exe":str,"argv":[str],"cwd":str,
//!                "start_ns":int,"units":{"<unit_id>":"<metadata>"}}
//! ```
//!
//! Everything is little-endian. `ts_ns` is `CLOCK_MONOTONIC` nanoseconds.
//!
//! KNOWN LOSS, deliberately kept for the spike (spec §4 replaces it at rung 2
//! with a `MAP_SHARED` mapping): records go through a per-thread `BufWriter`
//! that is flushed only by the thread-local's destructor. A thread whose
//! destructor never runs loses its buffered records.
//!
//! THE LOSS MODEL, as measured (`tests/thread_end.rs` pins all three rows):
//!
//! | how the process ends | calling thread | other live threads |
//! |---|---|---|
//! | return from `main`     | flushed, `THREAD_END` | header-only |
//! | `std::process::exit()` | flushed, `THREAD_END` | header-only |
//! | `abort()` / a signal   | header-only           | header-only |
//!
//! `process::exit` is NOT a total loss: glibc's `exit()` calls
//! `__call_tls_dtors()`, so the calling thread's spool is flushed and closed
//! exactly as if `main` had returned, and only the OTHER live threads lose
//! their tails. `abort()` and fatal signals run no destructor at all, so every
//! thread including the aborting one is left at its header.
//!
//! The FILE HEADER is flushed at open precisely so a spool that loses its tail
//! is still identifiable -- it names the thread and carries its serial, which
//! is what `live_threads` in the converter needs. Every row above therefore
//! leaves a well-formed, parseable spool; what varies is how much of it there
//! is and whether it ends with `THREAD_END`.

use std::fs::File;
use std::io::{self, BufWriter, Write};
use std::path::Path;

pub(crate) const MAGIC: [u8; 4] = *b"SNSR";
pub(crate) const VERSION: u8 = 1;

pub(crate) const KIND_CALL: u8 = 1;
pub(crate) const KIND_RETURN: u8 = 2;
pub(crate) const KIND_THREAD_END: u8 = 255;

pub(crate) const OUTCOME_NONE: u8 = 0;
pub(crate) const OUTCOME_PANIC: u8 = 3;

/// One record is exactly 24 bytes. The converter indexes on this.
pub(crate) const RECORD_LEN: usize = 24;

/// The site word packs the unit id into bits 31..24 and the site index into
/// bits 23..0.
pub(crate) const SITE_INDEX_MASK: u32 = 0x00ff_ffff;
pub(crate) const UNIT_ID_SHIFT: u32 = 24;

/// `CLOCK_MONOTONIC` nanoseconds.
pub(crate) fn now_ns() -> u64 {
    let mut ts = libc::timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };
    // SAFETY: `ts` is a valid, fully initialised `timespec` we own.
    unsafe {
        libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut ts);
    }
    (ts.tv_sec as u64)
        .wrapping_mul(1_000_000_000)
        .wrapping_add(ts.tv_nsec as u64)
}

/// One thread's spool file.
pub(crate) struct Spool {
    writer: BufWriter<File>,
    broken: bool,
}

impl Spool {
    /// Create `<dir>/<pid>.<serial>.spool` and write (and flush) its header.
    pub(crate) fn open(dir: &Path, pid: u32, serial: u32, name: &str) -> io::Result<Spool> {
        let path = dir.join(format!("{pid}.{serial}.spool"));
        let mut writer = BufWriter::new(File::create(path)?);
        writer.write_all(&MAGIC)?;
        writer.write_all(&[VERSION])?;
        writer.write_all(&serial.to_le_bytes())?;
        let name = truncate_name(name);
        writer.write_all(&(name.len() as u16).to_le_bytes())?;
        writer.write_all(name.as_bytes())?;
        // Flushed here, not at drop: a thread that never exits still leaves an
        // identifiable spool. See the module doc's KNOWN LOSS note.
        writer.flush()?;
        Ok(Spool {
            writer,
            broken: false,
        })
    }

    /// Append one 24-byte record. Returns false once the spool is broken.
    pub(crate) fn record(
        &mut self,
        seq: u64,
        ts_ns: u64,
        site: u32,
        kind: u8,
        outcome: u8,
    ) -> io::Result<()> {
        if self.broken {
            return Err(io::Error::other("spool already broken"));
        }
        let mut buf = [0u8; RECORD_LEN];
        buf[0..8].copy_from_slice(&seq.to_le_bytes());
        buf[8..16].copy_from_slice(&ts_ns.to_le_bytes());
        buf[16..20].copy_from_slice(&site.to_le_bytes());
        buf[20] = kind;
        buf[21] = outcome;
        // buf[22..24] stays zero: the reserved u16.
        let r = self.writer.write_all(&buf);
        if r.is_err() {
            self.broken = true;
        }
        r
    }
}

impl Drop for Spool {
    fn drop(&mut self) {
        if !self.broken {
            let _ = self.record(crate::next_seq(), now_ns(), 0, KIND_THREAD_END, OUTCOME_NONE);
        }
        let _ = self.writer.flush();
    }
}

/// Thread names are bounded by the header's `u16` length. Truncation keeps a
/// char boundary so the bytes stay valid UTF-8 for the converter.
fn truncate_name(name: &str) -> &str {
    const MAX: usize = u16::MAX as usize;
    if name.len() <= MAX {
        return name;
    }
    let mut end = MAX;
    while end > 0 && !name.is_char_boundary(end) {
        end -= 1;
    }
    &name[..end]
}

/// Write `<dir>/<pid>.proc.json`. Called once at the process's first event and
/// again each time a unit registers (the file is tiny; rewriting is cheaper
/// than any incremental scheme and keeps a single source of truth).
pub(crate) fn write_proc_header(
    dir: &Path,
    pid: u32,
    start_ns: u64,
    units: &[&'static str],
) -> io::Result<()> {
    let mut json = String::with_capacity(256);
    json.push_str("{\"pid\":");
    json.push_str(&pid.to_string());
    json.push_str(",\"ppid\":");
    // SAFETY: `getppid` takes no arguments and cannot fail.
    json.push_str(&unsafe { libc::getppid() }.to_string());
    json.push_str(",\"exe\":");
    push_json_str(
        &mut json,
        &std::env::current_exe()
            .map(|p| p.to_string_lossy().into_owned())
            .unwrap_or_default(),
    );
    json.push_str(",\"argv\":[");
    for (i, arg) in std::env::args_os().enumerate() {
        if i > 0 {
            json.push(',');
        }
        push_json_str(&mut json, &arg.to_string_lossy());
    }
    json.push_str("],\"cwd\":");
    push_json_str(
        &mut json,
        &std::env::current_dir()
            .map(|p| p.to_string_lossy().into_owned())
            .unwrap_or_default(),
    );
    json.push_str(",\"start_ns\":");
    json.push_str(&start_ns.to_string());
    json.push_str(",\"units\":{");
    for (id, metadata) in units.iter().enumerate() {
        if id > 0 {
            json.push(',');
        }
        push_json_str(&mut json, &id.to_string());
        json.push(':');
        push_json_str(&mut json, metadata);
    }
    json.push_str("}}");

    let path = dir.join(format!("{pid}.proc.json"));
    let mut f = File::create(path)?;
    f.write_all(json.as_bytes())?;
    f.flush()
}

fn push_json_str(out: &mut String, s: &str) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }
    out.push('"');
}
