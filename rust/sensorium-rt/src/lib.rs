//! `sensorium-rt` -- the runtime linked into every instrumented compilation
//! unit of the sensorium Rust recorder. v1, the `call` tier.
//!
//! At this tier the runtime records, per instrumented fn item, a CALL when the
//! entry guard is created and a RETURN when it drops, carrying the frame's
//! outcome and a capped `Debug` rendering of the value that crossed the
//! boundary. Not `?` sites (rung 3), not locals or LINE (rung 4), not program
//! output. `rust/HONESTY.md` is the list of what that does and does not mean;
//! §1, §2, §4, §7 and §8 are this crate's promises.
//!
//! The transformer injects, as the first statement of every eligible fn body:
//!
//! ```ignore
//! let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);
//! ```
//!
//! wraps every exit operand of a value-returning fn (the tail expression, and
//! each `return <e>` at closure depth 0) as:
//!
//! ```ignore
//! ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, <site>, |__r| {
//!     use ::sensorium_rt::probe::*;
//!     ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
//! }, <e>)
//! ```
//!
//! and appends to each instrumented crate root:
//!
//! ```ignore
//! #[doc(hidden)]
//! pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit =
//!     ::sensorium_rt::Unit::new("<-C metadata hash>");
//! ```
//!
//! Environment, read once per process on the first instrumented event -- an
//! `enter`, or a `spawn_child` that beats every `enter` to it:
//!
//! * `SENSORIUM_SPOOL` -- the spool directory. Unset or empty: the runtime is
//!   inert. Nothing is created, nothing is written, nothing is allocated.
//! * `SENSORIUM_TIER` -- `off` or `call`. Absent or empty means `call`. Any
//!   other value is refused with one stderr line and the runtime stays inert:
//!   recording a tier the caller did not ask for would put dishonest data in
//!   the trace.
//!
//! **The panic hook** is installed by the first `enter` that records, not by
//! `init`: it chains to whatever hook was in place, so a panicking program
//! prints exactly what it would have printed with no recorder linked in
//! (`src/panic.rs`).
//!
//! **The inert path.** `enter`'s first arm is one `Acquire` load, one compare
//! and the guard value -- no call, no branch on anything else, no allocation.
//! That shape is the invariant endpoint E1 measures, and it is the reason
//! `STATE_OFF` is tested before `STATE_CALL` below.
//!
//! **Zero dependencies** (plan decision D1): see `ffi.rs`. This crate must
//! compile with a bare
//! `rustc --crate-type rlib --edition 2021 -C opt-level=3 src/lib.rs`, so it has
//! no build script, needs no cargo feature, and reads nothing from cargo's
//! environment.

#[cfg(not(target_os = "linux"))]
compile_error!(
    "sensorium-rt v1 is Linux-only: thread serials come from gettid()/getpid() and the spool is a \
     MAP_SHARED mapping grown with ftruncate (spec §4). Portability is designed, not patched in."
);

mod ffi;
mod panic;
pub mod probe;
mod sha256;
mod spool;
mod tasks;
mod thread;

pub use tasks::spawn_child;

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU16, AtomicU64, AtomicU8, Ordering};
use std::sync::{Mutex, Once, OnceLock};

use probe::{Capture, Outcome};
use spool::{KIND_CALL, KIND_RETURN, OUTCOME_NONE, SITE_INDEX_MASK, UNIT_ID_SHIFT};

// ---------------------------------------------------------------------------
// Process state
// ---------------------------------------------------------------------------

const STATE_UNINIT: u8 = 0;
/// Configured off, or no spool directory. Inert.
const STATE_OFF: u8 = 1;
/// Recording CALL/RETURN.
const STATE_CALL: u8 = 2;
/// More units than the wire format's 8-bit unit id can carry. Inert.
const STATE_REFUSED: u8 = 3;
/// An I/O error took the recorder down. Inert.
const STATE_FAILED: u8 = 4;

