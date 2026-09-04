//! A directory module: its children resolve beside `mod.rs`, not under a
//! `sub/sub/` directory.

mod leaf;

pub fn deep_value() -> u32 {
    leaf::leaf_value()
}
