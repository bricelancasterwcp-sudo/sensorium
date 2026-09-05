//! ESCAPED (design R2): the arm binds the error and the name appears
//! somewhere that is not a provable shared borrow, so the arm writes
//! `arm_ambiguous` -- a HANDLED-class record that is never a SWALLOWED
//! candidate. The two controls at the bottom are the only uses that do NOT
//! escape.

fn one() -> Result<u8, String> {
    Ok(1)
}

fn take(_e: String) {}

fn note(_e: &String) {}

/// Stored in a `Vec`: the retry-loop shape a "swallowed" verdict would be a
/// false accusation on.
pub fn stored(errors: &mut Vec<String>) -> u8 {
    match one() {
        Ok(v) => v,
        Err(e) => {
            errors.push(e);
            0
        }
    }
}

/// Passed BY VALUE to a function, which may do anything at all with it.
pub fn handed_over() -> u8 {
    match one() {
        Ok(v) => v,
        Err(e) => {
            take(e);
            0
        }
    }
}

/// Assigned into an `Option` the caller reads later.
pub fn remembered(last: &mut Option<String>) -> u8 {
    match one() {
        Ok(v) => v,
        Err(e) => {
            *last = Some(e);
            0
        }
    }
}

/// The controls: a format argument and a shared borrow, the only two uses
/// design R2 calls provable. This arm is HANDLED, not ESCAPED.
pub fn printed() -> u8 {
    match one() {
        Ok(v) => v,
        Err(e) => {
            println!("{e}");
            note(&e);
            0
        }
    }
}
