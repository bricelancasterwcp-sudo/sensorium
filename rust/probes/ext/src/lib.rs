//! Outside the probe workspace directory, therefore not a workspace member,
//! therefore never handed to `RUSTC_WORKSPACE_WRAPPER`. This crate is the
//! control for `non_member_ext_is_never_wrapped`: if a manifest ever appears
//! for it, the wrapper is reaching past the workspace cargo gave it.

/// Deliberately an ordinary fn item: if this crate were wrapped it would be
/// instrumented, and the manifest would say so.
pub fn ext_marker() -> &'static str {
    "ext"
}

pub fn ext_double(n: u32) -> u32 {
    n * 2
}
