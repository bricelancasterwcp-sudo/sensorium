//! Spawn sites are named by the enclosing fn ITEM's file-local qualname and a
//! 1-based ordinal among the WRAPPED sites of that qualname, in source order.
//! A `Builder::spawn` between two of them is declared, and takes no ordinal.

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

pub mod tests {
    #[test]
    fn t() {@G(13)
        let h = @C(@A(tests::t#1)|| 128u8);
        assert_eq!(h.join().unwrap(), 128u8);
    }
}@U
