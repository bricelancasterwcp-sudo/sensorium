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
//!
//! match <operand> { __t => {
//!     ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, <site>, <how>, || {
//!         use ::sensorium_rt::probe::*;
//!         (&&&Probe(&__t)).err_cap()
//!     });
//!     __t
//! } }
//!
//! ::sensorium_rt::err_site_value(&crate::__SENSORIUM_UNIT, <site>, <how>, || {
//!     use ::sensorium_rt::probe::*;
//!     (&&Probe(&e)).err_cap_value()
//! });
//!
//! ::sensorium_rt::err_site_unbound(&crate::__SENSORIUM_UNIT, <site>, <how>);
//! ```
//!
//! Usage: `scenario <name> [args]`.
//!
//! The scenarios themselves live in `scenario/`, one module per group; this file
//! is the dispatch, the units the transformer would append, and the injected
//! exit-operand macro.

// The in-place err-flow wrap is a single-binding `match` BY DESIGN (design R3):
// binding the operand to `__t` and handing it straight back is what preserves
// drop order and the `let _` drop point. Clippy calls that shape redundant; the
// transformer will emit it in every workspace all the same, so the scenario
// binary compiles it rather than dodging it.
#![allow(clippy::match_single_binding)]

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

/// The in-place `?`/sink form, verbatim. `errflow::try_verbatim` spells it out
/// longhand once.
macro_rules! serr {
    ($site:expr, $how:expr, $e:expr) => {
        match $e {
            __t => {
                ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, $site, $how, || {
                    use ::sensorium_rt::probe::*;
                    (&&&Probe(&__t)).err_cap()
                });
                __t
            }
        }
    };
}

/// The `Err(e) =>` arm form, verbatim: the ladder is handed the BOUND error.
macro_rules! serr_value {
    ($site:expr, $how:expr, $e:expr) => {
        ::sensorium_rt::err_site_value(&crate::__SENSORIUM_UNIT, $site, $how, || {
            use ::sensorium_rt::probe::*;
            (&&Probe(&$e)).err_cap_value()
        })
    };
}

/// The `Err(_)`/`Err(..)` arm form, verbatim: nothing is bound, so nothing is
/// probed.
macro_rules! serr_unbound {
    ($site:expr, $how:expr) => {
        ::sensorium_rt::err_site_unbound(&crate::__SENSORIUM_UNIT, $site, $how)
    };
}

// A file directly under `src/bin/` is a crate ROOT, so a plain `mod ret;` would
// look for `src/bin/ret.rs`; `#[path]` puts the scenario modules in
// `src/bin/scenario/` instead. The dispatch itself stays in a file NAMED
// `scenario.rs` because `file!()` is part of the `SITE_*` constants below and
// `tests/spawn.rs` pins that file name as the shape of a baked spawn site.
#[path = "scenario/errflow.rs"]
mod errflow;
#[path = "scenario/panics.rs"]
mod panics;
#[path = "scenario/ret.rs"]
mod ret;
#[path = "scenario/spawn.rs"]
mod spawn;
#[path = "scenario/threads.rs"]
mod threads;
#[path = "scenario/units.rs"]
mod units;
#[path = "scenario/values.rs"]
mod values;

use sensorium_rt::Unit;

use errflow::{
    arm_unbound, arm_value_debug, arm_value_nodebug, err_big, err_nodebug, errflow_lazy,
    let_underscore_err, sink_ok_err, sink_ok_ok, try_err, try_ok, try_option, typed_err_return,
};
use panics::{
    panic_caught_scenario, panic_long_scenario, panic_non_string_scenario, panic_uncaught_scenario,
};
use ret::{
    drop_calls_instrumented_scenario, drop_recurses_bypass_scenario, drop_recurses_scenario,
    main_only, reentrant, ret_err_scenario, ret_mismatch_scenario, ret_ok_scenario,
    ret_panic_scenario, ret_question_scenario, ret_unit_scenario, unnamed_thread, wide_site,
};
use spawn::{
    panic_truncated_before_spool, panic_unrecorded_thread, spawn_empty_named_parent,
    spawn_from_main, spawn_grandchild, spawn_panics, spawn_value,
};
use threads::{
    blocked, blocked_errflow, errflow_spool_limit, errflow_two_threads, sequential_threads,
    spawn_first, spool_limit, two_threads, End,
};
use units::{two_units, unit_ceiling};
use values::{
    value_big, value_early_stop, value_empty_debug, value_nodebug, value_panic_debug,
    value_truncations,
};

/// The unit static the transformer appends to an instrumented crate root. Named
/// exactly as it is named there so the injected forms below are verbatim.
#[doc(hidden)]
pub static __SENSORIUM_UNIT: Unit = Unit::new("scenario-unit-a");

pub(crate) static UNIT_B: Unit = Unit::new("scenario-unit-b");

/// The site strings the transformer bakes at a rewritten `std::thread::spawn`:
/// `"<workspace-relative file>:<line>"`. They stay in this file, rather than in
/// `scenario/spawn.rs` where they are used, because `file!()` is part of their
/// value and `tests/spawn.rs` pins the shape against this file's name.
pub(crate) const SITE_CHILD: &str = concat!(file!(), ":", line!());
pub(crate) const SITE_GRANDCHILD: &str = concat!(file!(), ":", line!());
pub(crate) const SITE_VALUE: &str = concat!(file!(), ":", line!());
pub(crate) const SITE_PANIC: &str = concat!(file!(), ":", line!());

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
        "blocked-errflow" => {
            blocked_errflow(arg_u32(&args, 2, 50), args.get(3).map(String::as_str))
        }
        "spool-limit" => spool_limit(arg_u32(&args, 2, 6000)),

        "spawn-first" => spawn_first(),
        "two-threads" => two_threads(arg_u32(&args, 2, 400)),
        "sequential-threads" => sequential_threads(arg_u32(&args, 2, 8)),

        "try-err" => try_err(),
        "try-ok" => try_ok(),
        "try-option" => try_option(),
        "sink-ok-err" => sink_ok_err(),
        "sink-ok-ok" => sink_ok_ok(),
        "let-underscore-err" => let_underscore_err(),
        "arm-value-debug" => arm_value_debug(),
        "arm-value-nodebug" => arm_value_nodebug(),
        "arm-unbound" => arm_unbound(),
        "err-nodebug" => err_nodebug(),
        "err-big" => err_big(),
        "typed-err-return" => typed_err_return(),
        "errflow-lazy" => errflow_lazy(),
        "errflow-two-threads" => errflow_two_threads(arg_u32(&args, 2, 400)),
        "errflow-spool-limit" => errflow_spool_limit(arg_u32(&args, 2, 3000)),

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
