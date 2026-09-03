//! The probe workspace's application library.
//!
//! Every module shape here exists to be walked by the wrapper's module-tree
//! resolver, and every free fn below exists to be the *body* of one mechanics
//! check: a panic two frames deep, a panic caught and returned from, a thread
//! that blocks past the end of the process, and a frame the process dies
//! inside.

/// A NON-`mod.rs` file module: its own children live under `src/deep/`.
pub mod deep;

/// A module whose FIRST item is a `use` of an instrumented dependency —
/// bloomery's shape, and the one that needs `-L dependency` rather than
/// `--extern` alone. See `tally.rs`.
pub mod tally;

/// An inline module. Walked in place; it is not a file. Its `#[path]` child
/// resolves under `src/nested/`, because the path base for a `#[path]` inside
/// an inline module in a mod-rs file is the file's directory plus the inline
/// module components.
pub mod nested {
    #[path = "nested_child.rs"]
    pub mod child;

    pub fn nested_marker() -> &'static str {
        "nested"
    }
}

/// `#[cfg_attr(..., path = ...)]`: the wrapper does NOT evaluate `cfg`, so it
/// cannot know which file this is. It reports the module unreached and leaves
/// whatever file rustc picks unrewritten.
#[cfg_attr(windows, path = "maybe_windows.rs")]
pub mod maybe;

/// This process's id. `spawn_bin.rs` and `abort_child.rs` are what actually
/// exercise child processes; this is here so the lib unit has one fn whose
/// value is decided by the OS rather than by the source.
#[must_use]
pub fn probe_pid() -> u32 {
    std::process::id()
}

#[must_use]
pub fn describe() -> String {
    format!(
        "{}+{}+{}+{}",
        probe_core::add(1, 2),
        probe_ext::ext_marker(),
        deep::deep_marker(),
        nested::nested_marker(),
    )
}

/// Instrumented work with a value at the end of it: several CALL/RETURN pairs
/// and one captured return.
#[must_use]
pub fn work(n: u32) -> u32 {
    let mut c = probe_core::Counter::new();
    for _ in 0..n {
        c.bump();
    }
    probe_ext::ext_double(c.bump())
}

/// The outer of the two frames a `#[should_panic]` test panics inside. The
/// panic is raised in [`panic_inner`], so the trace has to show TWO frames
/// closed by `unwind`, not one.
pub fn panic_outer(label: &str) -> u32 {
    let doubled = work(1);
    panic_inner(label) + doubled
}

/// Where the panic actually happens.
pub fn panic_inner(label: &str) -> u32 {
    if label.is_empty() {
        return 0;
    }
    panic!("probe nested panic: {label}");
}

/// A panic raised and caught inside one instrumented frame. The frame that
/// caught it closes `return` with an `ok` outcome, beside the inner frame that
/// closed `unwind` — the pair is what says the two are told apart.
///
/// # Panics
/// Never: the inner panic is caught here.
#[must_use]
pub fn catch_inner_panic(label: &str) -> u32 {
    // 7 is what a CAUGHT panic returns, and it is the value the trace check
    // reads back off this frame's RETURN: an `ok` outcome carrying 7 beside an
    // inner frame that closed `unwind` is what tells the two apart.
    std::panic::catch_unwind(|| panic_inner(label)).unwrap_or(7)
}

/// Instrumented work, a handshake, and then a wait that never ends.
///
/// The thread that calls this is still alive when the process exits, so the
/// converter lists it in `live_threads` while its records — written before the
/// block — are all on disk. `ready` is what makes the check deterministic
/// rather than timed: the caller knows the work is done because the worker
/// said so, not because enough milliseconds passed.
pub fn work_then_block(
    rx: &std::sync::mpsc::Receiver<()>,
    ready: &std::sync::mpsc::Sender<u32>,
) -> u32 {
    let done = work(2);
    ready.send(done).ok();
    // The sender of `rx` is leaked by the caller, so this never returns
    // Disconnected, and this thread never ends.
    let _ = rx.recv();
    done
}

/// Die inside an open frame. `std::process::abort` is one of the calls the
/// transformer treats as diverging, so this fn's exit is never wrapped and its
/// CALL has no RETURN: the open frame IS the record of the death
/// (`rust/HONESTY.md` §5).
pub fn abort_mid_frame() -> ! {
    let n = work(1);
    println!("app-bin: aborting after work(1) = {n}");
    std::process::abort()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn describe_describes() {
        assert_eq!(describe(), "3+ext+deep+nested");
        assert_eq!(nested::child::child_marker(), "child");
    }

    #[test]
    fn work_works() {
        assert_eq!(work(2), 6);
    }

    #[test]
    fn tallying_goes_through_an_instrumented_dependencys_type() {
        assert_eq!(tally::tally(2), 3);
    }

    #[test]
    fn pid_is_positive() {
        assert!(probe_pid() > 0);
    }

    #[test]
    fn unreached_module_still_compiles() {
        assert_eq!(maybe::maybe_marker(), "maybe");
    }

    /// A `Result`-returning test fn: libtest accepts one, and the transformer
    /// has to wrap its `Ok(())` tail like any other exit operand.
    #[test]
    fn small_numbers_parse() -> Result<(), String> {
        let n = probe_core::values::parse_small("7")?;
        assert_eq!(n, 7);
        Ok(())
    }

    #[test]
    fn undebuggable_returns_are_still_values() {
        assert_eq!(probe_core::values::make_opaque().tag, 3);
        let _prickly = probe_core::values::make_prickly();
    }
}
