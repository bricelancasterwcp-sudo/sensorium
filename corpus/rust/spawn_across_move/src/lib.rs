//! Rust-only case: the function that spawns the worker MOVES to another file
//! between the two runs (a cargo feature selects which file compiles), and
//! nothing else changes. The planted truth is about the INSTRUMENT: a spawned
//! task's name is `<parent> :: spawn@<fn qualname>#<k>`, which a move does not
//! change, so `diff --ignore-moves` pairs the worker across the move while a
//! plain `diff` sees the move.
#[cfg(not(feature = "moved"))]
mod worker;
#[cfg(feature = "moved")]
#[path = "worker_moved.rs"]
mod worker;

pub fn apply(balance: u32, delta: u32) -> u32 { balance + delta }

#[cfg(test)]
mod tests {
    #[test]
    fn the_worker_is_named_across_a_move() {
        assert_eq!(crate::worker::start(5), 5);
    }
}
