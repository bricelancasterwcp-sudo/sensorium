//! A program whose path is decided by a file it wrote itself, so its second
//! execution is a DIFFERENT execution -- and `refocus` says so instead of
//! answering the question it was asked.
//!
//! The first run finds no `refocus_marker` beside `Cargo.toml`, writes one,
//! and calls `first_path`. The re-run that `sensorium refocus` launches from
//! that same workspace root finds the marker and calls `other` instead. The
//! CALL sequences part at their first step, so the verdict is DIVERGED, and
//! the value the deeper capture recorded belongs to the re-run alone.

const MARKER: &str = "refocus_marker";

fn first_path() -> u32 {
    1
}

fn other() -> u32 {
    2
}

fn main() {
    let seen = std::path::Path::new(MARKER).exists();
    if seen {
        println!("second: {}", other());
    } else {
        std::fs::write(MARKER, b"1").expect("write the marker");
        println!("first: {}", first_path());
    }
}
