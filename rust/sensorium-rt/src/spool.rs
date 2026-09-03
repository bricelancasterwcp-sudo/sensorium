//! The on-disk wire format: one `MAP_SHARED` spool file per emitting thread,
//! and the per-process JSON header beside them.
//!
//! Wire format v2 (verbatim from the plan; a converter is written against it,
//! so nothing here may drift):
//!
//! ```text
//! spool file:   <SENSORIUM_SPOOL>/<pid>.<thread_serial>.spool   -- one per emitting thread, MAP_SHARED
//! file header:  b"SNSR" u8 version=2 u8 flags=0 u16 name_len u32 thread_serial u64 records_dropped u64 truncated  name_bytes
//!               (fixed 28 bytes, then name_bytes; records start at 28 + name_len; records_dropped and truncated are
//!                rewritten IN PLACE through the mapping and are final only once THREAD_END is present)
//! record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome  u16 payload_len  [payload_len bytes]
//! kind:         0 = UNWRITTEN (the mapped tail; the reader STOPS at the first kind 0), 1 = CALL, 2 = RETURN,
//!               3 = PANIC, 255 = THREAD_END
//! outcome:      RETURN only: 0 none, 1 ok, 2 err, 3 panic; 0 on every other kind
//! site:         unit_id in bits 31..24, site index in bits 23..0; 0 on PANIC and THREAD_END
//! RETURN payload:  u8 tag (0 = no value, 1 = debug text follows, 2 = unread) u8 truncated(0|1) then UTF-8 text
//! PANIC payload:   u16 loc_len, loc UTF-8 ("<file>:<line>:<col>" as the hook saw it), then the message UTF-8 (rest)
//! ```
//!
//! Everything is little-endian. `ts_ns` is `CLOCK_MONOTONIC` nanoseconds and
//! `seq` is a process-global counter that starts at 0, so a converter can call
//! any missing number a hole.
//!
//! **The kind-last discipline.** Every field of a record is written first, and
//! `kind` last through an `AtomicU8` view of that byte with a `Release` store.
//! A reader that meets `kind == 0` has reached the end of what was written, and
//! everything before it is whole. This is the whole of `rust/HONESTY.md` §4's
//! one-record bound.
//!
//! **The file is one contiguous byte stream.** A record never straddles a
//! boundary because there are no boundaries: when the next record would not fit
//! the current mapping, the file is `ftruncate`d up to the next 64 KiB multiple
//! and mapped again *in full* from offset 0, so the record lands contiguously.
//! Growth costs one `ftruncate` and one `mmap` per 64 KiB, and the old mapping
//! is unmapped only once the new one exists -- which is what lets a thread
//! whose growth FAILED still write `records_dropped` into its header.
//!
//! **No `msync`.** `MAP_SHARED` dirty pages are the page cache, so a reader on
//! this machine sees them the instant they are written, through `read()` as
//! well as through a mapping; that covers every row of the durability table
//! (return from `main`, `exit`, `abort`, SIGKILL). Surviving a machine that
//! loses power is not a claim this recorder makes.

use std::ffi::c_void;
use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::os::unix::io::AsRawFd;
use std::path::Path;
use std::ptr;
use std::sync::atomic::{AtomicU8, Ordering};

use crate::ffi;
use crate::sha256::{hex_prefix, Sha256};

pub(crate) const MAGIC: [u8; 4] = *b"SNSR";
pub(crate) const VERSION: u8 = 2;
pub(crate) const FLAGS: u8 = 0;

/// Fixed part of the file header, before the thread name.
pub(crate) const HEADER_FIXED: usize = 28;
/// Fixed part of a record, before its payload.
pub(crate) const RECORD_FIXED: usize = 24;
/// Byte offsets of the two counters rewritten in place.
const OFF_RECORDS_DROPPED: usize = 12;
const OFF_TRUNCATED: usize = 20;
/// Byte offset of `kind` within a record: the last byte written.
const OFF_KIND: usize = 20;

