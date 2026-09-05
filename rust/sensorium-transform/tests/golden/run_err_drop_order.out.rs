//! Run probe: `Drop` order and temporary lifetimes across an err wrap. The
//! transformed and the untransformed build must print the same lines.
//!
//! The risk this exists to falsify is specific to the `match` the wrap is made
//! of: a `match` extends the temporaries of its SCRUTINEE to the end of the
//! match, and the wrap puts the operand there. If that ended a temporary's life
//! earlier than the enclosing statement would have, a `Drop` would move -- and
//! `rust/HONESTY.md` §9 promises it does not.
@W
struct Noisy(&'static str);

impl Drop for Noisy {
    fn drop(&mut self) {@G(7)
        println!("drop {}", self.0);
    }
}

impl Noisy {
    fn value(&self) -> Result<u8, String> {@G(8)
        println!("value {}", self.0);
        @R(8)Ok(1)@E
    }
}

fn side(x: u8) -> u8 {@G(9)
    println!("side {x}");
    @R(9)x@E
}

fn through_try() -> Result<u8, String> {@G(10)
    let v = @T(11)Noisy("try").value()@TE?;
    println!("after ?");
    @R(10)Ok(v)@E
}

fn through_sink() -> u8 {@G(12)
    let v = @S(13,HOW_SINK_UNWRAP_OR)Noisy("sink").value()@SE.unwrap_or(side(9));
    println!("after sink");
    @R(12)v@E
}

fn through_let() {@G(14)
    let _ = @L(15)Noisy("let").value()@LE;
    println!("after let _");
}

fn main() {@G(16)
    println!("{:?}", through_try());
    println!("{}", through_sink());
    through_let();
}@U
