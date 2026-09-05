//! The counterpart to `err_stored`, and the shape that separates the two:
//! an `Err(e) =>` arm whose body only FORMATS the error and carries on.
//!
//! `err_stored` moves the bound error out of the arm, so the program is
//! still holding it and this recording cannot say what it does with it
//! next. Here the arm borrows `e` to print it and then drops it: nothing
//! leaves the arm, the loop continues, and `charge` returns `Ok`. The
//! failure reached stderr and nowhere else, which is what a swallow is.
//!
//! Seeded bug: the first attempt is refused and the caller is told the
//! charge succeeded, at the second attempt's price. The refusal is on
//! stderr, where nothing correlates it with the value that was returned.

#[derive(Debug)]
struct Refused(u32);

fn attempt(n: u32) -> Result<u32, Refused> {
    if n == 1 {
        return Err(Refused(n));
    }
    Ok(n * 10)
}

fn charge(times: u32) -> Result<u32, Refused> {
    for n in 1..=times {
        match attempt(n) {
            Ok(v) => return Ok(v),
            // BUG: printed, then forgotten. The caller is told this
            // succeeded and never learns an attempt was refused.
            Err(e) => eprintln!("attempt failed: {e:?}"),
        }
    }
    Ok(0)
}

fn main() {
    println!("charged: {}", charge(2).unwrap_or(0));
}