/// The file grows in whole multiples of this.
const CHUNK: usize = 64 * 1024;

pub(crate) const KIND_CALL: u8 = 1;
pub(crate) const KIND_RETURN: u8 = 2;
#[allow(dead_code)] // written by the panic hook (Task 3); pinned here so the format has one home.
pub(crate) const KIND_PANIC: u8 = 3;
pub(crate) const KIND_THREAD_END: u8 = 255;

pub(crate) const OUTCOME_NONE: u8 = 0;

/// The site word packs the unit id into bits 31..24 and the site index into
/// bits 23..0.
pub(crate) const SITE_INDEX_MASK: u32 = 0x00ff_ffff;
pub(crate) const UNIT_ID_SHIFT: u32 = 24;

/// This runtime's identity, as the proc header carries it.
///
/// Hard-coded rather than `env!("CARGO_PKG_VERSION")`: the driver compiles this
/// crate with a bare `rustc` invocation (D1), where cargo's environment does
/// not exist and `env!` would not compile. A unit test below holds it to the
/// manifest.
pub(crate) const RT_VERSION: &str = "sensorium-rt 0.1.0";

fn round_up_to_chunk(n: usize) -> usize {
    n.div_ceil(CHUNK) * CHUNK
}

/// One thread's spool file and its live mapping.
pub(crate) struct Spool {
    file: File,
    base: *mut u8,
    map_len: usize,
    /// Offset the next record goes at; also the file's final length.
    pos: usize,
    /// Set once a growth failed. Every later record is a counted drop.
    broken: bool,
    records_dropped: u64,
    /// `None` in a production build; `Some` only under the `test-hooks`
    /// feature, where a test needs a disk to be full on demand.
    limit: Option<usize>,
}

impl Spool {
    /// Create `<dir>/<pid>.<serial>.spool`, size it to its first chunk, map it
    /// and write the header.
    pub(crate) fn open(
        dir: &Path,
        pid: u32,
        serial: u32,
        name: &str,
        truncated_so_far: u64,
    ) -> io::Result<Spool> {
        let name = truncate_name(name);
        let header_len = HEADER_FIXED + name.len();
        let path = dir.join(format!("{pid}.{serial}.spool"));
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(true)
            .open(path)?;
        let map_len = round_up_to_chunk(header_len + RECORD_FIXED);
        set_len(&file, map_len)?;
        let base = map(&file, map_len)?;
        let mut spool = Spool {
            file,
            base,
            map_len,
            pos: header_len,
            broken: false,
            records_dropped: 0,
            limit: spool_limit(),
        };
        spool.write_header(serial, name, truncated_so_far);
        Ok(spool)
    }

    fn write_header(&mut self, serial: u32, name: &str, truncated_so_far: u64) {
        let mut head = [0u8; HEADER_FIXED];
        head[0..4].copy_from_slice(&MAGIC);
        head[4] = VERSION;
        head[5] = FLAGS;
        head[6..8].copy_from_slice(&(name.len() as u16).to_le_bytes());
        head[8..12].copy_from_slice(&serial.to_le_bytes());
        head[OFF_RECORDS_DROPPED..OFF_RECORDS_DROPPED + 8].copy_from_slice(&0u64.to_le_bytes());
        head[OFF_TRUNCATED..OFF_TRUNCATED + 8].copy_from_slice(&truncated_so_far.to_le_bytes());
        self.put(0, &head);
        self.put(HEADER_FIXED, name.as_bytes());
    }

