//! `sensorium-rt` -- THROWAWAY SPIKE CODE for the rung-1 Rust mechanics spike
//! (`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`). Evidence, not
//! product: it is never merged to main, never `cargo install`ed, and never
//! depended on by the sensorium Python package.
//!
//! At this tier the runtime records exactly two things per instrumented fn item:
//! a CALL when the entry guard is created and a RETURN when it drops. No `?`
//! sites, no locals, no return values, no output capture. Its cost is what
//! endpoint E1 measures, so the inert path is one acquire load of a single
//! `u8` (a plain `mov` on x86-64), one compare, and the guard value itself --
//! nothing else, and no allocation.
//!
//! The transformer injects, as the first statement of every eligible fn body:
//!
//! ```ignore
//! let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);
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
//! Environment (read once per process, on the first `enter`):
//!
//! * `SENSORIUM_SPOOL` -- the spool directory. Unset or empty: the runtime is
//!   inert. Nothing is created, nothing is written, nothing is allocated.
//! * `SENSORIUM_TIER` -- `off` or `call`. Absent (or empty) means `call`. Any
//!   other value is refused with one stderr line and the runtime stays inert:
//!   recording a tier the caller did not ask for would put dishonest data in
//!   the trace.
//!
//! See `spool.rs` for the wire format and for the buffered-tail loss the spike
//! deliberately accepts.

#[cfg(not(target_os = "linux"))]
compile_error!(
    "sensorium-rt (spike) is Linux-only: thread serials come from gettid()/getpid() and the \
     spike's lens is this box. Rung 2 is where portability is designed, not patched in."
);

mod spool;
mod thread;

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU16, AtomicU64, AtomicU8, Ordering};
use std::sync::{Mutex, Once, OnceLock};

use spool::{
    KIND_CALL, KIND_RETURN, OUTCOME_NONE, OUTCOME_PANIC, SITE_INDEX_MASK, UNIT_ID_SHIFT,
};

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
/// `Acquire` so a thread that sees `STATE_CALL` also sees `SPOOL_DIR`.
static STATE: AtomicU8 = AtomicU8::new(STATE_UNINIT);
static INIT: Once = Once::new();
static SPOOL_DIR: OnceLock<PathBuf> = OnceLock::new();
static START_NS: AtomicU64 = AtomicU64::new(0);

/// One `fetch_add` per record. `Relaxed` is sufficient: a single atomic's
/// modification order is consistent with happens-before, so two events ordered
/// by any synchronisation are ordered by their sequence numbers too.
static SEQ: AtomicU64 = AtomicU64::new(0);

/// Registered units, indexed by unit id.
static UNITS: Mutex<Vec<&'static str>> = Mutex::new(Vec::new());

/// The wire format packs the unit id into 8 bits, so at most this many units
/// can be distinguished. Registering the 256th distinct unit makes the runtime
/// refuse to record rather than alias two units onto one id.
///
/// The brief's rule is "the 256th distinct unit makes the runtime refuse", read
/// literally: ids run 0..=254, so id 255 is never assigned and 255 units is the
/// ceiling. One id of slack, deliberately, rather than a rule that disagrees
/// with the sentence a converter author will read.
const MAX_UNITS: usize = 255;

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
        START_NS.store(spool::now_ns(), Ordering::Relaxed);
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
        // The proc header exists from the process's first event, before any
        // unit has registered; each registration rewrites it.
        write_proc_header(dir);
    });
    if STATE.load(Ordering::Acquire) != STATE_CALL {
        return None;
    }
    Some(dir.as_path())
}

fn write_proc_header(dir: &Path) {
    let units = UNITS.lock().unwrap_or_else(|e| e.into_inner());
    write_proc_header_locked(dir, &units);
}

