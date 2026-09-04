//! Reached only through `#[path = "renamed_source.rs"]`. If the wrapper's walk
//! ignored `#[path]` this file would be reported unreached and left
//! unrewritten.

pub fn renamed_marker() -> &'static str {
    "renamed"
}
