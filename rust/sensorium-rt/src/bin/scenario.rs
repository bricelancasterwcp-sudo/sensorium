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
        "drop-calls-instrumented" => drop_calls_instrumented_scenario(),
        "drop-recurses" => drop_recurses_scenario(arg_u32(&args, 2, 1) as u8),
        "drop-recurses-bypass" => drop_recurses_bypass_scenario(),
        "wide-site" => wide_site(),
        "unnamed-thread" => unnamed_thread(),

        "value-nodebug" => value_nodebug(),
        "value-big" => value_big(arg_u32(&args, 2, 1_000_000)),
        "value-early-stop" => value_early_stop(arg_u32(&args, 2, 10_000_000)),
        "value-panic-debug" => value_panic_debug(),
        "value-empty-debug" => value_empty_debug(),
        "value-truncations" => value_truncations(arg_u32(&args, 2, 3)),

        "panic-caught" => panic_caught_scenario(),
        "panic-uncaught" => panic_uncaught_scenario(),
        "panic-non-string" => panic_non_string_scenario(),
        "panic-long" => panic_long_scenario(),

        "spawn-from-main" => spawn_from_main(),
        "spawn-empty-named-parent" => spawn_empty_named_parent(),
        "panic-unrecorded-thread" => panic_unrecorded_thread(),
        "panic-truncated-before-spool" => panic_truncated_before_spool(),
        "spawn-grandchild" => spawn_grandchild(),
        "spawn-value" => spawn_value(),
        "spawn-panics" => spawn_panics(),

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

/// The `panic!` and the `line!()` that reports it are the SAME source line, so
/// a test compares the hook's location against the source rather than against a
/// number written down twice. `#[rustfmt::skip]` is what keeps them there.
#[rustfmt::skip]
fn panics() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 14);
    println!("panic_site {}:{}", file!(), line!()); panic!("boom");
}

/// No hook of its own: the runtime's hook is the one under test, and the
/// message the previous hook prints is what E7 compares.
fn ret_panic_scenario() {
    let r = std::panic::catch_unwind(panics);
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
// A `Drop` that runs instrumented code between an exit operand and its guard
// ---------------------------------------------------------------------------

/// A local whose `Drop` calls instrumented code. Declared AFTER the guard, so it
/// drops BEFORE it -- which is the window in which a single-slot stash gets
/// wiped and the outer frame silently reads `none`.
struct DropCallsInstrumented;

impl Drop for DropCallsInstrumented {
    fn drop(&mut self) {
        inner_unit_fn();
    }
}

/// A `-> ()` fn: `enter` and no `ret`, so it stashes nothing of its own.
fn inner_unit_fn() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 71);
}

fn outer_with_dropping_local() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 70);
    let _local = DropCallsInstrumented;
    sret!(70, Err("outer".to_owned()))
}

fn drop_calls_instrumented_scenario() {
    let r = outer_with_dropping_local();
    println!("returned {r:?}");
}

/// A `Drop` that calls the SAME instrumented function one level down. Both
/// frames are site 72; only their depths tell them apart.
struct DropRecurses(u8);

impl Drop for DropRecurses {
    fn drop(&mut self) {
        if self.0 > 0 {
            let _ = std::hint::black_box(recursive_frame(self.0 - 1));
        }
    }
}

fn recursive_frame(n: u8) -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 72);
    let _local = DropRecurses(n);
    sret!(72, Ok(n))
}

fn drop_recurses_scenario(n: u8) {
    let r = recursive_frame(n);
    println!("returned {r:?}");
    println!("frames {}", u32::from(n) + 1);
}

/// The same shape, except the inner frame leaves by `?` and so stashes NOTHING.
/// Matching on the site alone would let it take the OUTER frame's capture --
/// same site, still pending -- and report `Ok(9)` as its own while the outer
/// frame closed `none`. The depth is what forbids it.
struct DropRecursesBypass(bool);

impl Drop for DropRecursesBypass {
    fn drop(&mut self) {
        if self.0 {
            let _ = std::hint::black_box(bypass_frame(false));
        }
    }
}

fn returns_err_at_75() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 75);
    sret!(75, Err("bypass".to_owned()))
}