    /// Append one record. Returns false when nothing was written, having
    /// counted the drop.
    ///
    /// The sequence number is minted HERE, after the record is known to be
    /// writable, and never by the caller: a refused record must consume no
    /// number, or every witnessed drop would also leave a hole in the
    /// process-global sequence and be counted a second time as a `seq_gap` at
    /// conversion. `records_dropped` and `seq_gaps` are disjoint because of
    /// this line (`rust/HONESTY.md` §4).
    pub(crate) fn record(
        &mut self,
        ts_ns: u64,
        site: u32,
        kind: u8,
        outcome: u8,
        payload: &[u8],
    ) -> bool {
        debug_assert!(kind != 0, "kind 0 is the unwritten tail, never a record");
        // The payload arrives ALREADY BOUNDED: the caller cut it on a char
        // boundary and set whatever flag or counter witnesses the cut (the RETURN
        // writer's `truncated` byte and the header counter; the panic hook's own
        // in Task 3). Clamping here instead would cut silently, mid-char, and --
        // for a PANIC record -- possibly inside its `u16 loc_len` region. A
        // caller that ignores this loses the record and is TOLD it lost it,
        // rather than writing one whose length field has wrapped.
        debug_assert!(
            payload.len() <= u16::MAX as usize,
            "a {}-byte payload does not fit the wire format's u16 length; cap it in the caller",
            payload.len()
        );
        let payload_len = payload.len();
        let end = self.pos + RECORD_FIXED + payload_len;
        if self.broken || payload_len > u16::MAX as usize || (end > self.map_len && !self.grow(end))
        {
            self.count_drop();
            return false;
        }
        // Minted only now, with the record's place in the file secured. The
        // counter is process-global and `Relaxed` is enough: the number's job is
        // to name a hole, and the kind-last `Release` store below is what orders
        // these bytes against a reader.
        let seq = crate::next_seq();
        let mut fixed = [0u8; RECORD_FIXED];
        fixed[0..8].copy_from_slice(&seq.to_le_bytes());
        fixed[8..16].copy_from_slice(&ts_ns.to_le_bytes());
        fixed[16..20].copy_from_slice(&site.to_le_bytes());
        // fixed[OFF_KIND] stays 0 here: it is the last byte written, below.
        fixed[21] = outcome;
        fixed[22..24].copy_from_slice(&(payload_len as u16).to_le_bytes());
        self.put(self.pos, &fixed);
        self.put(self.pos + RECORD_FIXED, payload);
        self.publish_kind(self.pos + OFF_KIND, kind);
        self.pos = end;
        true
    }

    /// `ftruncate` to the next chunk boundary and map the whole file again. The
    /// old mapping is kept until the new one exists, so a failure leaves the
    /// header writable and the thread able to say what it lost.
    fn grow(&mut self, need: usize) -> bool {
        let new_len = round_up_to_chunk(need);
        if let Some(limit) = self.limit {
            if new_len > limit {
                self.broken = true;
                return false;
            }
        }
        if set_len(&self.file, new_len).is_err() {
            self.broken = true;
            return false;
        }
        let Ok(base) = map(&self.file, new_len) else {
            self.broken = true;
            return false;
        };
        unmap(self.base, self.map_len);
        self.base = base;
        self.map_len = new_len;
        true
    }

    fn count_drop(&mut self) {
        self.records_dropped += 1;
        let n = self.records_dropped;
        self.put(OFF_RECORDS_DROPPED, &n.to_le_bytes());
    }

    /// Rewrite the header's truncated-capture counter in place.
    pub(crate) fn set_truncated(&mut self, n: u64) {
        self.put(OFF_TRUNCATED, &n.to_le_bytes());
    }

    fn put(&mut self, at: usize, bytes: &[u8]) {
        debug_assert!(at + bytes.len() <= self.map_len);
        if bytes.is_empty() {
            return;
        }
        // SAFETY: `base` is a live MAP_SHARED mapping of `map_len` writable
        // bytes, `at + bytes.len() <= map_len`, and this thread is the mapping's
        // only writer (one spool per thread, held in that thread's thread-local).
        unsafe {
            ptr::copy_nonoverlapping(bytes.as_ptr(), self.base.add(at), bytes.len());
        }
    }