/// The single word the hot path reads. Stored with `Release` and loaded with
/// `Acquire`, so a thread that sees `STATE_CALL` also sees `SPOOL_DIR`.
static STATE: AtomicU8 = AtomicU8::new(STATE_UNINIT);
static INIT: Once = Once::new();
static SPOOL_DIR: OnceLock<PathBuf> = OnceLock::new();
static START_NS: AtomicU64 = AtomicU64::new(0);
static START_REALTIME_NS: AtomicU64 = AtomicU64::new(0);

/// One `fetch_add` per record, from 0. `Relaxed` is sufficient: a single
/// atomic's modification order is consistent with happens-before, so two events
/// ordered by any synchronisation are ordered by their sequence numbers too.
/// A number that appears in no spool is a record lost mid-write, which is what
/// the converter reports as `seq_gaps`.
static SEQ: AtomicU64 = AtomicU64::new(0);

/// The wire format packs the unit id into 8 bits, so at most this many units
/// can be distinguished. Ids run `0..=254`: id 255 is never assigned, so the
/// sentence "the 256th distinct unit makes the runtime refuse" is true read
/// literally, and a converter author reading it is not surprised.
const MAX_UNITS: usize = 255;

/// Registered units by id, and the unit that was refused, under one lock. They
/// move together because the proc header carries both.
struct Registry {
    units: Vec<&'static str>,
    refused: Option<&'static str>,
}

static REGISTRY: Mutex<Registry> = Mutex::new(Registry {
    units: Vec::new(),
    refused: None,
});

static DIR_READY: Once = Once::new();
static REFUSAL_WARNED: Once = Once::new();
static FAILURE_WARNED: Once = Once::new();
static TIER_WARNED: Once = Once::new();

pub(crate) fn next_seq() -> u64 {
    SEQ.fetch_add(1, Ordering::Relaxed)
}

#[cold]
fn init() {
    INIT.call_once(|| {
        // Both clocks at the same instant, so a reader can place the monotonic
        // timeline of every record on a wall clock.
        START_NS.store(ffi::now_ns(), Ordering::Relaxed);
        START_REALTIME_NS.store(ffi::now_realtime_ns(), Ordering::Relaxed);
        let dir = match std::env::var_os("SENSORIUM_SPOOL") {
            Some(d) if !d.is_empty() => PathBuf::from(d),
            _ => {
                STATE.store(STATE_OFF, Ordering::Release);
                return;
            }
        };
        let tier = match std::env::var_os("SENSORIUM_TIER") {
            None => STATE_CALL,
            Some(v) => match v.to_str() {
                None => bad_tier(&v.to_string_lossy()),
                Some("") | Some("call") => STATE_CALL,
                Some("off") => STATE_OFF,
                Some(other) => bad_tier(other),
            },
        };
        if tier == STATE_CALL {
            let _ = SPOOL_DIR.set(dir);
        }
        STATE.store(tier, Ordering::Release);
    });
}

#[cold]
fn bad_tier(value: &str) -> u8 {
    TIER_WARNED.call_once(|| {
        eprintln!(
            "sensorium-rt: SENSORIUM_TIER={value:?} is not one of `off`, `call`; \
             recording nothing rather than a tier that was not asked for"
        );
    });
    STATE_OFF
}

/// One stderr line, then the whole process goes inert. An instrument that
/// cannot write must say so; it must not keep half a trace and stay quiet.
#[cold]
pub(crate) fn fail_process(what: &str, e: &std::io::Error) {
    FAILURE_WARNED.call_once(|| {
        eprintln!("sensorium-rt: {what} failed: {e}; this process records nothing further");
    });
    STATE.store(STATE_FAILED, Ordering::Release);
}

/// The spool directory, created (once) on the process's first event. `None`
/// once the recorder is inert for any reason.
fn ensure_dir() -> Option<&'static Path> {
    let dir = SPOOL_DIR.get()?;
    DIR_READY.call_once(|| {
        if let Err(e) = std::fs::create_dir_all(dir) {
            fail_process("creating the spool directory", &e);
            return;
        }
        // The proc header exists from the process's first event, before any unit
        // has registered; each registration rewrites it.
        let registry = REGISTRY.lock().unwrap_or_else(|e| e.into_inner());
        write_proc_header(dir, &registry);
    });
    if STATE.load(Ordering::Acquire) != STATE_CALL {
        return None;
    }
    Some(dir.as_path())
}

