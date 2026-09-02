//! The probe workspace's application library.
//!
//! Every module shape here exists to be walked by the wrapper's module-tree
//! resolver, not because the probe needs the code.

/// A NON-`mod.rs` file module: its own children live under `src/deep/`.
pub mod deep;

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

/// `#[cfg_attr(..., path = ...)]`: the wrapper does NOT evaluate cfg, so it
/// cannot know which file this is. It reports the module unreached and leaves
/// whatever file rustc picks unrewritten (and symlinked in the mirror).
#[cfg_attr(windows, path = "maybe_windows.rs")]
pub mod maybe;

/// The process id, straight from libc: the probe's own libc use.
pub fn probe_pid() -> i32 {
    // SAFETY: `getpid` takes no arguments and cannot fail.
    unsafe { libc::getpid() }
}

pub fn describe() -> String {
    format!(
        "{}+{}+{}+{}",
        probe_core::add(1, 2),
        probe_ext::ext_marker(),
        deep::deep_marker(),
        nested::nested_marker(),
    )
}

pub fn work(n: u32) -> u32 {
    let mut c = probe_core::Counter::new();
    for _ in 0..n {
        c.bump();
    }
    probe_ext::ext_double(c.bump())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn describe_describes() {
        assert_eq!(describe(), "3+ext+deep+nested");
    }

    #[test]
    fn work_works() {
        assert_eq!(work(2), 6);
    }

    #[test]
    fn pid_is_positive() {
        assert!(probe_pid() > 0);
    }

    #[test]
    fn unreached_module_still_compiles() {
        assert_eq!(maybe::maybe_marker(), "maybe");
    }
}