    /// The one byte that makes a record real, stored with `Release` so every
    /// byte written above is visible to whoever sees a non-zero kind.
    fn publish_kind(&mut self, at: usize, kind: u8) {
        // SAFETY: `base.add(at)` is one writable byte inside the live mapping,
        // aligned for `u8` by definition, and no other thread writes this spool.
        let cell = unsafe { AtomicU8::from_ptr(self.base.add(at).cast()) };
        cell.store(kind, Ordering::Release);
    }
}

impl Drop for Spool {
    /// `THREAD_END`, then the file is cut to exactly what was written -- so a
    /// spool with a kind-0 tail is precisely a spool whose thread never ended.
    fn drop(&mut self) {
        self.record(ffi::now_ns(), 0, KIND_THREAD_END, OUTCOME_NONE, &[]);
        let written = self.pos;
        unmap(self.base, self.map_len);
        self.map_len = 0;
        let _ = set_len(&self.file, written);
    }
}

fn set_len(file: &File, len: usize) -> io::Result<()> {
    // SAFETY: `fd` is this `File`'s live descriptor, open for writing.
    let rc = unsafe { ffi::ftruncate(file.as_raw_fd(), len as ffi::off_t) };
    if rc == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

fn map(file: &File, len: usize) -> io::Result<*mut u8> {
    // SAFETY: `fd` is live and open for reading and writing, `len` is non-zero
    // and no larger than the file (just `ftruncate`d to it), and the kernel
    // chooses the address.
    let p = unsafe {
        ffi::mmap(
            ptr::null_mut(),
            len,
            ffi::PROT_READ | ffi::PROT_WRITE,
            ffi::MAP_SHARED,
            file.as_raw_fd(),
            0,
        )
    };
    if p == ffi::MAP_FAILED {
        return Err(io::Error::last_os_error());
    }
    Ok(p.cast::<u8>())
}

fn unmap(base: *mut u8, len: usize) {
    if len == 0 {
        return;
    }
    // SAFETY: `base`/`len` are exactly what the matching `mmap` returned and
    // asked for, and nothing holds a reference into the mapping past this point.
    unsafe {
        ffi::munmap(base.cast::<c_void>(), len);
    }
}

/// A synthetic disk-full, for the durability test's last row. Absent from a
/// production build: the driver's bare `rustc` line passes no feature cfg.
fn spool_limit() -> Option<usize> {
    #[cfg(feature = "test-hooks")]
    {
        std::env::var("SENSORIUM_TEST_SPOOL_LIMIT")
            .ok()
            .and_then(|v| v.parse().ok())
    }
    #[cfg(not(feature = "test-hooks"))]
    {
        None
    }
}

/// The longest prefix of `text` that is at most `max` bytes and ends on a char
/// boundary, and whether anything was cut.
///
/// Every payload the runtime writes goes through this: `record` takes bytes that
/// are already bounded (it will refuse an over-long one rather than clamp it
/// silently), so a caller with text to write cuts it here and reports the cut.
/// The RETURN writer uses it for its 200-byte capture; the panic hook (Task 3)
/// uses it for a message that an `assert_eq!` over two large collections can
/// easily push past 64 KiB.
pub(crate) fn cap_utf8(text: &str, max: usize) -> (&str, bool) {
    if text.len() <= max {
        return (text, false);
    }
    let mut end = max;
    while end > 0 && !text.is_char_boundary(end) {
        end -= 1;
    }
    (&text[..end], true)
}

/// Thread names are bounded by the header's `u16` length.
fn truncate_name(name: &str) -> &str {
    cap_utf8(name, u16::MAX as usize).0
}

// ---------------------------------------------------------------------------
// The per-process header
// ---------------------------------------------------------------------------

/// Write `<dir>/<pid>.proc.json`. Called at the process's first event and again
/// at every unit registration and at a refusal (the file is small; rewriting it
/// keeps one source of truth and needs no incremental scheme).
pub(crate) fn write_proc_header(
    dir: &Path,
    pid: u32,
    start_ns: u64,
    start_realtime_ns: u64,
    units: &[&'static str],
    refused: Option<&'static str>,
) -> io::Result<()> {
    let env = sorted_env();
    let mut json = String::with_capacity(4096);
    json.push_str("{\"pid\":");
    json.push_str(&pid.to_string());
    json.push_str(",\"ppid\":");
    json.push_str(&ffi::parent_pid().to_string());
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
    json.push_str(",\"start_realtime_ns\":");
    json.push_str(&start_realtime_ns.to_string());
    json.push_str(",\"env\":{");
    for (i, (k, v)) in env.iter().enumerate() {
        if i > 0 {
            json.push(',');
        }
        push_json_str(&mut json, k);
        json.push(':');
        push_json_str(&mut json, v);
    }
    json.push_str("},\"env_hash\":");
    push_json_str(&mut json, &env_hash(&env));
    json.push_str(",\"units\":{");
    for (id, metadata) in units.iter().enumerate() {
        if id > 0 {
            json.push(',');
        }
        push_json_str(&mut json, &id.to_string());
        json.push(':');
        push_json_str(&mut json, metadata);
    }
    json.push_str("},\"refused\":");
    match refused {
        None => json.push_str("null"),
        Some(metadata) => {
            json.push_str("{\"at\":");
            push_json_str(&mut json, metadata);
            json.push('}');
        }
    }
    json.push_str(",\"rt_version\":");
    push_json_str(&mut json, RT_VERSION);
    json.push('}');

    // Written to a per-process temporary and RENAMED into place. This file is
    // rewritten at every unit registration -- 77 times on a bloomery invocation --
    // and rows (c) and (d) of the durability table kill the process at an
    // arbitrary instant. `File::create` truncates first, so a kill inside that
    // window would leave invalid JSON and cost the whole run, against §4's
    // promise that a crash costs at most one record per thread. `rename` within
    // one directory is atomic, so a reader sees the old header or the new one.
    let tmp = dir.join(format!("{pid}.proc.json.tmp"));
    let path = dir.join(format!("{pid}.proc.json"));
    {
        let mut f = File::create(&tmp)?;
        f.write_all(json.as_bytes())?;
        f.flush()?;
    }
    std::fs::rename(&tmp, &path)
}

fn sorted_env() -> Vec<(String, String)> {
    let mut env: Vec<(String, String)> = std::env::vars_os()
        .map(|(k, v)| {
            (
                k.to_string_lossy().into_owned(),
                v.to_string_lossy().into_owned(),
            )
        })
        .collect();
    env.sort();
    env
}

/// `sha256` over `"\n".join(f"{k}={v}")` for the sorted environment, first 16
/// hex characters.
///
/// **Deliberately not the Python recorder's formula.** `src/sensorium/record/boot.py`
/// hashes `json.dumps(env, sort_keys=True)`; this hashes the plan's
/// `"{k}={v}"` join. Ruled 2026-09-02: `env_hash` is a per-recorder identity,
/// compared only between traces from the same recorder, and no command compares
/// one across languages. Each is stable within its own language, which is the
/// whole of what the key is for.
fn env_hash(env: &[(String, String)]) -> String {
    let mut h = Sha256::new();
    for (i, (k, v)) in env.iter().enumerate() {
        if i > 0 {
            h.update(b"\n");
        }
        h.update(k.as_bytes());
        h.update(b"=");
        h.update(v.as_bytes());
    }
    hex_prefix(&h.finish(), 16)
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
                let cp = c as u32;
                out.push_str("\\u00");
                out.push(char::from_digit(cp >> 4, 16).unwrap());
                out.push(char::from_digit(cp & 0xf, 16).unwrap());
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rt_version_tracks_the_manifest() {
        assert_eq!(
            RT_VERSION,
            format!("sensorium-rt {}", env!("CARGO_PKG_VERSION")),
            "the hard-coded version string drifted from Cargo.toml"
        );
    }

    #[test]
    fn env_hash_is_sha256_of_key_equals_value_newline_joined() {
        // sha256(b"A=1\nB=2").hexdigest()[:16]
        let env = vec![
            ("A".to_owned(), "1".to_owned()),
            ("B".to_owned(), "2".to_owned()),
        ];
        assert_eq!(env_hash(&env), "c1f0203c784f4397");
    }

    #[test]
    fn json_strings_escape_what_json_requires() {
        let mut out = String::new();
        push_json_str(&mut out, "a\"b\\c\nd\te\u{1}f\u{e9}");
        assert_eq!(out, "\"a\\\"b\\\\c\\nd\\te\\u0001f\u{e9}\"");
    }

    #[test]
    fn the_site_word_fields_are_the_widths_the_wire_format_names() {
        // Literals, not a restatement of the constants: the wire format says
        // "unit_id in bits 31..24, site index in bits 23..0", and a converter is
        // written to those numbers.
        assert_eq!(SITE_INDEX_MASK, 0x00ff_ffff);
        assert_eq!(UNIT_ID_SHIFT, 24);
        assert_eq!(
            SITE_INDEX_MASK.count_ones(),
            24,
            "the index field is 24 bits wide"
        );
        assert_eq!(
            SITE_INDEX_MASK >> UNIT_ID_SHIFT,
            0,
            "the index field and the unit id field do not overlap"
        );
    }

    /// A scratch directory on whatever disk the suite was pointed at.
    fn scratch_dir(what: &str) -> std::path::PathBuf {
        let root = match std::env::var_os("CARGO_TARGET_DIR") {
            Some(t) if !t.is_empty() => std::path::PathBuf::from(t),
            _ => std::env::temp_dir(),
        };
        let dir = root
            .join("rt-unit")
            .join(format!("{what}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).expect("scratch dir");
        dir
    }

    /// `record` states its contract as a `debug_assert`: the payload arrives
    /// already bounded, because clamping it here would cut silently and possibly
    /// mid-char -- and, for a PANIC record, inside its own `u16 loc_len` field.
    /// This is the falsifier Task 3's panic writer inherits.
    #[test]
    #[should_panic(expected = "does not fit the wire format's u16 length")]
    fn a_payload_too_long_for_the_length_field_trips_the_contract() {
        // Constant per profile, and deliberately asserted: this test is only
        // meaningful where `debug_assert!` is live, and a release run should say
        // so rather than pass for the wrong reason.
        #[allow(clippy::assertions_on_constants)]
        {
            assert!(
                cfg!(debug_assertions),
                "this test pins a debug_assert and needs a debug build"
            );
        }
        let dir = scratch_dir("oversize-payload");
        let mut spool = Spool::open(&dir, std::process::id(), 1, "t", 0).expect("open");
        spool.record(
            1,
            0,
            KIND_CALL,
            OUTCOME_NONE,
            &vec![b'x'; u16::MAX as usize + 1],
        );
    }

    /// The same length, one byte shorter: the largest payload the format can
    /// describe is written, not refused.
    #[test]
    fn the_largest_payload_the_length_field_can_describe_is_written() {
        let dir = scratch_dir("largest-payload");
        let mut spool = Spool::open(&dir, std::process::id(), 2, "t", 0).expect("open");
        let big = vec![b'x'; u16::MAX as usize];
        assert!(spool.record(1, 0, KIND_RETURN, OUTCOME_NONE, &big));
        assert_eq!(spool.records_dropped, 0);
        assert_eq!(
            spool.pos,
            HEADER_FIXED + 1 + RECORD_FIXED + u16::MAX as usize
        );
        drop(spool);
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// The seq of the record that starts at `at`, read back out of the live
    /// mapping.
    fn seq_at(spool: &Spool, at: usize) -> u64 {
        // SAFETY: `at + 8` is inside the live mapping (the caller passes a
        // position `record` has already written a whole record at), and nothing
        // is writing this spool while the test reads it.
        let bytes = unsafe { std::slice::from_raw_parts(spool.base.add(at), 8) };
        u64::from_le_bytes(bytes.try_into().expect("eight bytes"))
    }

    /// A record the spool REFUSED consumes no sequence number.
    ///
    /// This is what makes `records_dropped` and `seq_gaps` disjoint: a witnessed
    /// drop is counted once, by the writer, and leaves no hole for the converter
    /// to count a second time (`rust/HONESTY.md` §4). Two spools in one process,
    /// because the counter is process-global: a record written on one, a record
    /// refused on the other, a record written on the first again -- and the two
    /// written seqs are consecutive.
    #[test]
    fn a_refused_record_consumes_no_sequence_number() {
        let dir = scratch_dir("refused-no-hole");
        let pid = std::process::id();
        let mut ok = Spool::open(&dir, pid, 5, "ok", 0).expect("open");
        let mut full = Spool::open(&dir, pid, 6, "full", 0).expect("open");
        // `spool_limit()`'s own field, set here rather than through the
        // environment so this test needs neither the `test-hooks` feature nor a
        // process-wide `set_var`: `full` may not grow past what it already has.
        full.limit = Some(full.map_len);

        let first_at = ok.pos;
        assert!(ok.record(1, 0, KIND_CALL, OUTCOME_NONE, &[]));

        let too_big = vec![b'x'; CHUNK - RECORD_FIXED];
        assert!(
            !full.record(2, 0, KIND_CALL, OUTCOME_NONE, &too_big),
            "the record does not fit and the spool may not grow"
        );
        assert_eq!(full.records_dropped, 1, "and the writer counted it");

        let second_at = ok.pos;
        assert!(ok.record(3, 0, KIND_RETURN, OUTCOME_NONE, &[]));

        assert_eq!(
            seq_at(&ok, second_at),
            seq_at(&ok, first_at) + 1,
            "the refused record left a hole in the sequence"
        );
        drop(ok);
        drop(full);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn cap_utf8_cuts_on_a_char_boundary_and_says_it_cut() {
        assert_eq!(cap_utf8("abc", 10), ("abc", false));
        assert_eq!(cap_utf8("abc", 3), ("abc", false));
        assert_eq!(cap_utf8("abcdef", 3), ("abc", true));
        // 'é' is two bytes: a cap that lands inside one steps back.
        assert_eq!(cap_utf8("ééé", 5), ("éé", true));
        assert_eq!(cap_utf8("ééé", 4), ("éé", true));
        assert_eq!(cap_utf8("ééé", 1), ("", true));
        assert_eq!(cap_utf8("", 0), ("", false));
        // A four-byte char cut at every offset inside it.
        for max in 1..4 {
            let (cut, did) = cap_utf8("\u{1f600}x", max);
            assert_eq!(cut, "", "max={max}");
            assert!(did);
        }
    }

    #[test]
    fn chunks_round_up_and_never_to_zero() {
        assert_eq!(round_up_to_chunk(1), CHUNK);
        assert_eq!(round_up_to_chunk(CHUNK), CHUNK);
        assert_eq!(round_up_to_chunk(CHUNK + 1), 2 * CHUNK);
    }

    #[test]
    fn a_long_thread_name_is_cut_on_a_char_boundary() {
        let name = "é".repeat(40_000);
        let cut = truncate_name(&name);
        assert!(cut.len() <= u16::MAX as usize);
        assert!(name.starts_with(cut));
        assert_eq!(
            cut.len() % 2,
            0,
            "'é' is two bytes; a cut mid-char is not UTF-8"
        );
    }
}