fn write_proc_header(dir: &Path, registry: &Registry) {
    if let Err(e) = spool::write_proc_header(
        dir,
        std::process::id(),
        START_NS.load(Ordering::Relaxed),
        START_REALTIME_NS.load(Ordering::Relaxed),
        &registry.units,
        registry.refused,
    ) {
        fail_process("writing the process header", &e);
    }
}

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

const UNIT_UNREGISTERED: u16 = u16::MAX;

/// One instrumented compilation unit. Constructed in a `static` at each
/// instrumented crate root; it takes its process-unique id lazily, on its first
/// `enter`, so a unit that never runs costs nothing but its static.
pub struct Unit {
    metadata: &'static str,
    id: AtomicU16,
}

impl Unit {
    /// `metadata` is the unit's `-C metadata` hash: stable per crate per build,
    /// and what the converter joins a manifest to.
    #[must_use]
    pub const fn new(metadata: &'static str) -> Unit {
        Unit {
            metadata,
            id: AtomicU16::new(UNIT_UNREGISTERED),
        }
    }

    /// The metadata string this unit was declared with.
    #[must_use]
    pub fn metadata(&self) -> &'static str {
        self.metadata
    }

    /// This unit's id if it has already registered. Never registers: `ret` uses
    /// it, and a unit that has not registered has no open frame to attach to.
    fn current_id(&self) -> Option<u8> {
        match self.id.load(Ordering::Acquire) {
            UNIT_UNREGISTERED => None,
            id => Some(id as u8),
        }
    }
}

fn unit_id(unit: &'static Unit, dir: &Path) -> Option<u8> {
    match unit.current_id() {
        Some(id) => Some(id),
        None => register_unit(unit, dir),
    }
}

#[cold]
fn register_unit(unit: &'static Unit, dir: &Path) -> Option<u8> {
    let mut registry = REGISTRY.lock().unwrap_or_else(|e| e.into_inner());
    // Re-check under the lock: another thread may have registered it.
    if let Some(id) = unit.current_id() {
        return Some(id);
    }
    if registry.units.len() >= MAX_UNITS {
        refuse(unit, dir, &mut registry);
        return None;
    }
    let id = registry.units.len() as u16;
    registry.units.push(unit.metadata);
    unit.id.store(id, Ordering::Release);
    write_proc_header(dir, &registry);
    Some(id as u8)
}

/// The ceiling. Recording stops rather than aliasing two units onto one id, and
/// the refusal goes into the trace as well as onto stderr -- a trace that is
/// short because of this says so (`rust/HONESTY.md` §8, item 13).
#[cold]
fn refuse(unit: &'static Unit, dir: &Path, registry: &mut Registry) {
    STATE.store(STATE_REFUSED, Ordering::Release);
    registry.refused = Some(unit.metadata);
    write_proc_header(dir, registry);
    let metadata = unit.metadata;
    REFUSAL_WARNED.call_once(|| {
        eprintln!(
            "sensorium-rt: refusing to record: this process reached {MAX_UNITS} instrumented \
             units and {metadata:?} is the {}th; the wire format packs the unit id into 8 bits \
             of the site word, so recording further units would alias them. Every later enter() \
             in this process is inert.",
            MAX_UNITS + 1
        );
    });
}

// ---------------------------------------------------------------------------
// The entry guard
// ---------------------------------------------------------------------------

