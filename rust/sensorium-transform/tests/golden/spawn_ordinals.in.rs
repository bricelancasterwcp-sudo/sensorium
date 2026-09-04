//! Spawn sites are named by the enclosing fn ITEM's file-local qualname and a
//! 1-based ordinal among the WRAPPED sites of that qualname, in source order.
//! A `Builder::spawn` between two of them is declared, and takes no ordinal.

use std::thread;

pub struct T;

pub struct X;

pub fn a() -> u8 {
    let first = std::thread::spawn(|| 1u8);
    let declared = thread::Builder::new()
        .spawn(|| 2u8)
        .expect("spawn");
    let second = std::thread::spawn(|| 4u8);
    first.join().unwrap() + declared.join().unwrap() + second.join().unwrap()
}

impl T {
    pub fn m() -> u8 {
        thread::spawn(|| 8u8).join().unwrap()
    }
}

pub fn outer() -> u8 {
    fn inner() -> u8 {
        std::thread::spawn(|| 16u8).join().unwrap()
    }
    inner()
}

pub fn c() -> u8 {
    let f = || std::thread::spawn(|| 32u8);
    f().join().unwrap()
}

impl Drop for X {
    fn drop(&mut self) {
        let h = std::thread::spawn(|| 64u8);
        assert_eq!(h.join().unwrap(), 64u8);
    }
}

pub mod tests {
    #[test]
    fn t() {
        let h = std::thread::spawn(|| 128u8);
        assert_eq!(h.join().unwrap(), 128u8);
    }
}
