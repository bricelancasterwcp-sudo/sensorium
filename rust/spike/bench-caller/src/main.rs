//! THROWAWAY SPIKE CODE. One arm of the `fib(30)` micro-bench, in its own
//! process (`SENSORIUM_TIER` is read once per process) and its own package.
//!
//! WHY ITS OWN PACKAGE. `sensorium-rt` is pinned to `opt-level = 3` in every
//! profile, and a cargo package override applies to every TARGET of that
//! package -- so a bench binary living inside `sensorium-rt` is compiled at
//! opt-level 3 too, in the dev profile as much as in release. E1's
//! pre-registered lens is the dev profile: instrumented code at opt-level 0
//! against a runtime at 3, where the MIR inliner is off and
//! `sensorium_rt::enter` is a real cross-crate call. That lens is only
//! reachable from a package with no override of its own, which is this one:
//! `cargo build` gives an opt-0 caller, `cargo build --release` an opt-3 one.
//!
//! `microbench` (in `sensorium-rt`) orchestrates both.

use std::hint::black_box;
use std::time::Instant;

use sensorium_rt::{enter, Unit};

static UNIT: Unit = Unit::new("bench-caller-unit");

const N: u64 = 30;

/// No guard: the baseline the other two arms are read against.
fn fib_plain(n: u64) -> u64 {
    if n < 2 {
        n
    } else {
        fib_plain(n - 1) + fib_plain(n - 2)
    }
}

/// The guard is the first statement of the body, exactly as the transformer
/// splices it.
fn fib_guarded(n: u64) -> u64 {
    let _sens_guard = enter(&UNIT, 1);
    if n < 2 {
        n
    } else {
        fib_guarded(n - 1) + fib_guarded(n - 2)
    }
}

/// Calls made by the naive recursion: c(0) = c(1) = 1, c(n) = 1 + c(n-1) + c(n-2).
fn call_count(n: u64) -> u64 {
    let (mut a, mut b) = (1u64, 1u64);
    for _ in 2..=n {
        let next = 1 + a + b;
        a = b;
        b = next;
    }
    b
}

/// `caller=<profile>(opt<level>) rt=opt3`.
///
/// The caller half is stamped by `build.rs` from cargo's own `PROFILE` and
/// `OPT_LEVEL`. The `rt=opt3` half is the workspace manifest's
/// `[profile.*.package.sensorium-rt] opt-level = 3`, which `cargo build -v`
/// shows as `--crate-name sensorium_rt ... -C opt-level=3` in both profiles.
fn lens() -> String {
    format!(
        "caller={}(opt{}) rt=opt3",
        env!("SENSORIUM_CALLER_PROFILE"),
        env!("SENSORIUM_CALLER_OPT_LEVEL")
    )
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--lens") {
        println!("{}", lens());
        return;
    }
    let arm = args
        .iter()
        .position(|a| a == "--arm")
        .and_then(|i| args.get(i + 1))
        .map(String::as_str)
        .unwrap_or("plain");

    let n = black_box(N);
    let start = Instant::now();
    let value = if arm == "plain" {
        fib_plain(n)
    } else {
        fib_guarded(n)
    };
    let elapsed = start.elapsed();
    black_box(value);

    let calls = call_count(N);
    println!(
        "arm {arm} {} n={N} calls={calls} elapsed_ns={} ns_per_call={:.4}",
        lens(),
        elapsed.as_nanos(),
        elapsed.as_nanos() as f64 / calls as f64
    );
}
