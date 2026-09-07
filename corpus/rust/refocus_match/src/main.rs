//! The refocus loop, at its simplest: a deterministic `fill` recorded at
//! tier `call`, then re-recorded under `--focus fill` by `sensorium
//! refocus` -- the same crate, the same command, one flag deeper.
//!
//! The original holds no LINE row at all (`line=no`), so "what was `b` when
//! the statement wrote it" has no answer in it. The re-run answers it, and
//! the MATCH is what makes that answer a fact about the run that was asked
//! about rather than about a second, unrelated execution.

fn fill() -> String {
    let a = 1;
    let b = a + 1;
    let s = format!("{b}");
    s
}

fn main() {
    println!("filled: {}", fill());
}
