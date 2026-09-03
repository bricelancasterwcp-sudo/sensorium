//! The subject process for `sensorium-rt`'s integration tests.
//!
//! `SENSORIUM_TIER` and `SENSORIUM_SPOOL` are read ONCE per process, so every
//! falsification test needs its own process with its own environment. This
//! binary is that process: `cargo test` builds it and the integration tests
//! find it through `CARGO_BIN_EXE_scenario`.
//!
//! It also stands in for the transformer (Task 4), which is not written yet:
//! every instrumented body here is written by hand in exactly the shape the
//! transformer injects, so this binary is a standing check that the shape
//! compiles and behaves. The two forms are, verbatim:
//!
//! ```ignore
//! let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);
//!
//! ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, <site>, |__r| {
//!     use ::sensorium_rt::probe::*;
//!     ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
//! }, <e>)
//! ```
//!
//! Usage: `scenario <name> [args]`.

use std::fmt;
use std::sync::mpsc;

use sensorium_rt::{enter, Unit};

/// The unit static the transformer appends to an instrumented crate root. Named
/// exactly as it is named there so the injected forms below are verbatim.
#[doc(hidden)]
pub static __SENSORIUM_UNIT: Unit = Unit::new("scenario-unit-a");

static UNIT_B: Unit = Unit::new("scenario-unit-b");

/// 253 distinct units. With the crate's own unit and `UNIT_255` that is 255
/// registrations, so `UNIT_256` is the one that must be refused.
static MANY: [Unit; 253] = [const { Unit::new("many") }; 253];
static UNIT_255: Unit = Unit::new("the-255th-unit");
static UNIT_256: Unit = Unit::new("the-256th-unit");

/// The exit-operand form, verbatim. `ret_verbatim` below spells it out longhand
/// once, so the macro can never quietly drift from the injected text.
macro_rules! sret {
    ($site:expr, $e:expr) => {
        ::sensorium_rt::ret(
            &crate::__SENSORIUM_UNIT,
            $site,
            |__r| {
                use ::sensorium_rt::probe::*;
                ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
            },
            $e,
        )
    };
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let name = args.get(1).map(String::as_str).unwrap_or("main-only");
    install_hook();
    println!("pid {}", std::process::id());
    match name {
        "main-only" => main_only(),
        "reentrant" => reentrant(),

        "ret-ok" => ret_ok_scenario(),
        "ret-err" => ret_err_scenario(),
        "ret-question" => ret_question_scenario(),
        "ret-panic" => ret_panic_scenario(),
        "ret-unit" => ret_unit_scenario(),
        "ret-mismatch" => ret_mismatch_scenario(),

        "value-nodebug" => value_nodebug(),
        "value-big" => value_big(arg_u32(&args, 2, 1_000_000)),
        "value-early-stop" => value_early_stop(arg_u32(&args, 2, 10_000_000)),
        "value-panic-debug" => value_panic_debug(),
        "value-truncations" => value_truncations(arg_u32(&args, 2, 3)),

        "blocked-main-return" => blocked(arg_u32(&args, 2, 50), End::MainReturn, None),
        "blocked-exit" => blocked(arg_u32(&args, 2, 50), End::Exit, None),
        "blocked-abort" => blocked(arg_u32(&args, 2, 50), End::Abort, None),
        "blocked-forever" => blocked(50, End::Forever, args.get(2).map(String::as_str)),
        "spool-limit" => spool_limit(arg_u32(&args, 2, 6000)),

        "spawn-first" => spawn_first(),
        "two-threads" => two_threads(arg_u32(&args, 2, 400)),
        "sequential-threads" => sequential_threads(arg_u32(&args, 2, 8)),

        "two-units" => two_units(),
        "unit-ceiling" => unit_ceiling(),

        other => {
            eprintln!("scenario: unknown scenario {other:?}");
            std::process::exit(2);
        }
    }
}

fn arg_u32(args: &[String], i: usize, default: u32) -> u32 {
    args.get(i).and_then(|s| s.parse().ok()).unwrap_or(default)
}

/// The panic hook Task 3 installs, in the shape it will have: silent for a
/// panic raised *inside* the instrument (a workspace `Debug` impl that panics
/// while the recorder is formatting it), the ordinary hook for everything else.
fn install_hook() {
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        if sensorium_rt::in_runtime() {
            return;
        }
        previous(info);
    }));
}

// ---------------------------------------------------------------------------
// Shapes with no return value
// ---------------------------------------------------------------------------

/// One guard on the main thread. Site index 7.
fn main_only() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 7);
}

/// An `enter` reached from inside the runtime must be inert; the one after it
/// must not be.
fn reentrant() {
    sensorium_rt::__in_runtime(|| {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 90);
    });
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 91);
}

/// A `-> ()` function: the transformer emits an `enter` and NO `ret`, so its
/// RETURN carries outcome 0 and tag 0. Site index 15.
fn ret_unit_scenario() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 15);
    std::hint::black_box(1u8);
}

// ---------------------------------------------------------------------------
// Outcomes
// ---------------------------------------------------------------------------

/// The injected exit-operand form written out longhand, once, so the `sret!`
/// macro below it is provably the same text.
fn ret_verbatim() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 10);
    ::sensorium_rt::ret(
        &crate::__SENSORIUM_UNIT,
        10,
        |__r| {
            use ::sensorium_rt::probe::*;
            ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
        },
        Ok(3),
    )
}

fn ret_ok_scenario() {
    let r = ret_verbatim();
    println!("returned {r:?}");
}

