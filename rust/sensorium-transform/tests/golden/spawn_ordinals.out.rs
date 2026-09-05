//! Spawn sites are named by the enclosing NAMED ITEM's file-local qualname
//! and a 1-based ordinal among the WRAPPED sites of that qualname, in source
//! order. A `Builder::spawn` between two of them is declared, and takes no
//! ordinal.
@W
use std::fmt;
use std::thread;

pub struct T;

pub struct X;

pub fn a() -> u8 {@G(7)
    let first = @C(@A(a#1)|| 1u8);
    let declared = thread::Builder::new()
        .spawn(|| 2u8)
        .expect("spawn");
    let second = @C(@A(a#2)|| 4u8);
    @R(7)first.join().unwrap() + declared.join().unwrap() + second.join().unwrap()@E
}

impl T {
    pub fn m() -> u8 {@G(8)
        @R(8)@C(@I(thread::spawn;T::m#1)|| 8u8).join().unwrap()@E
    }

    // An associated const's initialiser is an expression inside an `impl`, and
    // the CONST is what names it -- the `impl` holds items, never expressions.
    pub const F: fn() = || {
        let h = @C(@A(T::F#1)|| ());
        h.join().unwrap();
    };
}

pub fn outer() -> u8 {@G(9)
    fn inner() -> u8 {@G(10)
        @R(10)@C(@A(outer::inner#1)|| 16u8).join().unwrap()@E
    }
    @R(9)inner()@E
}

pub fn c() -> u8 {@G(11)
    let f = || @C(@A(c#1)|| 32u8);
    @R(11)f().join().unwrap()@E
}

impl Drop for X {
    fn drop(&mut self) {@G(12)
        let h = @C(@A(X::drop#1)|| 64u8);
        assert_eq!(h.join().unwrap(), 64u8);
    }
}

// Two trait impls of one type, each with a `fmt`: the qualname names the SELF
// TYPE and never the trait, so the twins share it and their ordinals continue
// across them in source order (plan decision N6-iv).
impl fmt::Display for T {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {@G(13)
        @C(@A(T::fmt#1)|| ()).join().unwrap();
        @R(13)write!(f, "T")@E
    }
}

impl fmt::Debug for T {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {@G(14)
        @C(@A(T::fmt#2)|| ()).join().unwrap();
        @R(14)write!(f, "T!")@E
    }
}

pub static F: fn() = || {
    let h = @C(@A(F#1)|| ());
    h.join().unwrap();
};

pub const G: fn() = || {
    let h = @C(@A(G#1)|| ());
    h.join().unwrap();
};

pub static TABLE: &[(&str, fn())] = &[("a", || {
    let h = @C(@A(TABLE#1)|| ());
    h.join().unwrap();
})];

pub mod m {
    pub static H: fn() = || {
        let h = @C(@A(m::H#1)|| ());
        h.join().unwrap();
    };
}

pub mod tests {
    #[test]
    fn t() {@G(15)
        let h = @C(@A(tests::t#1)|| 128u8);
        assert_eq!(h.join().unwrap(), 128u8);
    }
}@U
