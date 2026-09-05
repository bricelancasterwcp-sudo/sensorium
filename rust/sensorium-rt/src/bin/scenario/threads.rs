//! Durability (a blocked thread and the four ways a process can end; the spool
//! limit) and thread ordering (serials across concurrent and sequential
//! threads) -- each with an err-flow twin, so kinds 4 and 5 are held to the same
//! bounds as kinds 1 and 2.

use std::sync::mpsc;

use crate::UNIT_B;

// ---------------------------------------------------------------------------
// Durability
// ---------------------------------------------------------------------------

pub(crate) enum End {
    MainReturn,
    Exit,
    Abort,
    Forever,
}

/// Emit one record pair on main, then leave a thread that has written `n`
/// complete frames blocked in `recv()` forever, then end the process the way
/// `end` says. `ready` (when given) is a path to create once the blocked thread
/// is parked, so a test can SIGKILL at a known moment.
pub(crate) fn blocked(n: u32, end: End, ready: Option<&str>) {
    {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 30);
    }
    // A second unit, so the proc header is rewritten twice and "names every
    // registered unit" is a claim with more than one unit in it.
    {
        let _sens_guard = ::sensorium_rt::enter(&UNIT_B, 31);
    }
    spawn_blocked_thread(n);
    println!("blocked_enters {n}");
    if let Some(path) = ready {
        std::fs::write(path, b"ready").expect("writing the ready marker");
    }
    match end {
        End::MainReturn => {}
        End::Exit => std::process::exit(0),
        End::Abort => std::process::abort(),
        End::Forever => loop {
            std::thread::park();
        },
    }
}

fn spawn_blocked_thread(n: u32) {
    let (ready_tx, ready_rx) = mpsc::channel::<()>();
    let (never_tx, never_rx) = mpsc::channel::<()>();
    std::thread::Builder::new()
        .name("blocked".to_owned())
        .spawn(move || {
            for i in 0..n {
                let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 100 + i);
            }
            ready_tx.send(()).expect("signal ready");
            let _ = never_rx.recv();
        })
        .expect("spawn");
    ready_rx.recv().expect("wait for the blocked thread");
    std::mem::forget(never_tx);
}

/// The same as [`blocked`], but every frame on the blocked thread also writes a
/// RAISE and a HANDLED: four records per iteration, in the fixed order CALL,
/// RAISE, HANDLED, RETURN. The process parks forever so a test can SIGKILL it at
/// a known moment and read the torn tail.
pub(crate) fn blocked_errflow(n: u32, ready: Option<&str>) {
    {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 560);
    }
    spawn_blocked_errflow_thread(n);
    println!("blocked_errflow {n}");
    if let Some(path) = ready {
        std::fs::write(path, b"ready").expect("writing the ready marker");
    }
    loop {
        std::thread::park();
    }
}

fn spawn_blocked_errflow_thread(n: u32) {
    let (ready_tx, ready_rx) = mpsc::channel::<()>();
    let (never_tx, never_rx) = mpsc::channel::<()>();
    std::thread::Builder::new()
        .name("blocked".to_owned())
        .spawn(move || {
            for i in 0..n {
                errflow_frame(i);
            }
            ready_tx.send(()).expect("signal ready");
            let _ = never_rx.recv();
        })
        .expect("spawn");
    ready_rx.recv().expect("wait for the blocked thread");
    std::mem::forget(never_tx);
}

/// One iteration: a frame at site `600 + i` holding a RAISE at `700 + i` and a
/// HANDLED at `800 + i`, `i` taken modulo 100 so the three bands are 600-699,
/// 700-799 and 800-899 however many iterations run. They never overlap, so a
/// test can name any record's role from its site alone.
fn errflow_frame(i: u32) {
    let i = i % 100;
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 600 + i);
    let _ = serr!(700 + i, ::sensorium_rt::HOW_TRY, Err::<u8, u8>(7));
    let _ = serr!(800 + i, ::sensorium_rt::HOW_SINK_OK, Err::<u8, u8>(7));
}

/// Two threads writing err-flow records concurrently: the merged sequence must
/// stay unique and gapless across kinds 4 and 5 as well as 1 and 2.
pub(crate) fn errflow_two_threads(n: u32) {
    let h = std::thread::Builder::new()
        .name("second".to_owned())
        .spawn(move || {
            for i in 0..n {
                errflow_frame(i);
            }
        })
        .expect("spawn");
    for i in 0..n {
        errflow_frame(i);
    }
    h.join().expect("join");
    println!("per_thread {n}");
}

/// `n` err-flow frames on the main thread. With a spool limit in force this
/// overruns it, and every attempt after that -- RAISE and HANDLED included -- is
/// a counted drop.
pub(crate) fn errflow_spool_limit(n: u32) {
    for i in 0..n {
        errflow_frame(i);
    }
    println!("iterations {n}");
}

/// `n` sequential frames on the main thread. With a spool limit in force this
/// overruns it, and every attempt after that is a counted drop.
pub(crate) fn spool_limit(n: u32) {
    for i in 0..n {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 40 + (i % 8));
    }
    println!("iterations {n}");
}

// ---------------------------------------------------------------------------
// Serials
// ---------------------------------------------------------------------------

/// A spawned thread emits and finishes BEFORE the main thread emits anything.
/// Serial 1 must still be main's.
pub(crate) fn spawn_first() {
    let h = std::thread::Builder::new()
        .name("wörker-✓".to_owned())
        .spawn(|| {
            let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 50);
        })
        .expect("spawn");
    h.join().expect("join");
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 51);
}

/// Two threads emitting concurrently: the merged sequence must stay unique and
/// gapless.
pub(crate) fn two_threads(n: u32) {
    let h = std::thread::Builder::new()
        .name("second".to_owned())
        .spawn(move || {
            for i in 0..n {
                let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 1000 + i);
            }
        })
        .expect("spawn");
    for i in 0..n {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 2000 + i);
    }
    h.join().expect("join");
    println!("per_thread {n}");
}

/// `n` threads, spawned and joined one at a time, so the OS is free to hand the
/// same thread id out again. Each must still get its own serial.
pub(crate) fn sequential_threads(n: u32) {
    for i in 0..n {
        let h = std::thread::Builder::new()
            .name(format!("seq-{i}"))
            .spawn(move || {
                let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 70 + i);
            })
            .expect("spawn");
        h.join().expect("join");
    }
    println!("threads {n}");
}
