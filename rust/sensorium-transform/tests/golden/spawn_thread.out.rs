//! The two spellings the transformer rewrites, so the child thread has a name.

use std::thread;

pub fn fully_qualified() -> u8 {@G(7)
    let h = @C(@A(src/lib.rs:6)|| 1u8);
    @R(7)h.join().unwrap()@E
}

pub fn imported() -> u8 {@G(8)
    @R(8)@C(@I(thread::spawn;src/lib.rs:11)|| 2u8).join().unwrap()@E
}@U
