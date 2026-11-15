//! Driving an `async fn` body or an `async` block.
//!
//! A sync guard cannot be the RETURN of a future. Its `Drop` runs when the
//! future is dropped, which may be another thread and is never the `.await`
//! the caller would read as a return, and a frame left open on a worker
//! between polls would parent every later task on that worker. The transformer
//! does not splice `enter_args` into an async body.
//!
//! It splices [`capture_args`] (once, before `async move` takes the parameters,
//! and only when this process is recording) and [`drive_async`] or
//! [`drive_value`]. The drive future emits CALL on its first poll, SUSPEND
//! (wire kind 7) when that poll is `Pending`, RESUME (kind 8) on the next
//! poll, and RETURN only when the inner future is `Ready`, this future is
//! dropped while suspended, or the poll unwinds. The converter parks the same
//! frame across SUSPEND/RESUME, so a poll on another worker does not nest
//! under the suspended call and the tree stays one frame.
//!
//! Argument `Debug` runs inside [`capture_args`], not on a later poll: the
//! closure borrows the parameters, and `async move` has to be free to take
//! them afterwards. An elided activation may therefore have formatted
//! arguments it does not store. Tier `off` does not call the closure at all.

use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicU64, Ordering};
use std::task::{Context, Poll};

use crate::cap::{self, Admit, ElidedGuard};
use crate::exit::{write_return_payload, RETURN_PAYLOAD_MAX};
use crate::probe::{Capture, Exit, Outcome};
use crate::spool::{KIND_CALL, KIND_RESUME, KIND_RETURN, KIND_SUSPEND, OUTCOME_NONE};
use crate::thread;
use crate::{pack_site, Unit, STATE, STATE_CALL, STATE_OFF, STATE_UNINIT};

static NEXT_ASYNC: AtomicU64 = AtomicU64::new(1);

/// Owned argument captures, or the fact that this activation records nothing.
///
/// Built by [`capture_args`] and consumed on the first poll. The captures are
/// already formatted: the drive future must not borrow the parameters the
/// `async move` block took.
pub struct ArgCaps {
    kind: CapsKind,
}

