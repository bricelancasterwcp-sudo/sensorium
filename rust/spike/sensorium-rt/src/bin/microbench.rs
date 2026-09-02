//! THROWAWAY SPIKE CODE. The `fib(30)` micro-bench for endpoint E1.
//!
//! Three arms, one process each because `SENSORIUM_TIER` is read once per
//! process:
//!
//! * `plain` -- no guard at all. What uninstrumented code costs.
//! * `off` -- the guard is compiled in, `SENSORIUM_TIER=off`. What
//!   compile-once-gate-at-runtime costs when nobody is recording.
//! * `call` -- the guard is compiled in and recording. What a traced run costs.
//!
//! `fib(30)` is deliberately the worst case: an almost-empty body, so the guard
//! is nearly the whole of the work. It is not a prediction of what a test suite
//! costs -- E1's test-suite arms are that.
//!
//! Run it from the release profile so the runtime is at `opt-level = 3`:
//!
//! ```text
//! cargo run --release --bin microbench
//! ```
//!
//! Output is machine-readable: the measurement runner re-invokes this binary
//! and reads the `*_ns_per_call` lines.

use std::hint::black_box;
use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;

use sensorium_rt::{enter, Unit};

static UNIT: Unit = Unit::new("microbench-unit");

const N: u64 = 30;
const RUNS: usize = 3;
const ARMS: [&str; 3] = ["plain", "off", "call"];

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

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.iter().position(|a| a == "--arm") {
        Some(i) => run_arm(args.get(i + 1).map(String::as_str).unwrap_or("plain")),
        None => orchestrate(),
    }
}

/// One arm, in its own process, with the environment its parent set.
fn run_arm(arm: &str) {
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
    let ns = elapsed.as_nanos() as f64;
    println!(
        "arm {arm} n {N} calls {calls} elapsed_ns {} ns_per_call {:.4}",
        elapsed.as_nanos(),
        ns / calls as f64
    );
}

fn orchestrate() {
    let exe = std::env::current_exe().expect("current_exe");
    let spool_root: PathBuf = std::env::var_os("SENSORIUM_BENCH_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir);
    let calls = call_count(N);
    println!("fib_n {N}");
    println!("runs_per_arm {RUNS}");
    println!("calls {calls}");

    let mut best = Vec::new();
    for arm in ARMS {
        let mut results = Vec::new();
        for run in 0..RUNS {
            let dir = spool_root.join(format!(
                "sensorium-rt-bench-{}-{arm}-{run}",
                std::process::id()
            ));
            let _ = std::fs::remove_dir_all(&dir);
            let mut cmd = Command::new(&exe);
            cmd.arg("--arm").arg(arm);
            cmd.env_remove("SENSORIUM_SPOOL");
            cmd.env_remove("SENSORIUM_TIER");
            match arm {
                "off" => {
                    cmd.env("SENSORIUM_SPOOL", &dir);
                    cmd.env("SENSORIUM_TIER", "off");
                }
                "call" => {
                    cmd.env("SENSORIUM_SPOOL", &dir);
                    cmd.env("SENSORIUM_TIER", "call");
                }
                _ => {}
            }
            let out = cmd.output().expect("running the arm");
            assert!(
                out.status.success(),
                "arm {arm} run {run} failed: {:?}\n{}",
                out.status,
                String::from_utf8_lossy(&out.stderr)
            );
            let line = String::from_utf8_lossy(&out.stdout).trim().to_owned();
            let value: f64 = line
                .split_whitespace()
                .skip_while(|t| *t != "ns_per_call")
                .nth(1)
                .and_then(|t| t.parse().ok())
                .unwrap_or_else(|| panic!("arm {arm} run {run} printed {line:?}"));
            let bytes = spool_bytes(&dir);
            println!("  {arm} run {run} ns_per_call {value:.4} spool_bytes {bytes}");
            let _ = std::fs::remove_dir_all(&dir);
            results.push(value);
        }
        let min = results.iter().copied().fold(f64::INFINITY, f64::min);
        best.push((arm, min));
    }

    for (arm, value) in &best {
        println!("{arm}_ns_per_call {value:.4}");
    }
    let plain = best[0].1;
    for (arm, value) in best.iter().skip(1) {
        println!("{arm}_over_plain {:.3}", value / plain);
        println!("{arm}_added_ns_per_call {:.4}", value - plain);
    }
}

fn spool_bytes(dir: &std::path::Path) -> u64 {
    std::fs::read_dir(dir)
        .map(|rd| {
            rd.filter_map(Result::ok)
                .filter_map(|e| e.metadata().ok())
                .map(|m| m.len())
                .sum()
        })
        .unwrap_or(0)
}