/// The entry guard. First-declared is last-dropped, so every `let`-bound local
/// of the instrumented body -- `MutexGuard`s included -- drops before RETURN.
///
/// It carries its frame's depth as well as its site, because a local whose
/// `Drop` calls instrumented code opens a frame BETWEEN this frame's exit
/// operand and this guard's drop -- possibly at the very same site, one level
/// down. `depth` is what keeps the two frames' values apart. Depth 0 is the
/// inert guard, so `Drop` is still a single compare.
///
/// It also carries whether the thread was ALREADY unwinding when the frame was
/// entered, because `std::thread::panicking()` at the exit cannot tell a frame
/// a panic tore through from one a `Drop` opened during someone else's unwind.
#[must_use]
pub struct Guard {
    site: u32,
    depth: u32,
    /// `std::thread::panicking()` as it read at `enter`. See `emit_return`.
    entered_unwinding: bool,
}

impl Guard {
    #[inline]
    fn inert() -> Guard {
        Guard {
            site: 0,
            depth: 0,
            entered_unwinding: false,
        }
    }
}

impl Drop for Guard {
    #[inline]
    fn drop(&mut self) {
        if self.depth == 0 {
            return;
        }
        emit_return(self.site, self.depth, self.entered_unwinding);
    }
}

/// Record a CALL and return the guard whose drop records the RETURN.
///
/// Inert -- no record, no file, no allocation beyond the returned value -- when
/// the recorder is off, refused, failed, or already running on this thread.
#[inline]
pub fn enter(unit: &'static Unit, site: u32) -> Guard {
    // One acquire load, one compare, one guard value. `STATE_OFF` is tested
    // first because that is the path a production build that is not recording
    // takes on every call, and it is what endpoint E1 measures.
    match STATE.load(Ordering::Acquire) {
        STATE_OFF => Guard::inert(),
        STATE_CALL => enter_recording(unit, site),
        other => enter_cold(unit, site, other),
    }
}

/// True when this process is recording, initialising it if nothing has yet.
///
/// `spawn_child` reads it: a rewritten spawn site is inside an instrumented
/// function, so an `enter` has all but always run first -- but the name a child
/// carries must not depend on which of the two the process happened to reach
/// first.
pub(crate) fn recording() -> bool {
    match STATE.load(Ordering::Acquire) {
        STATE_CALL => true,
        STATE_UNINIT => {
            init();
            STATE.load(Ordering::Acquire) == STATE_CALL
        }
        _ => false,
    }
}

#[cold]
fn enter_cold(unit: &'static Unit, site: u32, state: u8) -> Guard {
    if state != STATE_UNINIT {
        return Guard::inert();
    }
    init();
    if STATE.load(Ordering::Acquire) == STATE_CALL {
        enter_recording(unit, site)
    } else {
        Guard::inert()
    }
}

#[inline(never)]
fn enter_recording(unit: &'static Unit, site: u32) -> Guard {
    // Reentrancy: inert while the runtime is already running on this thread.
    let Some(_scope) = thread::try_enter_runtime() else {
        return Guard::inert();
    };
    // Before the CALL: from here on, a panic that crosses this frame has a hook
    // to write its PANIC record. One `Once::is_completed` load once it is in.
    panic::install();
    let Some(dir) = ensure_dir() else {
        return Guard::inert();
    };
    let Some(id) = unit_id(unit, dir) else {
        return Guard::inert();
    };
    debug_assert!(
        site <= SITE_INDEX_MASK,
        "site index {site} does not fit the wire format's 24 bits and would alias"
    );
    let packed = pack_site(id, site);
    if !thread::emit(dir, packed, KIND_CALL, OUTCOME_NONE, &[]) {
        return Guard::inert();
    }
    // Only now, with the CALL on the wire: an inert guard must not consume a
    // depth, or the frames that nest inside it would be mis-keyed.
    Guard {
        site: packed,
        depth: thread::open_frame(),
        entered_unwinding: std::thread::panicking(),
    }
}

fn pack_site(unit_id: u8, site: u32) -> u32 {
    (u32::from(unit_id) << UNIT_ID_SHIFT) | (site & SITE_INDEX_MASK)
}

