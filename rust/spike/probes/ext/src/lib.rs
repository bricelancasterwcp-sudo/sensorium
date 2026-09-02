//! Outside the probe workspace directory, therefore not a workspace member,
//! therefore never handed to `RUSTC_WORKSPACE_WRAPPER`. E8's control: if a
//! manifest ever appears for this crate, the wrapper is reaching too far.

/// Deliberately an ordinary fn item: if this crate were wrapped it would be
/// instrumented, and the manifest would say so.
pub fn ext_marker() -> &'static str {
    "ext"
}

pub fn ext_double(n: u32) -> u32 {
    n * 2
}
