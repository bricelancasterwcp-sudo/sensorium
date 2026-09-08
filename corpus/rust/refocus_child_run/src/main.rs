//! The refocus loop over an invocation that records TWO processes.
//!
//! `main` spawns this same binary again as a worker and waits for it, so
//! the driver instruments both and the re-run leaves two traces carrying
//! `refocus_of` -- the process the reader recorded and the child it
//! started. Only one of them is the pair; the other is a child run, which
//! is named beside the verdict rather than counted against it (design
//! 2026-09-07 §3, ruling R2).
//!
//! No seeded bug here: what this case pins is which trace a verdict is
//! about, so the program is deliberately dull and deterministic.

fn tally(items: u32) -> u32 {
    items + 1
}

fn worker() -> u32 {
    tally(2)
}

fn supervise() -> Option<i32> {
    let exe = std::env::current_exe().expect("current_exe");
    std::process::Command::new(exe)
        .arg("--worker")
        .status()
        .expect("spawn the worker")
        .code()
}

fn main() {
    if std::env::args().any(|a| a == "--worker") {
        worker();
        return;
    }
    let code = supervise();
    println!("worker finished: {code:?}");
}
