//! One job: make a change to the runtime's source rebuild this binary.
//!
//! `src/rt_src.rs` embeds `sensorium-rt`'s sources with `include_str!`, and
//! rustc's dep-info already lists the files it read, so an EDIT to one of them
//! rebuilds the driver without any help. What dep-info cannot see is a file
//! that does not exist yet: add `sensorium-rt/src/new_module.rs` and declare it
//! in the runtime's crate root, and nothing about this crate has changed as far
//! as cargo is concerned — the driver keeps its old tool hash, keeps writing
//! out the old file list, and its bare `rustc` line fails to find the new
//! module in somebody else's workspace.
//!
//! Watching the DIRECTORY closes that: a new file in it is a change to it.
//! (`rt_src::tests::every_module_the_crate_root_declares_is_embedded` is the
//! check that then fails, loudly, here rather than in a target workspace.)

fn main() {
    println!("cargo:rerun-if-changed=../sensorium-rt/src");
    println!("cargo:rerun-if-changed=build.rs");
}
