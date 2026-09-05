//! Seeded bug: one fixture row says `4o` where it means `40`, and every
//! layer above the parse hands the same failure straight up with `?`.
//! Four frames touch that one error and not one of them says a word about
//! it; the test fails with a bare `Err` and no stack.

#[derive(Debug)]
pub struct BadRow(pub String);

pub fn field(raw: &str) -> Result<u32, BadRow> {
    raw.parse::<u32>().map_err(|_| BadRow(raw.to_string()))
}

pub fn threshold(row: &str) -> Result<u32, BadRow> {
    let value = field(row)?;
    Ok(value)
}

pub fn budget(row: &str) -> Result<u32, BadRow> {
    let t = threshold(row)?;
    Ok(t * 10)
}

pub fn plan(row: &str) -> Result<u32, BadRow> {
    let b = budget(row)?;
    Ok(b + 1)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_plan_reads_the_threshold_row() -> Result<(), BadRow> {
        let good = plan("4")?;
        assert_eq!(good, 41);
        // BUG: the fixture's second row is `4o`, not `40`.
        let typo = plan("4o")?;
        assert_eq!(typo, 401);
        Ok(())
    }
}
