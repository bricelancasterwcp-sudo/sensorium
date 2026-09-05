//! `if let Err(..)` bodies are classified exactly as `Err(..) =>` arms are
//! (design R2). The `else` branch is not an `Err` body and is untouched.

fn one() -> Result<u8, String> {
    Ok(1)
}

fn note(_e: &String) {}

/// A bound pattern, HANDLED: the name is only borrowed.
pub fn bound() {
    if let Err(e) = one() {
        note(&e);
    }
}

/// An unbound pattern with an `else`: the `else` branch gets nothing.
pub fn unbound() -> u8 {
    if let Err(_) = one() {
        0
    } else {
        1
    }
}

/// A bound pattern that PROPAGATES: `return Err(..)` in the body.
pub fn propagating() -> Result<u8, String> {
    if let Err(e) = one() {
        return Err(e);
    }
    Ok(0)
}
