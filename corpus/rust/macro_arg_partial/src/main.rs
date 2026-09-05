//! The instrument's own limit, planted so it cannot drift: a `?` written
//! inside a macro invocation's TOKENS cannot be wrapped by the transformer,
//! so nothing is recorded when it fires.
//!
//! Both functions below fail the same way on the same input. `margin`'s `?`
//! is reachable and leaves a record; `banner`'s sits inside `format!` and
//! leaves none. The tool must DECLARE the second site rather than report one
//! failure and leave the reader to think that was all of them.

fn width(raw: &str) -> Result<u32, String> {
    raw.parse::<u32>()
        .map_err(|_| format!("width {raw:?} is not a number"))
}

fn margin(raw: &str) -> Result<u32, String> {
    let w = width(raw)?;
    Ok(w + 2)
}

fn banner(raw: &str) -> Result<String, String> {
    Ok(format!("[{:>4}]", width(raw)?))
}

fn main() {
    let m = margin("wide");
    let b = banner("tall");
    println!("{m:?} {b:?}");
}
