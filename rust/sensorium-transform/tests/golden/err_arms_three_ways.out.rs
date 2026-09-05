//! `Err(..) =>` arms are classified syntactically at closure depth 0 (design
//! R2): PROPAGATE writes a RAISE at the arm's entry, PANIC writes NOTHING --
//! a probe there would move the `panic!`'s own column, which E7 measures --
//! and HANDLED writes the swallow candidate.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

/// PROPAGATE: the arm's tail is `Err(..)`, so the error leaves this frame.
pub fn propagates() -> Result<u8, String> {@G(8)
    @R(8)match one() {
        Ok(v) => Ok(v),
        Err(e) => { @P(9,HOW_ARM_PROPAGATE,e) Err(e) },
    }@E
}

/// PROPAGATE by a `?` at depth 0, with an UNBOUND pattern: no type and no
/// text to read, so the record says only that an error was seen here.
pub fn propagates_by_try() -> Result<u8, String> {@G(10)
    @R(10)match one() {
        Ok(v) => Ok(v),
        Err(_) => { @P(11,HOW_ARM_PROPAGATE) Ok(@T(12)one()@TE? + 1) },
    }@E
}

/// PANIC: one of the four diverging macros at depth 0. No probe at all, so
/// the `panic!`'s own column is exactly where it was.
pub fn panics() -> u8 {@G(13)
    @R(13)match one() {
        Ok(v) => v,
        Err(e) => panic!("no: {e}"),
    }@E
}

/// HANDLED: the bound name is used only as a format argument and as a shared
/// borrow, which is what design R2 calls a provable non-escape.
pub fn handles() -> u8 {@G(14)
    @R(14)match one() {
        Ok(v) => v,
        Err(e) => {@P(15,HOW_ARM_HANDLED,e)
            println!("{e}");
            note(&e);
            0
        }
    }@E
}

fn note(_e: &String) {@G(16)}

/// An `assert!` is NOT one of the four diverging macros (the ruling of
/// 2026-09-04): this arm is HANDLED and the assert may well pass.
pub fn asserted(flag: bool) -> u8 {@G(17)
    @R(17)match one() {
        Ok(v) => v,
        Err(..) => {@P(18,HOW_ARM_HANDLED)
            assert!(flag, "an assert is not a panic");
            0
        }
    }@E
}@U