/// A guard that recorded its CALL always records its RETURN -- even if the
/// runtime went inert in between (the unit ceiling, an I/O failure on another
/// thread). Refusal gates `enter`, never the closing of a frame already open,
/// so the converter's frame stack cannot go negative.
#[inline(never)]
fn emit_return(site: u32, depth: u32, entered_unwinding: bool) {
    let _scope = thread::enter_runtime();
    // Only this frame's own entry, and only from the top: a capture left by
    // another frame is neither taken nor disturbed, so nothing another frame is
    // still owed can be reported here -- and this frame's own capture cannot be
    // taken by a `Drop` that ran instrumented code in between.
    let mine = thread::pop_stash_if(site, depth);
    // A panic that begins while the thread is ALREADY unwinding aborts the
    // process, so a frame entered during an unwind and left during the same one
    // cannot have panicked itself -- it is a `Drop` that ran instrumented code
    // and returned. Only a false-to-true transition ACROSS this frame is a
    // panic this frame was torn through by.
    let panicking = !entered_unwinding && std::thread::panicking();
    let outcome = if panicking {
        Outcome::Panic
    } else {
        mine.as_ref().map_or(Outcome::None, |s| s.outcome)
    };
    let capture = if panicking {
        None
    } else {
        mine.as_ref().map(|s| &s.capture)
    };
    let mut buf = [0u8; RETURN_PAYLOAD_MAX];
    let len = write_return_payload(&mut buf, capture);
    if let Some(dir) = SPOOL_DIR.get() {
        thread::emit(dir, site, KIND_RETURN, outcome as u8, &buf[..len]);
    }
    thread::close_frame(depth);
}

// ---------------------------------------------------------------------------
// The exit operand
// ---------------------------------------------------------------------------

const TAG_NO_VALUE: u8 = 0;
const TAG_DEBUG: u8 = 1;
const TAG_UNREAD: u8 = 2;
const RETURN_PAYLOAD_MAX: usize = 2 + probe::CAP;

/// Stash `(site, cap(&v))` for this frame's guard and hand `v` straight back.
///
/// `cap` is called ONLY when the recorder is live on this thread: at tier `off`
/// this function is a move and a compare, and a `Debug` impl that would have
/// been invoked is not invoked.
pub fn ret<T>(
    unit: &'static Unit,
    site: u32,
    cap: impl FnOnce(&T) -> (Capture, Outcome),
    v: T,
) -> T {
    if STATE.load(Ordering::Acquire) == STATE_CALL {
        stash_return(unit, site, cap, &v);
    }
    v
}

#[inline(never)]
fn stash_return<T>(
    unit: &'static Unit,
    site: u32,
    cap: impl FnOnce(&T) -> (Capture, Outcome),
    v: &T,
) {
    // The capture runs INSIDE the runtime scope, so a workspace `Debug` impl
    // that calls instrumented code records nothing (spec §3.6).
    let Some(_scope) = thread::try_enter_runtime() else {
        return;
    };
    // No registration here: a unit with no id has no open frame at this site.
    let Some(id) = unit.current_id() else {
        return;
    };
    // With no frame open on this thread there is no guard that could ever take
    // this, so it is not left for one.
    let depth = thread::frame_depth();
    if depth == 0 {
        return;
    }
    let (capture, outcome) = cap(v);
    thread::push_stash(thread::Stash {
        site: pack_site(id, site),
        depth,
        capture,
        outcome,
    });
}

/// `u8 tag, u8 truncated, then the UTF-8 text`. Always at least the two bytes,
/// on every RETURN, so a reader never has to ask whether a payload is there.
fn write_return_payload(buf: &mut [u8; RETURN_PAYLOAD_MAX], capture: Option<&Capture>) -> usize {
    buf[1] = 0;
    let Some(capture) = capture else {
        buf[0] = TAG_NO_VALUE;
        return 2;
    };
    let Some(text) = capture.text.as_deref() else {
        buf[0] = TAG_UNREAD;
        return 2;
    };
    buf[0] = TAG_DEBUG;
    // `spool::record` refuses a payload it cannot describe rather than clamping
    // one, so the cut happens here, on a char boundary -- and it is witnessed by
    // the flag, whether the capping writer cut the text or this did.
    let (text, cut_here) = spool::cap_utf8(text, probe::CAP);
    buf[1] = u8::from(capture.truncated || cut_here);
    buf[2..2 + text.len()].copy_from_slice(text.as_bytes());
    2 + text.len()
}

