//! `let _ = <value expression>` is the third written sink; `let _ = <place
//! expression>` is not a sink at all and is left alone.

fn one() -> Result<u8, String> {
    Ok(1)
}

pub fn discarded() {
    let _ = one();
}

/// A literal is not a place either, so it is wrapped: the transformer cannot
/// see types, and the runtime ladder writes nothing for one.
pub fn literal() {
    let _ = 1;
}

/// Places: a path, a field and a deref. None is wrapped, and none is declared.
pub fn places(r: Result<u8, String>, h: &Holder, p: &u8) {
    let _ = r;
    let _ = h.n;
    let _ = *p;
}

pub struct Holder {
    pub n: u8,
}

/// A typed `let _: T = ..` is a different spelling the design does not name,
/// and is left alone rather than guessed at.
pub fn typed() {
    let _: Result<u8, String> = one();
}

/// A `?` inside the value: two wraps, the `let` one outside.
pub fn both() -> Result<(), String> {
    let _ = Ok::<u8, String>(one()?);
    Ok(())
}
