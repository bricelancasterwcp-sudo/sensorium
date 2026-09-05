//! The two spellings the transformer rewrites, so the child thread has a name.
@W
use std::thread;

pub fn fully_qualified() -> u8 {@G(7)
    let h = @C(@A(fully_qualified#1)|| 1u8);
    @R(7)h.join().unwrap()@E
}

pub fn imported() -> u8 {@G(8)
    @R(8)@C(@I(thread::spawn;imported#1)|| 2u8).join().unwrap()@E
}@U