fn bypass_frame(recurse: bool) -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 74);
    let _local = DropRecursesBypass(recurse);
    if !recurse {
        let v = returns_err_at_75()?;
        return sret!(74, Ok(v));
    }
    sret!(74, Ok(9))
}

fn drop_recurses_bypass_scenario() {
    let r = bypass_frame(true);
    println!("returned {r:?}");
}

// ---------------------------------------------------------------------------
// Header and site-word edges
// ---------------------------------------------------------------------------

/// A site index that needs all 24 of its bits.
fn wide_site() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 0x00ab_cdef);
}

/// A thread with no name at all: `name_len` is 0 and records start at byte 28.
fn unnamed_thread() {
    let h = std::thread::spawn(|| {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 76);
    });
    h.join().expect("join");
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

/// A `Debug` impl that writes nothing. Its capture is `Some("")` -- a value that
/// WAS read and renders empty -- which the wire must keep distinct from a value
/// that could not be read at all.
struct EmptyDbg;

impl fmt::Debug for EmptyDbg {
    fn fmt(&self, _f: &mut fmt::Formatter<'_>) -> fmt::Result {
        Ok(())
    }
}

fn returns_empty_debug() -> EmptyDbg {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 25);
    sret!(25, EmptyDbg)
}

fn value_empty_debug() {
    let v = returns_empty_debug();
    println!("returned {v:?}.");
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

// ---------------------------------------------------------------------------
// Panics
// ---------------------------------------------------------------------------

/// An instrumented frame that CATCHES an instrumented frame's panic. The outer
/// returns a `u8` rather than the `Result` `catch_unwind` handed it: an `Err` at
/// the exit operand would close the outer frame `err`, and what this arm pins is
/// that catching a panic leaves the catching frame `ok`.
fn caught_outer() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 17);
    let caught = std::panic::catch_unwind(panicking_inner).is_err();
    sret!(17, u8::from(caught))
}

#[rustfmt::skip]
fn panicking_inner() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 16);
    println!("panic_site {}:{}", file!(), line!()); panic!("caught boom");
}

fn panic_caught_scenario() {
    println!("caught {}", caught_outer());
}

#[rustfmt::skip]
fn panics_uncaught() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 18);
    println!("panic_site {}:{}", file!(), line!()); panic!("uncaught boom");
}

/// Unwinds out of `main`: the thread-local destructor still runs, so the spool
/// still ends with `THREAD_END`, and the process still exits 101.
fn panic_uncaught_scenario() {
    std::hint::black_box(panics_uncaught());
}

/// A payload that is neither `&str` nor `String`.
#[rustfmt::skip]
fn panics_with_a_number() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 19);
    println!("panic_site {}:{}", file!(), line!()); std::panic::panic_any(7u32);
}

fn panic_non_string_scenario() {
    let r = std::panic::catch_unwind(panics_with_a_number);
    assert!(r.is_err(), "the scenario must actually unwind");
    println!("unwound 1");
}

/// A message far past the hook's cap, in three-byte characters so a cut that
/// did not step back to a char boundary would not be UTF-8.
fn panics_at_length() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 26);
    let msg = "\u{20ac}".repeat(2000);
    println!("msg_bytes {}", msg.len());
    panic!("{msg}");
}

fn panic_long_scenario() {
    let r = std::panic::catch_unwind(panics_at_length);
    assert!(r.is_err(), "the scenario must actually unwind");
    println!("unwound 1");
}

// ---------------------------------------------------------------------------
// spawn_child
// ---------------------------------------------------------------------------

/// The site strings the transformer bakes at a rewritten `std::thread::spawn`:
/// `"<workspace-relative file>:<line>"`.
const SITE_CHILD: &str = concat!(file!(), ":", line!());
const SITE_GRANDCHILD: &str = concat!(file!(), ":", line!());
const SITE_VALUE: &str = concat!(file!(), ":", line!());
const SITE_PANIC: &str = concat!(file!(), ":", line!());

/// libtest's shape: it names the thread it runs a `#[test]` on with the test's
/// own path, and a thread that test spawns is what rung 1 found unnamed.
const WORKER: &str = "sensorium_rt::tests::worker";

