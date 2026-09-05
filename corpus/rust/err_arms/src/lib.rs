//! Three `Err(..) =>` arms over the same failing step, written the three
//! ways this codebase writes them, and the seeded bug is that only one of
//! them is a decision anybody made on purpose.
//!
//! `handling` absorbs the error and returns a plausible zero; `panicking`
//! turns it into a crash; `propagating` hands it back. One error, three
//! arms, three different fates -- and nothing in the program's own output
//! distinguishes them.

#[derive(Debug)]
pub struct Refused(pub u32);

pub fn step(n: u32) -> Result<u32, Refused> {
    Err(Refused(n))
}

/// BUG: the failure becomes a zero and the caller cannot tell.
pub fn handling(n: u32) -> u32 {
    match step(n) {
        Ok(v) => v,
        Err(_) => 0,
    }
}

pub fn panicking(n: u32) -> u32 {
    match step(n) {
        Ok(v) => v,
        Err(_) => panic!("step {n} refused"),
    }
}

pub fn propagating(n: u32) -> Result<u32, Refused> {
    match step(n) {
        Ok(v) => Ok(v),
        Err(e) => Err(e),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn three_arms_three_fates() -> Result<(), Refused> {
        assert_eq!(handling(1), 0);
        let caught = std::panic::catch_unwind(|| panicking(2));
        assert!(caught.is_err());
        let passed = propagating(3)?;
        assert_eq!(passed, 3);
        Ok(())
    }
}
