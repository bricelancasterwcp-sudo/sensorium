//! The limit `rust/HONESTY.md` §1 names, planted so it cannot drift: a
//! GENERIC return type reads `ok` even when the value is an `Err`.
//!
//! The capture probe is specialised where the fragment sits -- inside
//! `measured`, where `T` is not known to be a `Result` -- so `measured`'s
//! frame closes `ok` although it handed back an `Err`. `direct` returns the
//! same value from a concrete signature and closes `err`. Same error, same
//! caller, two different readings, and the difference is the SIGNATURE the
//! error travelled through, not anything the program did.

#[derive(Debug)]
struct Missing(u32);

fn fetch(id: u32) -> Result<u32, Missing> {
    Err(Missing(id))
}

fn measured<T: std::fmt::Debug>(f: impl FnOnce() -> T) -> T {
    f()
}

fn direct(id: u32) -> Result<u32, Missing> {
    fetch(id)
}

fn main() {
    let through_generic = measured(|| fetch(7));
    let through_concrete = direct(8);
    println!("{through_generic:?} {through_concrete:?}");
}
