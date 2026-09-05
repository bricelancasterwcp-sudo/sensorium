//! `if let Err(..)` bodies are classified exactly as `Err(..) =>` arms are
//! (design R2). The `else` branch is not an `Err` body and is untouched.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

fn note(_e: &String) {@G(8)}

/// A bound pattern, HANDLED: the name is only borrowed.
pub fn bound() {@G(9)
    if let Err(e) = one() {@P(10,HOW_ARM_HANDLED,e)
        note(&e);
    }
}

/// An unbound pattern with an `else`: the `else` branch gets nothing.
pub fn unbound() -> u8 {@G(11)
    @R(11)if let Err(_) = one() {@P(12,HOW_ARM_HANDLED)
        0
    } else {
        1
    }@E
}

/// A bound pattern that PROPAGATES: `return Err(..)` in the body.
pub fn propagating() -> Result<u8, String> {@G(13)
    if let Err(e) = one() {@P(14,HOW_ARM_PROPAGATE,e)
        return @R(13)Err(e)@E;
    }
    @R(13)Ok(0)@E
}@U
