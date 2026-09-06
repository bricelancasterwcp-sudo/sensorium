//! A focused fn whose arms an `Err(..) =>` probe also lands in. Two wraps meet
//! on the same bytes of a bare-expression arm body -- the LINE arm-entry wrap
//! (amendment A1) and the err-flow arm probe's -- and the `Kind`/`seq` order
//! has to nest them, not interleave them. `oracle.rs` compiles the result.
@W
pub fn handled(r: Result<i32, String>) -> i32 {@G(7)@N(8,r)
    @R(7)match r {
        Ok(v) => { @N(9,v) v },
        Err(e) => {@N(10,e)@P(12,HOW_ARM_HANDLED,e)
            eprintln!("{e}");@N(11)
            0
        }
    }@E
}

pub fn bare(r: Result<i32, String>) -> i32 {@G(13)@N(14,r)
    @R(13)match r {
        Ok(v) => { @N(15,v) v },
        Err(e) => { @N(16,e) { @P(17,HOW_ARM_AMBIGUOUS,e) e.len() as i32 } },
    }@E
}@U
