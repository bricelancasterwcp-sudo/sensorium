//! The two spellings the transformer rewrites, so the child thread has a name.
@W
use std::thread;

pub fn fully_qualified() -> u8 {@G(7)
    let h = @C(@A(fully_qualified#1)|| 1u8);
    @R(7)h.join().unwrap()@E
}

pub fn imported() -> u8 {@G(8)
    @R(8)@C(@I(thread::spawn;imported#1)|| 2u8).join().unwrap()@E
}

/// `let _ = <spawn>`: the err wrap's `match ` opens on the byte the spawn
/// callee's REPLACED range starts at, and has to go in first.
pub fn discarded_handles() {@G(9)
    let _ = @L(10)@C(@A(discarded_handles#1)|| ())@LE;
    let _ = @L(11)@C(@I(thread::spawn;discarded_handles#2)|| ())@LE;
}@U
