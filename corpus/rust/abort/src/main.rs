//! Seeded bug: the compaction worker dies by abort() in the middle of a
//! frame, and the supervisor reads the child's exit CODE -- which a
//! signal death does not have -- so `None` is treated as "nothing to
//! report" and the run is declared finished.
//!
//! Rust-only case. Two processes, one invocation: the parent's trace links
//! the child it spawned, and the child's trace is the record of a process
//! nobody waited for.
//!
//! The abort is a real SIGABRT, so a box whose `ulimit -c` is permissive
//! writes a core file for it -- into the child's working directory, or
//! wherever `kernel.core_pattern` sends it, which the corpus cannot reach.
//! The child lowers its OWN core limit to zero before aborting (below), so
//! the crash this case is ABOUT leaves nothing behind but the trace. In the
//! case and not in the harness: 63 cases run through that harness and one
//! of them aborts, and a sweep there would be a rule about every case
//! written for the sake of this one.

/// `struct rlimit`, and the one constant naming the resource. Declared
/// against libc directly because a corpus crate takes no dependencies --
/// `rlim_t` is `u64` and `RLIMIT_CORE` is 4 on Linux and on macOS -- and
/// because `setrlimit` returns a plain `int`: nothing here puts an `Err`
/// into a trace whose whole subject is what the recorder saw of a crash.
#[cfg(unix)]
#[repr(C)]
struct RLimit {
    rlim_cur: u64,
    rlim_max: u64,
}

#[cfg(unix)]
const RLIMIT_CORE: i32 = 4;

#[cfg(unix)]
extern "C" {
    fn setrlimit(resource: i32, rlim: *const RLimit) -> i32;
}

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
        // Lowering a limit needs no privilege, and this process is about to
        // die: setting the HARD limit too costs nothing it will live to
        // regret. Inline rather than in a function of its own -- a function
        // here would be instrumented, and the child's trace is read for
        // exactly which of its frames were left open.
        #[cfg(unix)]
        unsafe {
            setrlimit(RLIMIT_CORE, &RLimit { rlim_cur: 0, rlim_max: 0 });
        }
        worker();
        return;
    }
    let code = supervise();
    println!("compaction finished: {code:?}");
}
