//! The return shapes the capture probe has to classify, one fn per shape.
//!
//! Tier `call` captures a return value through `Debug` (`rust/HONESTY.md` §2),
//! so the three interesting cases are a `Result` (the outcome comes off the
//! exit operand, not off the value), a type with no `Debug` impl at all, and a
//! `Debug` impl that panics while the instrument is formatting it. The last two
//! must both read `<unread>` and neither may reach the program's stderr: the
//! runtime catches the formatting panic and its hook stays silent for it.

use std::fmt;

/// A `Result`-returning fn: `ok` and `err` come off the exit operand.
///
/// # Errors
/// The input text when it is not a number this fn accepts.
pub fn parse_small(text: &str) -> Result<u32, String> {
    match text.parse::<u32>() {
        Ok(n) if n < 100 => Ok(n),
        Ok(n) => Err(format!("{n} is not small")),
        Err(e) => Err(e.to_string()),
    }
}

/// No `Debug` impl anywhere: the specialised capture cannot apply, so the
/// fallback does, and the trace says `<unread>` rather than inventing text.
pub struct Opaque {
    pub tag: u8,
}

#[must_use]
pub fn make_opaque() -> Opaque {
    Opaque { tag: 3 }
}

/// A `Debug` impl that panics. Formatting it is the instrument's own work, so
/// the panic is caught, the program is not unwound, and the hook prints
/// nothing.
pub struct Prickly;

impl fmt::Debug for Prickly {
    fn fmt(&self, _f: &mut fmt::Formatter<'_>) -> fmt::Result {
        panic!("Prickly refuses to be formatted");
    }
}

#[must_use]
pub fn make_prickly() -> Prickly {
    Prickly
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn small_numbers_parse_and_large_ones_do_not() {
        assert_eq!(parse_small("7"), Ok(7));
        assert!(parse_small("700").is_err());
        assert!(parse_small("seven").is_err());
    }

    #[test]
    fn the_undebuggable_values_are_still_ordinary_values() {
        assert_eq!(make_opaque().tag, 3);
        let _prickly = make_prickly();
    }
}
