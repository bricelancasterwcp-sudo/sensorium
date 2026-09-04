//! The two spellings the transformer rewrites, so the child thread has a name.

use std::thread;

pub fn fully_qualified() -> u8 {
    let h = std::thread::spawn(|| 1u8);
    h.join().unwrap()
}

pub fn imported() -> u8 {
    thread::spawn(|| 2u8).join().unwrap()
}
