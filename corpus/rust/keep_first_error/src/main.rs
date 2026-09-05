//! A frame that holds TWO different errors and returns the FIRST.
//!
//! `pick` calls `first` (fails with `Refused(1)`), then `second` (fails with
//! `Refused(2)`), and returns the first error it saw -- the keep-first-error
//! shape. The chain machine used to hand the exit hop to the INNERMOST held
//! chain (the second error's), labelling it `translated` because the text
//! changed, and left the first error's chain without its hop. Since the
//! 2026-09-05 borrow-repair slice the hop goes to the chain whose text the
//! RETURN carries.
//!
//! Seeded bug: `main` logs the failure and carries on, so the process exits 0
//! with `ok: 0` and the refusal is on stderr only -- a swallow of the FIRST
//! error, which is the one the caller was handed. The second error never left
//! `pick`: its chain reads ambiguous, never swallowed, and never `translated`.

#[derive(Debug)]
struct Refused(u32);

fn first() -> Result<u32, Refused> {
    Err(Refused(1))
}

fn second() -> Result<u32, Refused> {
    Err(Refused(2))
}

/// Holds both errors, returns the first: the keep-first-error shape.
fn pick() -> Result<u32, Refused> {
    let a = first();
    let b = second();
    if a.is_err() {
        return a;
    }
    b
}

fn main() {
    let value = match pick() {
        Ok(v) => v,
        // BUG: printed, then forgotten -- the first refusal is swallowed here.
        Err(e) => {
            eprintln!("pick failed: {e:?}");
            0
        }
    };
    println!("ok: {value}");
}
