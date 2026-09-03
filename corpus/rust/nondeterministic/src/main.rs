//! Seeded property, not a bug: this program's branch depends on state
//! OUTSIDE the process -- a counter file it reads and increments -- so no
//! rerun ever reproduces the previous execution.
//!
//! Ground truth: `sensorium diff` of the two recordings must report
//! DIVERGED, never MATCH. That is the CORRECT answer, not a flaw in this
//! case: the second run genuinely was a different execution, and this
//! recorder cannot replay state outside the process (`refocus` says so and
//! refuses, which is the same fact from the other side).
//!
//! Do NOT "fix" this into a random coin flip. A coin flip is the honest
//! illustration and a flaky corpus case: the diff would land on MATCH
//! roughly half the time. Here the verdict is guaranteed while the REASON
//! stays exactly the real one -- the harness copies the case into a fresh
//! temp dir per run, so the counter starts clean every time.

use std::fs;
use std::path::Path;

fn pick() -> bool {
    let counter = Path::new("run_count.txt");
    let n: u32 = fs::read_to_string(counter)
        .ok()
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or(0);
    fs::write(counter, (n + 1).to_string()).expect("write counter");
    n % 2 == 0
}

fn left() -> &'static str {
    "L"
}

fn right() -> &'static str {
    "R"
}

fn main() {
    let branch = if pick() { left() } else { right() };
    println!("{branch}");
}
