//! Rust-only case: the work under test does not happen on the test's own
//! thread. The test spawns a worker, the worker takes the ledger's lock and
//! does every instrumented call while holding it, and the test thread does
//! nothing but join.
//!
//! Nothing here is buggy. The planted truth is about the INSTRUMENT: a
//! thread spawned by workspace code is a named unit of work, named for the
//! test that spawned it and the source line that spawned it -- so the work
//! can be found and compared by a name, not by a thread number that means
//! nothing on the next run.

use std::sync::{Arc, Mutex};

pub fn apply(balance: u32, delta: u32) -> u32 {
    balance + delta
}

pub fn drain(ledger: &Arc<Mutex<u32>>, delta: u32) -> u32 {
    let mut held = ledger.lock().expect("ledger poisoned");
    *held = apply(*held, delta);
    *held
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_worker_holds_the_ledger() {
        let ledger = Arc::new(Mutex::new(0u32));
        let worker = {
            let ledger = Arc::clone(&ledger);
            std::thread::spawn(move || drain(&ledger, 7))
        };
        assert_eq!(worker.join().expect("worker joined"), 7);
    }
}
