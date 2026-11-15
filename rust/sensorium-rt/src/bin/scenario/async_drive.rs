//! Hand-polled futures in the shape the transformer splices.
//!
//! No tokio here: this binary is compiled without dev-dependencies. The tokio
//! sample lives in `tests/tokio_sample.rs`.

use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll, RawWaker, RawWakerVTable, Waker};

use sensorium_rt::probe::{AnyOutcome as _, DebugCap as _, Probe};

/// Pending once, then `Ready(9)`.
struct Twice {
    polls: u8,
}

impl Future for Twice {
    type Output = u8;

    fn poll(self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<u8> {
        let this = self.get_mut();
        this.polls += 1;
        if this.polls == 1 {
            Poll::Pending
        } else {
            Poll::Ready(9)
        }
    }
}

/// Pending, and calls `enter` while the drive frame is open.
struct Nested {
    polls: u8,
}

impl Future for Nested {
    type Output = ();

    fn poll(self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<()> {
        let this = self.get_mut();
        this.polls += 1;
        if this.polls == 1 {
            let _guard = sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 41);
            Poll::Pending
        } else {
            Poll::Ready(())
        }
    }
}

/// Always pending, so dropping the drive is the close.
struct Stuck;

impl Future for Stuck {
    type Output = ();

    fn poll(self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<()> {
        Poll::Pending
    }
}

/// Panics on the first poll.
struct Boom;

impl Future for Boom {
    type Output = u8;

    fn poll(self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<u8> {
        panic!("async-poll");
    }
}

fn waker() -> Waker {
    fn clone(_: *const ()) -> RawWaker {
        RawWaker::new(std::ptr::null(), &VTABLE)
    }
    fn wake(_: *const ()) {}
    fn wake_by_ref(_: *const ()) {}
    fn drop(_: *const ()) {}
    static VTABLE: RawWakerVTable = RawWakerVTable::new(clone, wake, wake_by_ref, drop);
    // SAFETY: every vtable function ignores the data pointer.
    unsafe { Waker::from_raw(RawWaker::new(std::ptr::null(), &VTABLE)) }
}

// The extra `&` is the autoref ladder the transformer splices. Clippy sees
// the outcome side resolve on `Probe` itself and calls the borrow needless.
#[allow(clippy::needless_borrow)]
fn value_probe(out: &u8) -> (sensorium_rt::probe::Capture, sensorium_rt::probe::Exit) {
    ((&&Probe(out)).debug_cap(), (&&Probe(out)).outcome())
}

/// First poll parks the frame. Second poll returns `9`.
pub fn pending_then_ready() {
    let n = 7u8;
    let caps = sensorium_rt::capture_args(&crate::__SENSORIUM_UNIT, 40, || {
        [("n", sensorium_rt::probe_cap!(&n))]
    });
    let mut drive = sensorium_rt::drive_value(caps, value_probe, Twice { polls: 0 });
    let waker = waker();
    let mut cx = Context::from_waker(&waker);
    assert!(Pin::new(&mut drive).poll(&mut cx).is_pending());
    match Pin::new(&mut drive).poll(&mut cx) {
        Poll::Ready(9) => {}
        other => panic!("expected Ready(9), got {other:?}"),
    }
}

/// A sync `enter` during the first poll sits between CALL and SUSPEND.
pub fn nested_during_poll() {
    let caps = sensorium_rt::capture_args(&crate::__SENSORIUM_UNIT, 40, || []);
    let mut drive = sensorium_rt::drive_async(caps, Nested { polls: 0 });
    let waker = waker();
    let mut cx = Context::from_waker(&waker);
    assert!(Pin::new(&mut drive).poll(&mut cx).is_pending());
    assert!(Pin::new(&mut drive).poll(&mut cx).is_ready());
}

/// Dropping a parked future closes it with no value, after a RESUME.
pub fn drop_while_pending() {
    let caps = sensorium_rt::capture_args(&crate::__SENSORIUM_UNIT, 42, || []);
    let mut drive = sensorium_rt::drive_async(caps, Stuck);
    let waker = waker();
    let mut cx = Context::from_waker(&waker);
    assert!(Pin::new(&mut drive).poll(&mut cx).is_pending());
    drop(drive);
}

/// A panic during the poll is this frame's RETURN, and it propagates.
pub fn panic_during_poll() {
    let caps = sensorium_rt::capture_args(&crate::__SENSORIUM_UNIT, 43, || []);
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let mut drive = sensorium_rt::drive_value(caps, value_probe, Boom);
        let waker = waker();
        let mut cx = Context::from_waker(&waker);
        let _ = Pin::new(&mut drive).poll(&mut cx);
    }));
    assert!(result.is_err(), "the panic must leave the drive future");
}
