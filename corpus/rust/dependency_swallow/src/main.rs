//! Seeded bug: the scratch file is removed on a best-effort basis and the
//! "effort" half is never checked, so a removal that fails -- a permission,
//! a directory that is not there, a file another process is holding --
//! leaves the run reporting a clean finish.
//!
//! The error is born in the standard library, which this build did not
//! instrument, so there is no frame to attribute it to. The absorbing site
//! is still ours, and the verdict must say both: it was swallowed, and it
//! came from outside instrumented code.

use std::fs;

fn cleanup(path: &str) {
    let _ = fs::remove_file(path);
}

fn finish(path: &str) -> &'static str {
    cleanup(path);
    "clean"
}

fn main() {
    println!("scratch: {}", finish("scratch/never-created.tmp"));
}
