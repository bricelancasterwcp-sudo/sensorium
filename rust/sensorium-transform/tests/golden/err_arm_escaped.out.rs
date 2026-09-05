//! ESCAPED (design R2): the arm binds the error and the name appears
//! somewhere that is not a provable shared borrow, so the arm writes
//! `arm_ambiguous` -- a HANDLED-class record that is never a SWALLOWED
//! candidate. The two controls at the bottom are the only uses that do NOT
//! escape.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

fn take(_e: String) {@G(8)}

fn note(_e: &String) {@G(9)}

/// Stored in a `Vec`: the retry-loop shape a "swallowed" verdict would be a
/// false accusation on.
pub fn stored(errors: &mut Vec<String>) -> u8 {@G(10)
    @R(10)match one() {
        Ok(v) => v,
        Err(e) => {@P(11,HOW_ARM_AMBIGUOUS,e)
            errors.push(e);
            0
        }
    }@E
}

/// Passed BY VALUE to a function, which may do anything at all with it.
pub fn handed_over() -> u8 {@G(12)
    @R(12)match one() {
        Ok(v) => v,
        Err(e) => {@P(13,HOW_ARM_AMBIGUOUS,e)
            take(e);
            0
        }
    }@E
}

/// Assigned into an `Option` the caller reads later.
pub fn remembered(last: &mut Option<String>) -> u8 {@G(14)
    @R(14)match one() {
        Ok(v) => v,
        Err(e) => {@P(15,HOW_ARM_AMBIGUOUS,e)
            *last = Some(e);
            0
        }
    }@E
}

/// The R2 amendment of 2026-09-05: `format!` RETURNS the rendered text, and
/// here that text is the arm's own value, so a rendering of the failure
/// reaches every caller. Endpoint E6' STOPped on this shape.
pub fn rendered_into_value() -> String {@G(16)
    @R(16)match one() {
        Ok(v) => v.to_string(),
        Err(e) => { @P(17,HOW_ARM_AMBIGUOUS,e) format!("unreadable: {e}") },
    }@E
}

/// The controls: a format argument and a shared borrow, the only two uses
/// design R2 calls provable. This arm is HANDLED, not ESCAPED.
pub fn printed() -> u8 {@G(18)
    @R(18)match one() {
        Ok(v) => v,
        Err(e) => {@P(19,HOW_ARM_HANDLED,e)
            println!("{e}");
            note(&e);
            0
        }
    }@E
}@U