fn returns_err() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 11);
    sret!(11, Err("x".to_owned()))
}

fn ret_err_scenario() {
    let r = returns_err();
    println!("returned {r:?}");
}

/// Site 12 returns `Err`; site 13's `?` propagates it, so site 13's tail is
/// never reached and its frame closes with nothing stashed.
fn question_inner() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 12);
    sret!(12, Err("propagated".to_owned()))
}

fn question_outer() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 13);
    let v = question_inner()?;
    sret!(13, Ok(v))
}

fn ret_question_scenario() {
    let r = question_outer();
    println!("returned {r:?}");
}

fn panics() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 14);
    panic!("boom");
}

fn ret_panic_scenario() {
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(|_| {}));
    let r = std::panic::catch_unwind(panics);
    std::panic::set_hook(previous);
    assert!(r.is_err(), "the scenario must actually unwind");
    println!("unwound 1");
}

/// A stash that belongs to no open frame. Site 60's `ret` runs while site 60
/// has no guard -- the shape instrumented code takes when an `enter`'s CALL
/// could not be written (a broken spool) but the wrapped exit operand still
/// runs. The next frame to close, site 61, must NOT take that value.
fn ret_mismatch_scenario() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 61);
    let orphan: Result<u8, String> = sret!(60, Ok(7));
    println!("orphan {orphan:?}");
}

// ---------------------------------------------------------------------------
// Values
// ---------------------------------------------------------------------------

struct NoDbg(#[allow(dead_code)] u8);

struct PanicDbg;

/// A hand-written `Debug` impl that propagates the writer's error, which is
/// what most hand-written ones do. std's collection impls do NOT (see
/// `rust/HONESTY.md` §2), so this is the shape whose cost the cap actually
/// bounds.
struct EarlyStop(u32);

impl fmt::Debug for EarlyStop {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for i in 0..self.0 {
            write!(f, "{i},")?;
        }
        Ok(())
    }
}

impl fmt::Debug for PanicDbg {
    fn fmt(&self, _f: &mut fmt::Formatter<'_>) -> fmt::Result {
        panic!("this Debug impl panics on purpose");
    }
}

fn returns_nodebug() -> NoDbg {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 20);
    sret!(20, NoDbg(9))
}

fn value_nodebug() {
    let v = returns_nodebug();
    println!("returned {}", v.0);
}

fn returns_big(n: u32) -> Vec<u8> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 21);
    let big = std::hint::black_box(vec![7u8; n as usize]);
    let started = std::time::Instant::now();
    let out = sret!(21, big);
    println!("capture_ns {}", started.elapsed().as_nanos());
    out
}

fn value_big(n: u32) {
    let v = returns_big(n);
    println!("returned {}", v.len());
}

fn returns_early_stop(n: u32) -> EarlyStop {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 24);
    let v = std::hint::black_box(EarlyStop(n));
    let started = std::time::Instant::now();
    let out = sret!(24, v);
    println!("capture_ns {}", started.elapsed().as_nanos());
    out
}

fn value_early_stop(n: u32) {
    let v = returns_early_stop(n);
    println!("returned {}", v.0);
}

fn returns_panicking_debug() -> PanicDbg {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 22);
    sret!(22, PanicDbg)
}

fn value_panic_debug() {
    let v = returns_panicking_debug();
    std::hint::black_box(&v);
    println!("survived 1");
}

fn returns_long(i: u32) -> Vec<u32> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 23);
    sret!(23, (0..500u32).map(|x| x + i).collect::<Vec<u32>>())
}

/// `n` returns that all truncate, so the thread header's counter has a value to
/// be wrong about.
fn value_truncations(n: u32) {
    for i in 0..n {
        std::hint::black_box(returns_long(i));
    }
    println!("truncations {n}");
}

// ---------------------------------------------------------------------------
// Durability
// ---------------------------------------------------------------------------

enum End {
    MainReturn,
    Exit,
    Abort,
    Forever,
}

/// Emit one record pair on main, then leave a thread that has written `n`
/// complete frames blocked in `recv()` forever, then end the process the way
/// `end` says. `ready` (when given) is a path to create once the blocked thread
/// is parked, so a test can SIGKILL at a known moment.
fn blocked(n: u32, end: End, ready: Option<&str>) {
    {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 30);
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

/// `n` sequential frames on the main thread. With a spool limit in force this
/// overruns it, and every attempt after that is a counted drop.
fn spool_limit(n: u32) {
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
fn spawn_first() {
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
fn two_threads(n: u32) {
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
fn sequential_threads(n: u32) {
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

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

fn two_units() {
    let _a = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 80);
    let _b = ::sensorium_rt::enter(&UNIT_B, 81);
}

/// 1 + 253 + 1 = 255 registrations, then a 256th that must be refused, then two
/// more `enter`s that must record nothing: one on a brand-new unit and one on a
/// unit that registered successfully long before the refusal.
///
/// The frame at site 300 is held OPEN across the refusal, because refusal gates
/// `enter` and never the closing of a frame that is already open -- if it did,
/// a converter's frame stack would go negative.
fn unit_ceiling() {
    let _outer = enter(&crate::__SENSORIUM_UNIT, 300);
    for (i, unit) in MANY.iter().enumerate() {
        let _g = enter(unit, i as u32);
    }
    {
        let _g = enter(&UNIT_255, 254);
    }
    {
        let _g = enter(&UNIT_256, 255);
    }
    {
        let _g = enter(&UNIT_B, 256);
    }
    {
        let _g = enter(&MANY[0], 257);
    }
    println!("attempted 258");
}
