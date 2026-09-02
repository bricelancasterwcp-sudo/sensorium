//! THROWAWAY SPIKE CODE. The `fib(30)` micro-bench for endpoint E1.
//!
//! Three arms:
//!
//! * `plain` -- no guard at all. What uninstrumented code costs.
//! * `off` -- the guard is compiled in, `SENSORIUM_TIER=off`. What
//!   compile-once-gate-at-runtime costs when nobody is recording.
//! * `call` -- the guard is compiled in and recording. What a traced run costs.
//!
//! TWO LENSES, and the difference between them is large enough to reverse a
//! conclusion:
//!
//! * `caller=dev(opt0) rt=opt3` -- E1's PRE-REGISTERED lens. Instrumented code
//!   at opt-level 0, runtime at 3. The MIR inliner is off, so `enter` is a real
//!   cross-crate call.
//! * `caller=release(opt3) rt=opt3` -- both optimised, `enter`'s gate inlined
//!   into the caller.
//!
//! Each arm therefore runs once per caller binary. `bench-caller` is a separate
//! package precisely so both exist (see its module doc); build both profiles
//! before running:
//!
//! ```text
//! cargo build && cargo build --release && cargo run --release --bin microbench
//! ```
//!
//! Output is machine-readable: one `key=value` line per number, with the lens
//! on every line, for Task 5's runner. `#`-prefixed lines are a human summary.
//!
//! `fib(30)` is deliberately the worst case: an almost-empty body, so the guard
//! is nearly the whole of the work. It is not a prediction of what a test suite
//! costs -- E1's test-suite arms are that.

use std::path::{Path, PathBuf};
use std::process::Command;

const RUNS: usize = 3;
const ARMS: [&str; 3] = ["plain", "off", "call"];

fn main() {
    let callers = match find_callers() {
        Ok(c) => c,
        Err(e) => {
            eprintln!("microbench: {e}");
            std::process::exit(2);
        }
    };
    let spool_root: PathBuf = std::env::var_os("SENSORIUM_BENCH_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir);

    println!("bench runs_per_arm={RUNS}");
    let mut summary: Vec<(String, Vec<(&str, f64)>)> = Vec::new();
    for caller in &callers {
        let lens = lens_of(caller);
        let mut best: Vec<(&str, f64)> = Vec::new();
        for arm in ARMS {
            let mut results = Vec::new();
            for run in 0..RUNS {
                let (value, bytes) = one_run(caller, arm, run, &spool_root);
                println!(
                    "run {lens} arm={arm} run={run} metric=ns_per_call value={value:.4} \
                     spool_bytes={bytes}"
                );
                results.push(value);
            }
            let min = results.iter().copied().fold(f64::INFINITY, f64::min);
            println!("result {lens} arm={arm} metric=ns_per_call value={min:.4}");
            best.push((arm, min));
        }
        let plain = best[0].1;
        for (arm, value) in best.iter().skip(1) {
            println!(
                "result {lens} arm={arm} metric=over_plain value={:.3}",
                value / plain
            );
            println!(
                "result {lens} arm={arm} metric=added_ns_per_call value={:.4}",
                value - plain
            );
        }
        summary.push((lens, best));
    }

    println!("#");
    println!("# fib(30), best of {RUNS}, ns per call");
    println!("# {:<32} {:>10} {:>10} {:>10}", "lens", "plain", "off", "call");
    for (lens, best) in &summary {
        println!(
            "# {lens:<32} {:>10.4} {:>10.4} {:>10.4}",
            best[0].1, best[1].1, best[2].1
        );
    }
}

/// Run one arm in its own process with the environment that arm needs, and
/// return (ns per call, bytes the arm spooled before cleanup).
fn one_run(caller: &Path, arm: &str, run: usize, spool_root: &Path) -> (f64, u64) {
    let dir = spool_root.join(format!(
        "sensorium-rt-bench-{}-{}-{arm}-{run}",
        std::process::id(),
        caller.parent().and_then(|p| p.file_name()).map_or_else(
            || "unknown".to_owned(),
            |p| p.to_string_lossy().into_owned()
        )
    ));
    let _ = std::fs::remove_dir_all(&dir);
    let mut cmd = Command::new(caller);
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
    let value = parse_kv(&line, "ns_per_call")
        .unwrap_or_else(|| panic!("arm {arm} run {run} printed {line:?}"));
    let bytes = spool_bytes(&dir);
    let _ = std::fs::remove_dir_all(&dir);
    (value, bytes)
}

fn parse_kv(line: &str, key: &str) -> Option<f64> {
    line.split_whitespace()
        .find_map(|t| t.strip_prefix(key)?.strip_prefix('='))
        .and_then(|v| v.parse().ok())
}

/// The dev-profile and release-profile `bench-caller` binaries, beside this one
/// under the same target directory.
fn find_callers() -> Result<Vec<PathBuf>, String> {
    let exe = std::env::current_exe().map_err(|e| format!("current_exe: {e}"))?;
    let target = exe
        .parent()
        .and_then(Path::parent)
        .ok_or_else(|| format!("cannot find the target dir from {}", exe.display()))?;
    let mut found = Vec::new();
    for profile_dir in ["debug", "release"] {
        let p = target.join(profile_dir).join("bench-caller");
        if p.is_file() {
            found.push(p);
        } else {
            return Err(format!(
                "{} is missing. Both lenses are required: run\n    \
                 cargo build && cargo build --release\nfirst.",
                p.display()
            ));
        }
    }
    Ok(found)
}

/// Ask the caller binary what it was compiled as, rather than assuming.
fn lens_of(caller: &Path) -> String {
    let out = Command::new(caller)
        .arg("--lens")
        .output()
        .unwrap_or_else(|e| panic!("asking {} for its lens: {e}", caller.display()));
    String::from_utf8_lossy(&out.stdout).trim().to_owned()
}

fn spool_bytes(dir: &Path) -> u64 {
    std::fs::read_dir(dir)
        .map(|rd| {
            rd.filter_map(Result::ok)
                .filter_map(|e| e.metadata().ok())
                .map(|m| m.len())
                .sum()
        })
        .unwrap_or(0)
}
