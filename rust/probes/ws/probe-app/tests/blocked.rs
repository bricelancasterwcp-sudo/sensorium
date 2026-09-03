//! A thread that is still running when the process exits.
//!
//! The worker does instrumented work, says so, and then blocks on a channel
//! whose sender is leaked — so it never returns and never writes a
//! `THREAD_END`. The converter must list it in `live_threads` with
//! `incomplete` still false (the *process* finished, the thread did not), and
//! every record it wrote before blocking must be present with no hole in the
//! process-global sequence (`rust/HONESTY.md` §4).

use std::sync::mpsc;
use std::thread;
use std::time::Duration;

#[test]
fn a_worker_blocks_past_the_end_of_the_test() {
    let (never, blocked_on) = mpsc::channel::<()>();
    // Leaked on purpose: a dropped sender would wake `recv()` and end the
    // worker, and then there would be no live thread left to check.
    std::mem::forget(never);
    let (ready, done) = mpsc::channel::<u32>();
    thread::spawn(move || probe_app::work_then_block(&blocked_on, &ready));
    // A handshake, not a sleep: the worker has finished its instrumented work
    // when this returns, and is on its way into a `recv()` it never leaves.
    let value = done
        .recv_timeout(Duration::from_secs(30))
        .expect("the worker reported its work");
    assert_eq!(value, 6);
}
