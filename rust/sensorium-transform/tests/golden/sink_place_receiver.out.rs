//! Sinks whose receiver is a PLACE expression are declared, not wrapped
//! (design R2), and `let _ = <place>` is neither: `_` does not bind, so that
//! statement moves nothing, drops nothing and absorbs no error.
@W
pub struct Holder {
    pub last: Result<u8, u8>,
}

static REF: Result<u8, u8> = Ok(1);

fn returns_ref_result() -> &'static Result<u8, u8> {@G(7)
    @R(7)&REF@E
}

impl Holder {
    /// A field behind a shared borrow. `Result<u8, u8>` is `Copy`, so the sink
    /// compiles -- and the receiver is declared rather than wrapped all the
    /// same.
    pub fn defaulted(&self) -> u8 {@G(8)
        @R(8)self.last.unwrap_or(0)@E
    }
}

pub fn indexed(v: &[Result<u8, u8>]) -> u8 {@G(9)
    @R(9)v[0].unwrap_or(0)@E
}

pub fn dereferenced(p: &Result<u8, u8>) -> u8 {@G(10)
    @R(10)(*p).unwrap_or(0)@E
}

pub fn a_local(r: Result<u8, u8>) -> u8 {@G(11)
    @R(11)r.unwrap_or(0)@E
}

/// Design R16's named blind spot: the operand's type is `&Result<T, E>`, so
/// the runtime ladder falls to its fallback and records nothing at all. The
/// wrap is still placed, and still compiles, which is what this pins.
pub fn ref_result() {@G(12)
    let _ = @L(13)returns_ref_result()@LE;
}

/// `let _ = <place>` is left alone entirely, and is not declared either.
pub fn place_let(r: Result<u8, u8>) {@G(14)
    let _ = r;
}@U
