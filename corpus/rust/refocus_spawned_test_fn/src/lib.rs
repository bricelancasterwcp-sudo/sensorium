//! Rust-only case: a thread the PROGRAM started, entering through a
//! function libtest also runs as a test of its own.
//!
//! Nothing here is buggy, and both tests pass. The planted truth is about
//! the INSTRUMENT. `#[test] fn` is an ordinary function to rustc, so a test
//! can spawn a thread onto one -- and the spawned thread's root frame then
//! carries the same `#[test]` mark as the thread libtest spawned. A rule
//! that read the mark alone subtracted BOTH as the recorder's own, reported
//! `no thread started besides the main one`, and GRANTED a refocus licence
//! over a thread the program started. What tells the two apart is a fact
//! the recording already holds: the runtime names a workspace spawn at its
//! site, so one task is `tests::spawns_a_marked_fn` and the other is
//! `tests::spawns_a_marked_fn :: spawn@tests::spawns_a_marked_fn#1`.

pub fn work() -> u32 {
    7
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn helper_test() {
        assert_eq!(work(), 7);
    }

    #[test]
    fn spawns_a_marked_fn() {
        std::thread::spawn(|| helper_test()).join().expect("joined");
    }
}