enum CapsKind {
    Inert,
    Live {
        packed: u32,
        args: Vec<(&'static str, Capture)>,
    },
}

impl ArgCaps {
    fn inert() -> ArgCaps {
        ArgCaps {
            kind: CapsKind::Inert,
        }
    }
}

/// Format `args` only when this process is recording.
///
/// `N = 0` (`|| []`) is "the arguments were read and there were none", the
/// same record [`crate::enter_args`] writes for a function with no parameters.
#[inline]
pub fn capture_args<const N: usize>(
    unit: &'static Unit,
    site: u32,
    args: impl FnOnce() -> [(&'static str, Capture); N],
) -> ArgCaps {
    match STATE.load(Ordering::Acquire) {
        STATE_OFF => ArgCaps::inert(),
        STATE_CALL => capture_live(unit, site, args),
        other => capture_cold(unit, site, args, other),
    }
}

#[cold]
fn capture_cold<const N: usize>(
    unit: &'static Unit,
    site: u32,
    args: impl FnOnce() -> [(&'static str, Capture); N],
    state: u8,
) -> ArgCaps {
    if state != STATE_UNINIT {
        return ArgCaps::inert();
    }
    crate::init();
    if STATE.load(Ordering::Acquire) == STATE_CALL {
        capture_live(unit, site, args)
    } else {
        ArgCaps::inert()
    }
}

fn capture_live<const N: usize>(
    unit: &'static Unit,
    site: u32,
    args: impl FnOnce() -> [(&'static str, Capture); N],
) -> ArgCaps {
    // Re-entrant `Debug` must not format again, and must not record.
    let Some(_scope) = thread::try_enter_runtime() else {
        return ArgCaps::inert();
    };
    crate::panic::install();
    let Some(dir) = crate::ensure_dir() else {
        return ArgCaps::inert();
    };
    let Some(id) = crate::unit_id(unit, dir) else {
        return ArgCaps::inert();
    };
    let packed = pack_site(id, site);
    ArgCaps {
        kind: CapsKind::Live {
            packed,
            args: args().into_iter().collect(),
        },
    }
}

enum Phase {
    Fresh,
    /// Recording, and this poll's frame is on the thread-local stack.
    Active,
    /// Recording, frame parked. The next poll resumes it.
    Suspended,
    Elided,
    /// Elided layer popped, so a later task on this thread is not inside it.
    ElidedParked,
    Inert,
    Closed,
}

/// The future the transformer builds around an async body.
///
/// `G` is the output probe. [`drive_async`] passes none: a unit (or `!`) body
/// has nothing to read, and the converter turns wire outcome `none` plus
/// `ret: unit` into `()` the way a sync unit function does. [`drive_value`]
/// passes the autoref probe, which has to be spelled at the splice. A generic
/// function cannot see the concrete `Debug` impl.
pub struct Drive<F, G> {
    fut: F,
    probe: Option<G>,
    caps: ArgCaps,
    phase: Phase,
    site: u32,
    depth: u32,
    async_id: u64,
    entered_unwinding: bool,
    elided: Option<ElidedGuard>,
}

/// Unit or diverging async body. RETURN carries no value.
#[allow(clippy::type_complexity)]
pub fn drive_async<F: Future>(
    caps: ArgCaps,
    fut: F,
) -> Drive<F, fn(&F::Output) -> (Capture, Exit)> {
    Drive::new(caps, None, fut)
}

/// Value-returning async body or async block. `probe` runs only when the
/// inner future is `Ready` and this activation is being stored.
pub fn drive_value<F, G>(caps: ArgCaps, probe: G, fut: F) -> Drive<F, G>
where
    F: Future,
    G: FnOnce(&F::Output) -> (Capture, Exit),
{
    Drive::new(caps, Some(probe), fut)
}

impl<F, G> Drive<F, G> {
    fn new(caps: ArgCaps, probe: Option<G>, fut: F) -> Drive<F, G> {
        Drive {
            fut,
            probe,
            caps,
            phase: Phase::Fresh,
            site: 0,
            depth: 0,
            async_id: 0,
            entered_unwinding: false,
            elided: None,
        }
    }

    /// CALL on the first poll, RESUME on a later one. An inert or elided
    /// activation still polls the inner future.
    fn begin_poll(&mut self) {
        match self.phase {
            Phase::Fresh => self.begin_first(),
            Phase::Suspended => self.begin_resume(),
            Phase::ElidedParked => {
                self.elided = Some(new_elided(self.site));
                self.phase = Phase::Elided;
            }
            Phase::Inert | Phase::Elided | Phase::Active | Phase::Closed => {}
        }
        self.entered_unwinding = std::thread::panicking();
    }

    fn begin_first(&mut self) {
        let CapsKind::Live { packed, args } =
            std::mem::replace(&mut self.caps.kind, CapsKind::Inert)
        else {
            self.phase = Phase::Inert;
            return;
        };
        self.site = packed;
        self.async_id = NEXT_ASYNC.fetch_add(1, Ordering::Relaxed);
        let admit = {
            let _scope = thread::enter_runtime();
            cap::admit(packed)
        };
        if admit == Admit::Elide {
            self.elided = Some(new_elided(packed));
            self.phase = Phase::Elided;
            return;
        }
        let pairs: Vec<(&str, Capture)> = args.iter().map(|(n, c)| (*n, c.clone())).collect();
        let mut buf = [0u8; crate::line::LINE_PAYLOAD_MAX];
        let len = {
            let _scope = thread::enter_runtime();
            let (len, _) = crate::line::write_line_payload(
                &mut buf,
                &pairs,
                &[],
                crate::redact::key(),
                crate::redact::knobs(),
            );
            len
        };
        let wrote = emit(packed, KIND_CALL, OUTCOME_NONE, &buf[..len as usize]);
        if !wrote {
            self.phase = Phase::Inert;
            return;
        }
        cap::note_kept(packed);
        self.depth = thread::open_frame();
        cap::push_recorded();
        self.phase = Phase::Active;
    }

    fn begin_resume(&mut self) {
        let resumed = emit(
            self.site,
            KIND_RESUME,
            OUTCOME_NONE,
            &self.async_id.to_le_bytes(),
        );
        // Depth was closed at SUSPEND. This poll, possibly on another thread,
        // opens its own.
        self.depth = thread::open_frame();
        cap::push_recorded();
        if resumed {
            self.phase = Phase::Active;
            return;
        }
        // The CALL is on the wire and the RESUME was lost. Close anyway so
        // this thread's depth does not stay elevated.
        finish_return(self.site, self.depth, exit_none(), None);
        self.phase = Phase::Closed;
    }

    fn suspend(&mut self) {
        match self.phase {
            Phase::Active => {
                emit(
                    self.site,
                    KIND_SUSPEND,
                    OUTCOME_NONE,
                    &self.async_id.to_le_bytes(),
                );
                cap::pop_recorded();
                thread::close_frame(self.depth);
                self.phase = Phase::Suspended;
            }
            Phase::Elided => {
                // Not panicking here: dropping the guard only pops the layer,
                // so the next task on this thread is not inside an elided frame.
                self.elided = None;
                self.phase = Phase::ElidedParked;
            }
            _ => {}
        }
    }

    fn finish_ready(&mut self, output: &F::Output)
    where
        F: Future,
        G: FnOnce(&F::Output) -> (Capture, Exit),
    {
        match self.phase {
            Phase::Active => {
                let probed = self.probe.take().map(|probe| {
                    let _scope = thread::enter_runtime();
                    probe(output)
                });
                let (exit, capture) = match probed {
                    Some((capture, exit)) => (exit, Some(capture)),
                    None => (exit_none(), None),
                };
                finish_return(self.site, self.depth, exit, capture.as_ref());
                self.phase = Phase::Closed;
            }
            Phase::Elided => {
                self.elided = None;
                self.phase = Phase::Closed;
            }
            _ => {}
        }
    }
}

fn exit_none() -> Exit {
    Exit {
        outcome: Outcome::None,
        err_type: None,
    }
}

fn new_elided(site: u32) -> ElidedGuard {
    let entered = std::thread::panicking();
    let id = cap::push_elided(site, entered);
    ElidedGuard::new(site, id, entered)
}

fn emit(site: u32, kind: u8, outcome: u8, payload: &[u8]) -> bool {
    crate::SPOOL_DIR
        .get()
        .is_some_and(|dir| thread::emit(dir, site, kind, outcome, payload))
}

fn finish_return(site: u32, depth: u32, exit: Exit, capture: Option<&Capture>) {
    let _scope = thread::enter_runtime();
    let mut buf = [0u8; RETURN_PAYLOAD_MAX];
    let len = write_return_payload(&mut buf, capture, exit);
    emit(site, KIND_RETURN, exit.outcome as u8, &buf[..len]);
    cap::pop_recorded();
    thread::close_frame(depth);
}

impl<F, G> Drop for Drive<F, G> {
    fn drop(&mut self) {
        match self.phase {
            Phase::Active => {
                // A panic that starts during this poll is this frame's. A poll
                // that began already unwinding is a `Drop` of something else
                // running instrumented code, the same rule as a sync guard.
                let panic_here = !self.entered_unwinding && std::thread::panicking();
                let exit = if panic_here {
                    Exit {
                        outcome: Outcome::Panic,
                        err_type: None,
                    }
                } else {
                    exit_none()
                };
                finish_return(self.site, self.depth, exit, None);
                self.phase = Phase::Closed;
            }
            Phase::Suspended => {
                // Parked. RESUME onto this thread, then close with no value:
                // the future was dropped, it did not return.
                emit(
                    self.site,
                    KIND_RESUME,
                    OUTCOME_NONE,
                    &self.async_id.to_le_bytes(),
                );
                let depth = thread::open_frame();
                cap::push_recorded();
                finish_return(self.site, depth, exit_none(), None);
                self.phase = Phase::Closed;
            }
            Phase::Elided => {
                // Dropping the guard while panicking writes the skeleton CALL
                // and the panic RETURN. While not panicking it only pops.
                self.elided = None;
                self.phase = Phase::Closed;
            }
            _ => {}
        }
    }
}

impl<F, G> Future for Drive<F, G>
where
    F: Future,
    G: FnOnce(&F::Output) -> (Capture, Exit),
{
    type Output = F::Output;

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<F::Output> {
        // SAFETY: `fut` stays at its address for the life of this pin. The
        // other fields are plain data and are not projected as pinned.
        let this = unsafe { self.get_unchecked_mut() };
        this.begin_poll();
        // SAFETY: same pin as above; `begin_poll` does not move `fut`.
        let fut = unsafe { Pin::new_unchecked(&mut this.fut) };
        match fut.poll(cx) {
            Poll::Pending => {
                this.suspend();
                Poll::Pending
            }
            Poll::Ready(value) => {
                this.finish_ready(&value);
                Poll::Ready(value)
            }
        }
    }
}
