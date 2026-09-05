//! The blind spot, planted so it cannot drift: a GENUINE swallow in a frame
//! that then fails for an unrelated reason.
//!
//! `run` throws away the cleanup error with `let _ =` -- that is a real
//! swallow -- and then fails on its own work. The chain machine sees the
//! sink and then sees the holder close `err`, and it cannot tell "absorbed,
//! then failed anyway" from "the absorption is what made it fail". So the
//! verdict is ambiguous and the swallow goes unreported. That under-claim is
//! the designed behaviour: a false accusation is the one failure this
//! command must never produce.

fn cleanup(path: &str) -> Result<(), String> {
    Err(format!("cleanup {path} failed"))
}

fn work(n: u32) -> Result<u32, String> {
    Err(format!("work {n} failed"))
}

fn run(n: u32) -> Result<u32, String> {
    // BUG: a cleanup failure is dropped without a word.
    let _ = cleanup("scratch.tmp");
    let value = work(n)?;
    Ok(value)
}

fn main() {
    println!("outcome: {:?}", run(7));
}