// ---------------------------------------------------------------------------
// For tests
// ---------------------------------------------------------------------------

/// Run `f` with this thread marked as inside the runtime.
///
/// Exists so the reentrancy rule is falsifiable: nothing on the recording path
/// calls instrumented code, so there is no other way to provoke reentrancy
/// deterministically. Not part of the instrumented-code API.
#[doc(hidden)]
pub fn __in_runtime<T>(f: impl FnOnce() -> T) -> T {
    let _scope = thread::enter_runtime();
    f()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_site_word_packs_the_unit_id_above_the_index() {
        assert_eq!(pack_site(0, 7), 7);
        assert_eq!(pack_site(1, 81), (1 << 24) | 81);
        assert_eq!(pack_site(254, 0), 254 << 24);
        assert_eq!(pack_site(3, SITE_INDEX_MASK), (3 << 24) | SITE_INDEX_MASK);
    }

    #[test]
    fn a_site_index_that_would_alias_is_masked_not_bled_into_the_unit_id() {
        assert_eq!(pack_site(2, SITE_INDEX_MASK + 1), 2 << 24);
    }

    /// The tags are wire-format numbers, so they are written out here as
    /// numbers. Asserting against the constants would move with them and pin
    /// nothing -- which is exactly what these three tests did until a mutation
    /// run walked through them untouched.
    #[test]
    fn the_payload_tags_are_the_numbers_the_wire_format_names() {
        assert_eq!(TAG_NO_VALUE, 0);
        assert_eq!(TAG_DEBUG, 1);
        assert_eq!(TAG_UNREAD, 2);
    }

    #[test]
    fn a_return_with_no_capture_is_two_bytes() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        assert_eq!(write_return_payload(&mut buf, None), 2);
        assert_eq!(&buf[..2], &[0, 0]);
    }

    #[test]
    fn an_unread_value_is_two_bytes_with_tag_two() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: None,
            truncated: false,
        };
        assert_eq!(write_return_payload(&mut buf, Some(&c)), 2);
        assert_eq!(&buf[..2], &[2, 0]);
    }

    #[test]
    fn a_read_value_carries_its_text_and_its_flag() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: Some("Ok(3)".to_owned()),
            truncated: true,
        };
        let n = write_return_payload(&mut buf, Some(&c));
        assert_eq!(n, 7);
        assert_eq!(buf[0], 1);
        assert_eq!(buf[1], 1);
        assert_eq!(&buf[2..n], b"Ok(3)");
    }

    #[test]
    fn an_over_long_capture_is_clipped_on_a_char_boundary_and_flagged() {
        // `truncated: false` on purpose: the cut happens HERE, and the flag has
        // to be set by the writer that cut, not inherited from the capture.
        let text = "é".repeat(500);
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: Some(text),
            truncated: false,
        };
        let n = write_return_payload(&mut buf, Some(&c));
        assert!(n <= RETURN_PAYLOAD_MAX, "{n} bytes");
        assert_eq!(n, 2 + probe::CAP, "'é' is two bytes and the cap is even");
        assert_eq!(
            buf[1], 1,
            "a payload cut here is a payload marked truncated"
        );
        assert_eq!(
            std::str::from_utf8(&buf[2..n]),
            Ok("é".repeat(probe::CAP / 2).as_str())
        );
    }

    #[test]
    fn an_empty_debug_rendering_is_a_read_value_not_an_unread_one() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: Some(String::new()),
            truncated: false,
        };
        assert_eq!(write_return_payload(&mut buf, Some(&c)), 2);
        assert_eq!(&buf[..2], &[1, 0], "tag 1 with no text, never tag 2");
    }
}