fn write_proc_header_locked(dir: &Path, units: &[&'static str]) {
    if let Err(e) = spool::write_proc_header(
        dir,
        std::process::id(),
        START_NS.load(Ordering::Relaxed),
        units,
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
}

fn unit_id(unit: &'static Unit, dir: &Path) -> Option<u8> {
    let id = unit.id.load(Ordering::Acquire);
    if id != UNIT_UNREGISTERED {
        return Some(id as u8);
    }
    register_unit(unit, dir)
}

#[cold]
fn register_unit(unit: &'static Unit, dir: &Path) -> Option<u8> {
    let mut units = UNITS.lock().unwrap_or_else(|e| e.into_inner());
    // Re-check under the lock: another thread may have registered it.
    let id = unit.id.load(Ordering::Acquire);
    if id != UNIT_UNREGISTERED {
        return Some(id as u8);
    }
    if units.len() >= MAX_UNITS {
        STATE.store(STATE_REFUSED, Ordering::Release);
        let metadata = unit.metadata;
        REFUSAL_WARNED.call_once(|| {
            eprintln!(
                "sensorium-rt: refusing to record: this process reached {MAX_UNITS} instrumented \
                 units and {metadata:?} is the {}th; the wire format packs the unit id into 8 \
                 bits of the site word, so recording further units would alias them. Every \
                 later enter() is inert.",
                MAX_UNITS + 1
            );
        });
        return None;
    }
    let id = units.len() as u16;
    units.push(unit.metadata);
    unit.id.store(id, Ordering::Release);
    write_proc_header_locked(dir, &units);
    Some(id as u8)
}

// ---------------------------------------------------------------------------
// The entry guard
// ---------------------------------------------------------------------------

/// The entry guard. First-declared is last-dropped, so every `let`-bound local
/// of the instrumented body drops before RETURN.
///
/// An inert guard carries no site and its `Drop` is a single branch.
#[must_use]
pub struct Guard {
    site: Option<u32>,
}

impl Guard {
    #[inline]
    fn inert() -> Guard {
        Guard { site: None }
    }
}

impl Drop for Guard {
    #[inline]
    fn drop(&mut self) {
        let Some(site) = self.site else {
            return;
        };
        emit_return(site);
    }
}

/// A guard that recorded its CALL always records its RETURN -- even if the
/// runtime went inert in between (the unit ceiling, an I/O failure on another
/// thread). Refusal gates `enter`, never the closing of a frame already open,
/// so the converter's frame stack cannot go negative.
#[inline(never)]
fn emit_return(site: u32) {
    let outcome = if std::thread::panicking() {
        OUTCOME_PANIC
    } else {
        OUTCOME_NONE
    };
    if let Some(dir) = SPOOL_DIR.get() {
        thread::emit(dir, site, KIND_RETURN, outcome);
    }
}

/// Record a CALL and return the guard whose drop records the RETURN.
///
/// Inert -- no record, no file, no allocation beyond the returned value -- when
/// the recorder is off, refused, failed, or already running on this thread.
#[inline]
pub fn enter(unit: &'static Unit, site: u32) -> Guard {
    match STATE.load(Ordering::Acquire) {
        STATE_CALL => enter_recording(unit, site),
        STATE_UNINIT => {
            init();
            if STATE.load(Ordering::Acquire) == STATE_CALL {
                enter_recording(unit, site)
            } else {
                Guard::inert()
            }
        }
        _ => Guard::inert(),
    }
}

#[inline(never)]
fn enter_recording(unit: &'static Unit, site: u32) -> Guard {
    // Reentrancy: inert while the runtime is already running on this thread.
    let Some(_scope) = thread::try_enter_runtime() else {
        return Guard::inert();
    };
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
    let packed = (u32::from(id) << UNIT_ID_SHIFT) | (site & SITE_INDEX_MASK);
    if !thread::emit(dir, packed, KIND_CALL, OUTCOME_NONE) {
        return Guard::inert();
    }
    Guard { site: Some(packed) }
}

// ---------------------------------------------------------------------------
// Test hook
// ---------------------------------------------------------------------------

/// Run `f` with this thread marked as "inside the runtime".
///
/// This exists ONLY so the reentrancy rule is falsifiable from a test: nothing
/// on the recording path calls instrumented code, so there is no other way to
/// provoke reentrancy deterministically. Not part of the rung-2 API.
#[doc(hidden)]
pub fn __spike_in_runtime<T>(f: impl FnOnce() -> T) -> T {
    let _scope = thread::force_enter_runtime();
    f()
}
