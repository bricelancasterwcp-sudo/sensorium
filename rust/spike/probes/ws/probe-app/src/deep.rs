//! A non-`mod.rs` file module. Rust 2018: its children live in `deep/`, NOT
//! beside this file. A walker that gets this wrong reaches nothing here.

mod inner;

pub fn deep_marker() -> &'static str {
    inner::inner_marker()
}