/// A child of the MAIN thread. Main is not a task, so the child's name is its
/// site alone -- no `main :: ` prefix.
fn spawn_from_main() {
    // `main` is instrumented too, so the main thread has a spool of its own to
    // be unnamed-as-a-task in.
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 206);
    println!("site {SITE_CHILD}");
    let h = sensorium_rt::spawn_child(SITE_CHILD, || {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 200);
        // The OS thread name is std's own -- `spawn_child` names the TASK, in a
        // thread-local of its own, and a child of `std::thread::spawn` has no OS
        // name. An implementation that reached for `Builder::name` instead would
        // be changing something the program itself can see.
        println!(
            "child_os_name {}",
            std::thread::current().name().unwrap_or("<none>")
        );
    });
    h.join().expect("join");
}

/// A parent whose OS name is the empty string. An empty name is no name: the
/// header writes an unnamed thread as zero bytes, so a derived `" :: spawn@..."`
/// would name a parent no reader could ever see.
fn spawn_empty_named_parent() {
    println!("site {SITE_CHILD}");
    std::thread::Builder::new()
        .name(String::new())
        .spawn(|| {
            let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 208);
            let child = sensorium_rt::spawn_child(SITE_CHILD, || {
                let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 209);
            });
            child.join().expect("join the child");
        })
        .expect("spawn")
        .join()
        .expect("join the empty-named parent");
}

/// A thread that panics having recorded NOTHING. The hook opens no spool -- that
/// is what makes it unable to fail, and so unable to abort a panicking process
/// (`src/panic.rs`) -- so this thread leaves no file at all.
/// A local whose `Drop` runs instrumented code, so this thread's FIRST spool is
/// opened during the unwind -- after the hook has already cut an over-long panic
/// message it had nowhere to write.
struct EntersOnDrop;

impl Drop for EntersOnDrop {
    fn drop(&mut self) {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 211);
    }
}

/// The hook cuts a 6000-byte message on a thread with no spool, and the spool
/// that thread opens a moment later must not carry a truncation counter for a
/// record that was never written.
fn panic_truncated_before_spool() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 212);
    let h = std::thread::spawn(|| {
        let _local = EntersOnDrop;
        let msg = "\u{20ac}".repeat(2000);
        println!("msg_bytes {}", msg.len());
        panic!("{msg}");
    });
    h.join().expect_err("the child must have panicked");
    println!("survived 1");
}

fn panic_unrecorded_thread() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 210);
    let h = std::thread::spawn(|| panic!("orphan boom"));
    h.join().expect_err("the child must have panicked");
    println!("survived 1");
}

/// A named thread, its child and its grandchild: three names, two `::` joins.
fn spawn_grandchild() {
    println!("site_child {SITE_CHILD}");
    println!("site_grandchild {SITE_GRANDCHILD}");
    println!("parent {WORKER}");
    std::thread::Builder::new()
        .name(WORKER.to_owned())
        .spawn(|| {
            let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 201);
            let child = sensorium_rt::spawn_child(SITE_CHILD, || {
                let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 202);
                let grandchild = sensorium_rt::spawn_child(SITE_GRANDCHILD, || {
                    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 203);
                });
                grandchild.join().expect("join the grandchild");
            });
            child.join().expect("join the child");
        })
        .expect("spawn")
        .join()
        .expect("join the worker");
}

/// The handle is std's own: it carries the closure's value back.
fn spawn_value() {
    let h = sensorium_rt::spawn_child(SITE_VALUE, || {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 204);
        41u32
    });
    println!("joined {}", h.join().expect("join"));
}

/// And it re-raises the child's panic, payload unchanged, without touching the
/// thread that joined.
fn spawn_panics() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 207);
    println!("site {SITE_PANIC}");
    let h = sensorium_rt::spawn_child(SITE_PANIC, || {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 205);
        panic!("child boom");
    });
    let payload = h.join().expect_err("the child must have panicked");
    let msg = payload
        .downcast_ref::<&str>()
        .copied()
        .unwrap_or("<not a &str>");
    println!("join_msg {msg}");
    println!("join_err 1");
    println!("survived 1");
}
