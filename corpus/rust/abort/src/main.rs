//! Seeded bug: the compaction worker dies by abort() in the middle of a
//! frame, and the supervisor reads the child's exit CODE -- which a
//! signal death does not have -- so `None` is treated as "nothing to
//! report" and the run is declared finished.
//!
//! Rust-only case. Two processes, one invocation: the parent's trace links
//! the child it spawned, and the child's trace is the record of a process
//! nobody waited for.

fn checkpoint(step: u32) -> u32 {
    step + 1
}

fn compact(step: u32) -> u32 {
    if checkpoint(step) > 0 {
        // BUG: a corrupt page aborts the process mid-compaction, leaving
        // this frame -- and every frame under main -- open forever.
        std::process::abort();
    }
    step
}

fn worker() -> u32 {
    compact(1)
}

fn supervise() -> Option<i32> {
    let exe = std::env::current_exe().expect("current_exe");
    let status = std::process::Command::new(exe)
        .arg("--abort")
        .status()
        .expect("spawn the compaction worker");
    // BUG: a process killed by a signal has no exit code, so this is None
    // for a crash and the caller cannot tell it from a clean finish.
    status.code()
}

fn main() {
    if std::env::args().any(|a| a == "--abort") {
        worker();
        return;
    }
    let code = supervise();
    println!("compaction finished: {code:?}");
}
