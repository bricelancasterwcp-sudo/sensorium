//! Per-run caps. A call past `max_calls` for its site, or past the process
//! event or byte estimate, is counted and not stored.
//!
//! The driver resolves config, suffixes and flags, then exports plain
//! integers in `SENSORIUM_MAX_EVENTS`, `SENSORIUM_MAX_BYTES` and
//! `SENSORIUM_MAX_CALLS`. Unset here means the same defaults. `0` is
//! unlimited. This module does not read a config file and does not parse
//! size suffixes.
//!
//! Elided calls do not open a frame (`thread::open_frame` stays put) and do
//! not run the args closure. Their guard is [`ElidedGuard`], not `Guard`:
//! `Guard`'s drop returns immediately at depth 0, which cannot write the
//! RETURN a panic still needs. On the non-panic path the elided drop writes
//! nothing. On a panic, the hook writes skeleton CALLs (empty payload: args
//! were not read) for the innermost run of elided frames, outermost first,
//! before PANIC. The elided drop then writes RETURN with outcome panic.
//!
//! Counts are not known when the proc header is rewritten, so they are not
//! put there. `<spool>/<pid>.elision.json` is written from `atexit` and,
//! best-effort, from the panic hook.

use std::cell::{Cell, RefCell};
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, OnceLock};

use crate::exit::{self, write_return_payload};
use crate::ffi;
use crate::probe::{Exit, Outcome};
use crate::spool::{self, KIND_CALL, KIND_RETURN, OUTCOME_NONE};
use crate::thread;

/// Same numbers as `src/sensorium/limits.py`.
pub const DEFAULT_MAX_EVENTS: u64 = 100_000;
/// 8 MiB.
pub const DEFAULT_MAX_BYTES: u64 = 8 * 1024 * 1024;
/// Above the largest same-function burst the suite records, below a hot loop.
pub const DEFAULT_MAX_CALLS: u64 = 1024;

const ENV_EVENTS: &str = "SENSORIUM_MAX_EVENTS";
const ENV_BYTES: &str = "SENSORIUM_MAX_BYTES";
const ENV_CALLS: &str = "SENSORIUM_MAX_CALLS";

#[derive(Clone, Copy)]
struct Limits {
    max_events: u64,
    max_bytes: u64,
    max_calls: u64,
}

impl Limits {
    fn from_env() -> Limits {
        Limits {
            max_events: env_u64(ENV_EVENTS, DEFAULT_MAX_EVENTS),
            max_bytes: env_u64(ENV_BYTES, DEFAULT_MAX_BYTES),
            max_calls: env_u64(ENV_CALLS, DEFAULT_MAX_CALLS),
        }
    }

    fn unlimited(self) -> bool {
        self.max_events == 0 && self.max_bytes == 0 && self.max_calls == 0
    }
}

fn env_u64(name: &str, default: u64) -> u64 {
    match std::env::var(name) {
        Err(_) => default,
        Ok(text) if text.trim().is_empty() => default,
        Ok(text) => match text.trim().parse::<u64>() {
            Ok(n) => n,
            Err(_) => {
                eprintln!(
                    "sensorium-rt: {name}={text:?} is not a non-negative integer; using {default}"
                );
                default
            }
        },
    }
}

static LIMITS: OnceLock<Limits> = OnceLock::new();
static EVENTS: AtomicU64 = AtomicU64::new(0);
static BYTES: AtomicU64 = AtomicU64::new(0);

struct SiteRow {
    site: u32,
    elided: u64,
    kept: u64,
    hot: bool,
    /// The cap named when this site first became hot. Marked on the first
    /// drop, not when the row is armed.
    reason: &'static str,
}

struct Budget {
    sites: Vec<SiteRow>,
    hits: Vec<&'static str>,
    failures_kept: u64,
}

static BUDGET: Mutex<Budget> = Mutex::new(Budget {
    sites: Vec::new(),
    hits: Vec::new(),
    failures_kept: 0,
});

static SIDECAR: Mutex<()> = Mutex::new(());

fn limits() -> Limits {
    LIMITS.get().copied().unwrap_or(Limits {
        max_events: DEFAULT_MAX_EVENTS,
        max_bytes: DEFAULT_MAX_BYTES,
        max_calls: DEFAULT_MAX_CALLS,
    })
}

fn lock() -> std::sync::MutexGuard<'static, Budget> {
    BUDGET.lock().unwrap_or_else(|e| e.into_inner())
}

