//! Two tasks on a current-thread runtime, each yielding once.
//!
//! The spool must show the first task parked before the second task's CALL.
//! A frame left open across the yield would still emit the same kinds, so the
//! hand-polled test is what shows SUSPEND popping the runtime frame: this one
//! shows the same folding on a real tokio scheduler.

mod common;

use std::pin::Pin;
use std::task::{Context, Poll};

use common::{TempDir, KIND_CALL, KIND_RESUME, KIND_RETURN, KIND_SUSPEND};

use sensorium_rt::Unit;

static UNIT: Unit = Unit::new("tokio-sample");

struct YieldOnce {
    polled: bool,
}

impl std::future::Future for YieldOnce {
    type Output = ();

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        if self.polled {
            Poll::Ready(())
        } else {
            self.get_mut().polled = true;
            cx.waker().wake_by_ref();
            Poll::Pending
        }
    }
}

// Same ladder the transformer splices. See `scenario/async_drive.rs`.
#[allow(clippy::needless_borrow)]
fn probe(out: &u8) -> (sensorium_rt::probe::Capture, sensorium_rt::probe::Exit) {
    use sensorium_rt::probe::{AnyOutcome as _, DebugCap as _, Probe};
    ((&&Probe(out)).debug_cap(), (&&Probe(out)).outcome())
}

#[test]
fn two_yielding_tasks_park_between_polls() {
    let dir = TempDir::created("tokio-sample");
    // SAFETY: this test has not spawned a thread yet, and nothing else in
    // this process reads the environment. The runtime reads these once.
    unsafe {
        std::env::set_var("SENSORIUM_SPOOL", dir.path());
        std::env::set_var("SENSORIUM_TIER", "call");
    }

    let rt = tokio::runtime::Builder::new_current_thread()
        .build()
        .expect("current-thread runtime");
    rt.block_on(async {
        let first = async {
            let caps = sensorium_rt::capture_args(&UNIT, 40, || []);
            sensorium_rt::drive_value(caps, probe, async move {
                YieldOnce { polled: false }.await;
                let _guard = sensorium_rt::enter(&UNIT, 42);
                1u8
            })
            .await
        };
        let second = async {
            let caps = sensorium_rt::capture_args(&UNIT, 41, || []);
            sensorium_rt::drive_async(caps, YieldOnce { polled: false }).await
        };
        tokio::join!(first, second);
    });

    // `cargo test` runs this function off the process main thread, so the
    // spool serial is not 1. One thread recorded.
    let spools = dir.spools();
    assert_eq!(spools.len(), 1, "spools: {:?}", dir.walk());
    let kinds: Vec<(u8, u32)> = spools[0]
        .records
        .iter()
        .filter(|r| matches!(r.kind, KIND_CALL | KIND_SUSPEND | KIND_RESUME | KIND_RETURN))
        .map(|r| (r.kind, r.site_index()))
        .collect();
    let pos = |kind: u8, site: u32| {
        kinds
            .iter()
            .position(|row| *row == (kind, site))
            .unwrap_or_else(|| panic!("missing kind {kind} site {site} in {kinds:?}"))
    };
    let call_a = pos(KIND_CALL, 40);
    let suspend_a = pos(KIND_SUSPEND, 40);
    let call_b = pos(KIND_CALL, 41);
    assert!(
        call_a < suspend_a && suspend_a < call_b,
        "task B must start only after task A has parked, got {kinds:?}"
    );
    let resume_a = pos(KIND_RESUME, 40);
    let nested = pos(KIND_CALL, 42);
    let nested_ret = pos(KIND_RETURN, 42);
    let ret_a = pos(KIND_RETURN, 40);
    assert!(
        resume_a < nested && nested < nested_ret && nested_ret < ret_a,
        "the sync call during the resumed poll is inside the async frame, got {kinds:?}"
    );
    assert!(pos(KIND_SUSPEND, 41) < pos(KIND_RESUME, 41));
    assert!(pos(KIND_RESUME, 41) < pos(KIND_RETURN, 41));
}
