//! `let _ = <value expression>` is the third written sink; `let _ = <place
//! expression>` is not a sink at all and is left alone.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

pub fn discarded() {@G(8)
    let _ = @L(9)one()@LE;
}

/// A literal is not a place either, so it is wrapped: the transformer cannot
/// see types, and the runtime ladder writes nothing for one.
pub fn literal() {@G(10)
    let _ = @L(11)1@LE;
}

/// Places: a path, a field and a deref. None is wrapped, and none is declared.
pub fn places(r: Result<u8, String>, h: &Holder, p: &u8) {@G(12)
    let _ = r;
    let _ = h.n;
    let _ = *p;
}

pub struct Holder {
    pub n: u8,
}

/// A typed `let _: T = ..` is a different spelling the design does not name,
/// and is left alone rather than guessed at.
pub fn typed() {@G(13)
    let _: Result<u8, String> = one();
}

/// A `?` inside the value: two wraps, the `let` one outside.
pub fn both() -> Result<(), String> {@G(14)
    let _ = @L(15)Ok::<u8, String>(@T(16)one()@TE?)@LE;
    @R(14)Ok(())@E
}@U
