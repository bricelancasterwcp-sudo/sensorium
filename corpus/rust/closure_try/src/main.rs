//! Seeded bug: the doubling step is written as a closure with a `?` in it,
//! so a row that does not parse returns from the CLOSURE and not from the
//! function around it. The enclosing `total` carries on, the bad row
//! contributes a zero, and the total still looks like a total.

fn parse_one(text: &str) -> Result<u32, String> {
    text.parse::<u32>()
        .map_err(|_| format!("row {text:?} is not a number"))
}

fn total(rows: &[&str]) -> u32 {
    let doubled = |text: &str| -> Result<u32, String> {
        let n = parse_one(text)?;
        Ok(n * 2)
    };
    // BUG: `unwrap_or(0)` makes a failed row indistinguishable from a row
    // that was legitimately worth nothing.
    rows.iter().map(|r| doubled(r).unwrap_or(0)).sum()
}

fn main() {
    println!("total: {}", total(&["3", "x"]));
}
