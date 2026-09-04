//! Spawn sites are named by the enclosing NAMED ITEM's file-local qualname
//! and a 1-based ordinal among the WRAPPED sites of that qualname, in source
//! order. A `Builder::spawn` between two of them is declared, and takes no
//! ordinal.

use std::fmt;
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

    // An associated const's initialiser is an expression inside an `impl`, and
    // the CONST is what names it -- the `impl` holds items, never expressions.
    pub const F: fn() = || {
        let h = std::thread::spawn(|| ());
        h.join().unwrap();
    };
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

// Two trait impls of one type, each with a `fmt`: the qualname names the SELF
// TYPE and never the trait, so the twins share it and their ordinals continue
// across them in source order (plan decision N6-iv).
impl fmt::Display for T {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        std::thread::spawn(|| ()).join().unwrap();
        write!(f, "T")
    }
}

impl fmt::Debug for T {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        std::thread::spawn(|| ()).join().unwrap();
        write!(f, "T!")
    }
}

pub static F: fn() = || {
    let h = std::thread::spawn(|| ());
    h.join().unwrap();
};

pub const G: fn() = || {
    let h = std::thread::spawn(|| ());
    h.join().unwrap();
};

pub static TABLE: &[(&str, fn())] = &[("a", || {
    let h = std::thread::spawn(|| ());
    h.join().unwrap();
})];

pub mod m {
    pub static H: fn() = || {
        let h = std::thread::spawn(|| ());
        h.join().unwrap();
    };
}

pub mod tests {
    #[test]
    fn t() {
        let h = std::thread::spawn(|| 128u8);
        assert_eq!(h.join().unwrap(), 128u8);
    }
}
