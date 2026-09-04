//! Reached through a `#[path]` inside an INLINE module, whose base directory
//! is `src/nested/`.

pub fn child_marker() -> &'static str {
    "child"
}
