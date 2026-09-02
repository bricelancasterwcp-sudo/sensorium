//! THROWAWAY SPIKE CODE. The subject process for `sensorium-rt`'s tests.
//!
//! `SENSORIUM_TIER` and `SENSORIUM_SPOOL` are read ONCE per process, so every
//! falsification test needs its own process with its own environment. This
//! binary is that process: `cargo test` builds it, and the integration tests
//! find it through `CARGO_BIN_EXE_scenario`.
//!
//! Usage: `scenario <name> [arg]`. Each scenario returns from `main` normally
//! (never `process::exit`) so thread-local destructors run.

use std::sync::mpsc;

use sensorium_rt::{enter, Unit};

static UNIT_A: Unit = Unit::new("unit-a-metadata");
static UNIT_B: Unit = Unit::new("unit-b-metadata");

/// 300 distinct units, so the 8-bit unit id can actually be exhausted.
static MANY: [Unit; 300] = [const { Unit::new("many") }; 300];

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let name = args.get(1).map(String::as_str).unwrap_or("main-only");
    println!("pid {}", std::process::id());
    match name {
        "main-only" => main_only(),
        "spawn-first" => spawn_first(),
        "two-threads" => two_threads(),
        "panic" => panic_scenario(),
        "leak" => leak(),
        "clean-thread" => clean_thread(),
        "two-units" => two_units(),
        "reentrant" => reentrant(),
        "unit-limit" => unit_limit(args.get(2).and_then(|s| s.parse().ok()).unwrap_or(300)),
        other => {
            eprintln!("scenario: unknown scenario {other:?}");
            std::process::exit(2);
        }
    }
}

/// One guard on the main thread. Site index 7.
fn main_only() {
    let _g = enter(&UNIT_A, 7);
}

/// A spawned thread emits and finishes BEFORE the main thread emits anything.
/// Serial 1 must still be main's.
fn spawn_first() {
    let h = std::thread::Builder::new()
        .name("wörker-✓".to_owned())
        .spawn(|| {
            let _g = enter(&UNIT_A, 11);
        })
        .expect("spawn");
    h.join().expect("join");
    let _g = enter(&UNIT_A, 12);
}

/// Two threads emitting concurrently: the merged sequence must stay unique and
/// strictly increasing.
fn two_threads() {
    const N: u32 = 400;
    let h = std::thread::Builder::new()
        .name("second".to_owned())
        .spawn(|| {
            for i in 0..N {
                let _g = enter(&UNIT_A, 1000 + i);
            }
        })
        .expect("spawn");
    for i in 0..N {
        let _g = enter(&UNIT_A, i);
    }
    h.join().expect("join");
}

/// One guard dropped during unwinding, then one dropped normally.
fn panic_scenario() {
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(|_| {}));
    let r = std::panic::catch_unwind(|| {
        let _g = enter(&UNIT_A, 1);
        panic!("boom");
    });
    std::panic::set_hook(previous);
    assert!(r.is_err(), "the scenario must actually unwind");
    let _g = enter(&UNIT_A, 2);
}

/// A thread still alive when the process exits. Its thread-local destructor
/// never runs, so its buffered records are lost and its spool has no
/// `THREAD_END` -- the loss the spike's `BufWriter` implies, made observable.
fn leak() {
    let _g = enter(&UNIT_A, 5);
    let (ready_tx, ready_rx) = mpsc::channel::<()>();
    let (never_tx, never_rx) = mpsc::channel::<()>();
    std::thread::Builder::new()
        .name("leaked".to_owned())
        .spawn(move || {
            {
                let _g = enter(&UNIT_A, 6);
            }
            ready_tx.send(()).expect("signal ready");
            // Nothing ever sends, and the sender is kept alive by the closure
            // below, so this blocks until the process exits.
            let _ = never_rx.recv();
        })
        .expect("spawn");
    ready_rx.recv().expect("wait for the leaked thread");
    // Keep the sender alive so `recv` cannot return `Err(Disconnected)`.
    std::mem::forget(never_tx);
}

/// A thread that exits cleanly, on a process whose main thread never emits.
fn clean_thread() {
    let h = std::thread::Builder::new()
        .name("worker".to_owned())
        .spawn(|| {
            let _g = enter(&UNIT_A, 21);
        })
        .expect("spawn");
    h.join().expect("join");
}

/// Two distinct units, so the site word's unit-id bits and the proc header's
/// unit map both carry two entries.
fn two_units() {
    let _a = enter(&UNIT_A, 3);
    let _b = enter(&UNIT_B, 4);
}

/// An `enter` reached from inside the runtime must be inert.
fn reentrant() {
    sensorium_rt::__spike_in_runtime(|| {
        let _g = enter(&UNIT_A, 900);
    });
    let _g = enter(&UNIT_A, 901);
}

/// Enter `n` distinct units in order.
fn unit_limit(n: usize) {
    for (i, unit) in MANY.iter().take(n).enumerate() {
        let _g = enter(unit, i as u32);
    }
}