/// Read the integers once and register `atexit`. Called from process init,
/// only when this process is actually recording.
pub(crate) fn install() {
    let _ = LIMITS.set(Limits::from_env());
    // SAFETY: `flush_at_exit` is a process-lifetime `extern "C"` fn with no
    // captured state. `atexit` only stores the pointer.
    unsafe {
        let _ = ffi::atexit(flush_at_exit);
    }
}

extern "C" fn flush_at_exit() {
    write_sidecar();
}

/// One record landed in a spool. The cap compares against this estimate,
/// which is the on-wire size of records actually written.
pub(crate) fn note_written(nbytes: usize) {
    EVENTS.fetch_add(1, Ordering::Relaxed);
    BYTES.fetch_add(nbytes as u64, Ordering::Relaxed);
}

/// Whether this activation is stored.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Admit {
    Record,
    Elide,
}

/// `Record` or count one elision and return `Elide`. Does not run user code.
pub(crate) fn admit(site: u32) -> Admit {
    let limits = limits();
    if limits.unlimited() {
        return Admit::Record;
    }
    let mut g = lock();
    let mut hot_hit: Option<&'static str> = None;
    let mut was_hot = false;
    if let Some(row) = g.sites.iter_mut().find(|s| s.site == site) {
        if row.hot {
            row.elided += 1;
            if row.elided == 1 {
                hot_hit = Some(row.reason);
            }
            was_hot = true;
        }
    }
    if was_hot {
        if let Some(reason) = hot_hit {
            mark(&mut g.hits, reason);
        }
        return Admit::Elide;
    }
    let kept = g
        .sites
        .iter()
        .find(|s| s.site == site)
        .map(|s| s.kept)
        .unwrap_or(0);
    let events = EVENTS.load(Ordering::Relaxed);
    let bytes = BYTES.load(Ordering::Relaxed);
    let mut reasons: [&'static str; 3] = ["", "", ""];
    let mut n = 0usize;
    if limits.max_calls != 0 && kept >= limits.max_calls {
        reasons[n] = "max_calls";
        n += 1;
    }
    if limits.max_events != 0 && events >= limits.max_events {
        reasons[n] = "max_events";
        n += 1;
    }
    if limits.max_bytes != 0 && bytes >= limits.max_bytes {
        reasons[n] = "max_bytes";
        n += 1;
    }
    if n == 0 {
        return Admit::Record;
    }
    for reason in reasons.iter().take(n) {
        mark(&mut g.hits, reason);
    }
    let reason = reasons[0];
    if let Some(row) = g.sites.iter_mut().find(|s| s.site == site) {
        row.hot = true;
        row.elided = 1;
        row.reason = reason;
    } else {
        g.sites.push(SiteRow {
            site,
            elided: 1,
            kept,
            hot: true,
            reason,
        });
    }
    Admit::Elide
}

/// A CALL that was actually written.
pub(crate) fn note_kept(site: u32) {
    let limits = limits();
    if limits.unlimited() {
        return;
    }
    let mut g = lock();
    if let Some(row) = g.sites.iter_mut().find(|s| s.site == site) {
        row.kept += 1;
        if limits.max_calls != 0 && row.kept >= limits.max_calls && !row.hot {
            row.hot = true;
            row.reason = "max_calls";
        }
        return;
    }
    let kept = 1;
    let hot = limits.max_calls != 0 && kept >= limits.max_calls;
    g.sites.push(SiteRow {
        site,
        elided: 0,
        kept,
        hot,
        reason: "max_calls",
    });
}

fn mark(hits: &mut Vec<&'static str>, name: &'static str) {
    if !name.is_empty() && !hits.contains(&name) {
        hits.push(name);
    }
}

/// Spend one elided count so a skeleton CALL is not also reported as dropped.
fn claim_failure(site: u32) -> bool {
    let mut g = lock();
    let Some(row) = g.sites.iter_mut().find(|s| s.site == site) else {
        return false;
    };
    if row.elided == 0 {
        return false;
    }
    row.elided -= 1;
    row.kept += 1;
    g.failures_kept += 1;
    true
}

fn unclaim_failure(site: u32) {
    let mut g = lock();
    if let Some(row) = g.sites.iter_mut().find(|s| s.site == site) {
        row.elided += 1;
        row.kept = row.kept.saturating_sub(1);
    }
    g.failures_kept = g.failures_kept.saturating_sub(1);
}

// ---------------------------------------------------------------------------
// Per-thread layer stack. Recorded frames and elided frames interleave.
// `inside_elided` is the top of this stack, which is what `ret`, LINE and
// err sites consult so a probe inside an elided body does not attach to the
// recorded parent.
// ---------------------------------------------------------------------------

struct ElidedLayer {
    id: u64,
    site: u32,
    entered_unwinding: bool,
    materialized: bool,
}

enum Layer {
    Recorded,
    Elided(ElidedLayer),
}

thread_local! {
    static LAYERS: RefCell<Vec<Layer>> = const { RefCell::new(Vec::new()) };
    static NEXT_ID: Cell<u64> = const { Cell::new(1) };
}

/// True when the innermost frame on this thread was elided.
pub(crate) fn inside_elided() -> bool {
    LAYERS
        .try_with(|c| matches!(c.borrow().last(), Some(Layer::Elided(_))))
        .unwrap_or(false)
}

pub(crate) fn push_recorded() {
    let _ = LAYERS.try_with(|c| c.borrow_mut().push(Layer::Recorded));
}

pub(crate) fn pop_recorded() {
    let _ = LAYERS.try_with(|c| {
        let mut s = c.borrow_mut();
        if matches!(s.last(), Some(Layer::Recorded)) {
            s.pop();
        }
    });
}

pub(crate) fn push_elided(site: u32, entered_unwinding: bool) -> u64 {
    let id = NEXT_ID
        .try_with(|c| {
            let id = c.get();
            c.set(id + 1);
            id
        })
        .unwrap_or(0);
    let _ = LAYERS.try_with(|layers| {
        layers.borrow_mut().push(Layer::Elided(ElidedLayer {
            id,
            site,
            entered_unwinding,
            materialized: false,
        }));
    });
    id
}

enum Taken {
    Missing,
    NotTop,
    Top { materialized: bool },
}

fn take_elided(id: u64) -> Taken {
    LAYERS
        .try_with(|c| {
            let mut s = c.borrow_mut();
            if let Some(Layer::Elided(e)) = s.last() {
                if e.id == id {
                    let materialized = e.materialized;
                    s.pop();
                    return Taken::Top { materialized };
                }
            }
            let Some(i) = s
                .iter()
                .position(|l| matches!(l, Layer::Elided(e) if e.id == id))
            else {
                return Taken::Missing;
            };
            s.remove(i);
            Taken::NotTop
        })
        .unwrap_or(Taken::Missing)
}

fn mark_materialized(id: u64) {
    let _ = LAYERS.try_with(|c| {
        for layer in c.borrow_mut().iter_mut() {
            if let Layer::Elided(e) = layer {
                if e.id == id {
                    e.materialized = true;
                }
            }
        }
    });
}

/// The guard `enter` returns for a call that was not stored.
pub(crate) struct ElidedGuard {
    site: u32,
    id: u64,
    entered_unwinding: bool,
}

impl ElidedGuard {
    pub(crate) fn new(site: u32, id: u64, entered_unwinding: bool) -> ElidedGuard {
        ElidedGuard {
            site,
            id,
            entered_unwinding,
        }
    }
}

impl Drop for ElidedGuard {
    fn drop(&mut self) {
        finish_elided(self.site, self.id, self.entered_unwinding);
    }
}

fn finish_elided(site: u32, id: u64, entered_unwinding: bool) {
    let taken = take_elided(id);
    // A frame entered during someone else's unwind did not panic itself.
    // A frame that is not the top must not emit RETURN: that would close
    // whatever the converter still has open.
    let Taken::Top { materialized } = taken else {
        return;
    };
    if entered_unwinding || !std::thread::panicking() {
        return;
    }
    let mut have_call = materialized;
    if !have_call && claim_failure(site) {
        if emit_skeleton(site) {
            have_call = true;
        } else {
            unclaim_failure(site);
        }
    }
    if have_call {
        emit_panic_return(site);
    }
}

/// Skeleton CALLs for the elided suffix of this thread, outermost first,
/// before the hook writes PANIC. A recorded frame inside an elided one is
/// already the top of the converter stack; those outer elided frames are
/// not rewritten in front of it.
pub(crate) fn materialize_for_panic() {
    let frames = LAYERS
        .try_with(|c| {
            let s = c.borrow();
            let start = s
                .iter()
                .rposition(|l| matches!(l, Layer::Recorded))
                .map(|i| i + 1)
                .unwrap_or(0);
            s[start..]
                .iter()
                .filter_map(|l| match l {
                    Layer::Elided(e) if !e.materialized && !e.entered_unwinding => {
                        Some((e.id, e.site))
                    }
                    _ => None,
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    for (id, site) in frames {
        if !claim_failure(site) {
            continue;
        }
        if emit_skeleton(site) {
            mark_materialized(id);
        } else {
            unclaim_failure(site);
        }
    }
}

fn emit_skeleton(site: u32) -> bool {
    thread::emit_if_open(site, KIND_CALL, OUTCOME_NONE, &[])
}

fn emit_panic_return(site: u32) {
    let _scope = thread::enter_runtime();
    let exit = Exit {
        outcome: Outcome::Panic,
        err_type: None,
    };
    let mut buf = [0u8; exit::RETURN_PAYLOAD_MAX];
    let len = write_return_payload(&mut buf, None, exit);
    let _ = thread::emit_if_open(site, KIND_RETURN, Outcome::Panic as u8, &buf[..len]);
}

struct Snap {
    max_events: u64,
    max_bytes: u64,
    max_calls: u64,
    hits: Vec<&'static str>,
    events: u64,
    calls_elided: u64,
    failures_kept: u64,
    /// `(packed site, elided, kept)` for rows that still have a drop.
    sites: Vec<(u32, u64, u64)>,
}

fn snapshot() -> Snap {
    let limits = limits();
    let g = lock();
    let mut calls_elided = 0u64;
    let mut sites = Vec::new();
    for row in &g.sites {
        if row.elided > 0 {
            calls_elided += row.elided;
            sites.push((row.site, row.elided, row.kept));
        }
    }
    Snap {
        max_events: limits.max_events,
        max_bytes: limits.max_bytes,
        max_calls: limits.max_calls,
        hits: g.hits.clone(),
        events: EVENTS.load(Ordering::Relaxed),
        calls_elided,
        failures_kept: g.failures_kept,
        sites,
    }
}

/// `<dir>/<pid>.elision.json` when anything is still elided. A zero total
/// removes a sidecar a panic wrote earlier, so a run whose every elided
/// call was put back for a failure looks like any other complete trace.
pub(crate) fn write_sidecar() {
    let Some(dir) = crate::SPOOL_DIR.get() else {
        return;
    };
    let snap = snapshot();
    let _write = SIDECAR.lock().unwrap_or_else(|e| e.into_inner());
    let pid = std::process::id();
    let path = dir.join(format!("{pid}.elision.json"));
    if snap.calls_elided == 0 {
        let _ = std::fs::remove_file(&path);
        return;
    }
    let bytes = render(&snap);
    let _ = write_atomic(dir, pid, bytes.as_bytes());
}

fn render(snap: &Snap) -> String {
    let mut json = String::with_capacity(256);
    json.push_str("{\"max_events\":");
    json.push_str(&snap.max_events.to_string());
    json.push_str(",\"max_bytes\":");
    json.push_str(&snap.max_bytes.to_string());
    json.push_str(",\"max_calls\":");
    json.push_str(&snap.max_calls.to_string());
    json.push_str(",\"hit\":[");
    for (i, hit) in snap.hits.iter().enumerate() {
        if i > 0 {
            json.push(',');
        }
        crate::json::push_json_str(&mut json, hit);
    }
    json.push_str("],\"events_recorded\":");
    json.push_str(&snap.events.to_string());
    json.push_str(",\"calls_elided\":");
    json.push_str(&snap.calls_elided.to_string());
    if snap.failures_kept > 0 {
        json.push_str(",\"failures_kept\":");
        json.push_str(&snap.failures_kept.to_string());
    }
    json.push_str(",\"sites\":[");
    for (i, (site, elided, kept)) in snap.sites.iter().enumerate() {
        if i > 0 {
            json.push(',');
        }
        let unit = site >> spool::UNIT_ID_SHIFT;
        let index = site & spool::SITE_INDEX_MASK;
        json.push_str("{\"unit\":");
        json.push_str(&unit.to_string());
        json.push_str(",\"site\":");
        json.push_str(&index.to_string());
        json.push_str(",\"elided\":");
        json.push_str(&elided.to_string());
        json.push_str(",\"kept\":");
        json.push_str(&kept.to_string());
        json.push('}');
    }
    json.push_str("]}");
    json
}

fn write_atomic(dir: &Path, pid: u32, bytes: &[u8]) -> std::io::Result<()> {
    let tmp = dir.join(format!("{pid}.elision.json.tmp"));
    let path = dir.join(format!("{pid}.elision.json"));
    {
        let mut opts = OpenOptions::new();
        opts.write(true).create(true).truncate(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            opts.mode(0o600);
        }
        let mut f = opts.open(&tmp)?;
        f.write_all(bytes)?;
        f.flush()?;
    }
    std::fs::rename(&tmp, &path)
}
