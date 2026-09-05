//! A sink whose receiver is a PLACE expression is wrapped like any other: all
//! four written sinks take `self` BY VALUE, so the call moves the receiver
//! exactly as the wrap does, and an E0507 the wrap could cause is one the sink
//! caused already (design R2 as amended 2026-09-04).
//!
//! `let _ = <place>` is the one shape still left alone -- `_` does not bind, so
//! that statement moves nothing, drops nothing and absorbs no error.
@W
pub struct Holder {
    pub last: Result<u8, u8>,
}

static REF: Result<u8, u8> = Ok(1);

fn returns_ref_result() -> &'static Result<u8, u8> {@G(7)
    @R(7)&REF@E
}

impl Holder {
    /// A field behind a shared borrow. `Result<u8, u8>` is `Copy`, so the
    /// original copies the receiver and so does the wrap.
    pub fn defaulted(&self) -> u8 {@G(8)
        @R(8)@S(9,HOW_SINK_UNWRAP_OR)self.last@SE.unwrap_or(0)@E
    }
}

pub fn indexed(v: &[Result<u8, u8>]) -> u8 {@G(10)
    @R(10)@S(11,HOW_SINK_UNWRAP_OR)v[0]@SE.unwrap_or(0)@E
}

/// The parentheses are the SOURCE's own, and the wrap goes INSIDE them:
/// `match (*p) { .. }` is `unused_parens`.
pub fn dereferenced(p: &Result<u8, u8>) -> u8 {@G(12)
    @R(12)(@S(13,HOW_SINK_UNWRAP_OR)*p@SE).unwrap_or(0)@E
}

pub fn a_local(r: Result<u8, u8>) -> u8 {@G(14)
    @R(14)@S(15,HOW_SINK_UNWRAP_OR)r@SE.unwrap_or(0)@E
}

/// Design R16's named blind spot: the operand's type is `&Result<T, E>`, so
/// the runtime ladder falls to its fallback and records nothing at all. The
/// wrap is still placed, and still compiles, which is what this pins.
pub fn ref_result() {@G(16)
    let _ = @L(17)returns_ref_result()@LE;
}

/// `let _ = <place>` is left alone entirely, and is not declared either.
pub fn place_let(r: Result<u8, u8>) {@G(18)
    let _ = r;
}@U
