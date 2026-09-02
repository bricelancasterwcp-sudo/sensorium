//! THROWAWAY SPIKE CODE. Per-thread state: serial, reentrancy depth, spool.

use std::cell::{Cell, RefCell};
use std::path::Path;
use std::sync::atomic::{AtomicU32, Ordering};

use crate::spool::Spool;

/// Serials are minted from 2 upward. Serial 1 is RESERVED for the main thread
/// (the thread whose `gettid() == getpid()`) whether or not it ever emits, so a
/// spawned thread that emits first still gets 2.
static NEXT_SERIAL: AtomicU32 = AtomicU32::new(2);

thread_local! {
    /// Non-zero while the runtime itself is running (opening a spool, writing a
    /// header). `enter` returns an inert guard while it is set, so instrumented
    /// code reached from inside the runtime emits nothing (Python's `in_hook`).
    static DEPTH: Cell<u32> = const { Cell::new(0) };
    /// 0 until this thread mints one.
    static SERIAL: Cell<u32> = const { Cell::new(0) };
    /// Opened on the thread's first event. Its destructor writes `THREAD_END`
    /// and flushes -- which is exactly the loss a leaked thread suffers.
    static SPOOL: RefCell<Option<Spool>> = const { RefCell::new(None) };
}

/// Linux: the main thread is the one whose thread id equals the process id.
fn is_main_thread() -> bool {
    // SAFETY: both calls take no arguments and cannot fail.
    unsafe { libc::gettid() == libc::getpid() }
}

/// This thread's serial, minting it on first use.
fn serial() -> u32 {
    SERIAL.with(|c| {
        let existing = c.get();
        if existing != 0 {
            return existing;
        }
        let minted = if is_main_thread() {
            1
        } else {
            NEXT_SERIAL.fetch_add(1, Ordering::Relaxed)
        };
        c.set(minted);
        minted
    })
}

/// Held while the runtime runs. Its `Drop` clears the depth even if the body
/// panics, so a fault inside the instrument cannot wedge the thread silently.
pub(crate) struct RuntimeScope(());

impl Drop for RuntimeScope {
    fn drop(&mut self) {
        let _ = DEPTH.try_with(|d| d.set(d.get().saturating_sub(1)));
    }
}

/// `Some` only when the runtime was not already running on this thread.
pub(crate) fn try_enter_runtime() -> Option<RuntimeScope> {
    DEPTH
        .try_with(|d| {
            if d.get() != 0 {
                return None;
            }
            d.set(1);
            Some(RuntimeScope(()))
        })
        .ok()
        .flatten()
}

/// Unconditionally mark the runtime as running. Used only by the hidden test
/// hook that makes the reentrancy rule falsifiable.
pub(crate) fn force_enter_runtime() -> Option<RuntimeScope> {
    DEPTH
        .try_with(|d| {
            d.set(d.get() + 1);
            RuntimeScope(())
        })
        .ok()
}

/// Append one record to this thread's spool, opening it on first use.
/// Returns false if nothing was written.
pub(crate) fn emit(dir: &Path, site: u32, kind: u8, outcome: u8) -> bool {
    SPOOL
        .try_with(|cell| {
            let Ok(mut slot) = cell.try_borrow_mut() else {
                return false;
            };
            if slot.is_none() {
                let serial = serial();
                let name = std::thread::current().name().unwrap_or("").to_owned();
                match Spool::open(dir, std::process::id(), serial, &name) {
                    Ok(s) => *slot = Some(s),
                    Err(e) => {
                        crate::fail_process("opening a spool file", &e);
                        return false;
                    }
                }
            }
            let Some(spool) = slot.as_mut() else {
                return false;
            };
            match spool.record(crate::next_seq(), crate::spool::now_ns(), site, kind, outcome) {
                Ok(()) => true,
                Err(e) => {
                    crate::fail_process("writing a spool record", &e);
                    false
                }
            }
        })
        .unwrap_or(false)
}
