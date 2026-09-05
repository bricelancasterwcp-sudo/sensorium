//! A sink whose receiver is a PLACE expression is wrapped like any other: all
//! four written sinks take `self` BY VALUE, so the call moves the receiver
//! exactly as the wrap does, and an E0507 the wrap could cause is one the sink
//! caused already (design R2 as amended 2026-09-04).
//!
//! `let _ = <place>` is the one shape still left alone -- `_` does not bind, so
//! that statement moves nothing, drops nothing and absorbs no error.

pub struct Holder {
    pub last: Result<u8, u8>,
}

static REF: Result<u8, u8> = Ok(1);

fn returns_ref_result() -> &'static Result<u8, u8> {
    &REF
}

impl Holder {
    /// A field behind a shared borrow. `Result<u8, u8>` is `Copy`, so the
    /// original copies the receiver and so does the wrap.
    pub fn defaulted(&self) -> u8 {
        self.last.unwrap_or(0)
    }
}

pub fn indexed(v: &[Result<u8, u8>]) -> u8 {
    v[0].unwrap_or(0)
}

/// The parentheses are the SOURCE's own, and the wrap goes INSIDE them:
/// `match (*p) { .. }` is `unused_parens`.
pub fn dereferenced(p: &Result<u8, u8>) -> u8 {
    (*p).unwrap_or(0)
}

pub fn a_local(r: Result<u8, u8>) -> u8 {
    r.unwrap_or(0)
}

/// Design R16's named blind spot: the operand's type is `&Result<T, E>`, so
/// the runtime ladder falls to its fallback and records nothing at all. The
/// wrap is still placed, and still compiles, which is what this pins.
pub fn ref_result() {
    let _ = returns_ref_result();
}

/// `let _ = <place>` is left alone entirely, and is not declared either.
pub fn place_let(r: Result<u8, u8>) {
    let _ = r;
}
