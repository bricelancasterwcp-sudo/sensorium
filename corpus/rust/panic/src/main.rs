//! Seeded bug: a panic inside the quota calculation is caught and turned
//! into a successful zero, so the caller sees Ok and the failed quota is
//! silently billed as nothing. The program exits 0 and prints a plausible
//! total.

fn risky(n: u32) -> u32 {
    if n == 0 {
        panic!("quota divisor was zero");
    }
    100 / n
}

fn attempt(n: u32) -> Result<u32, String> {
    match std::panic::catch_unwind(|| risky(n)) {
        Ok(v) => Ok(v),
        // BUG: a panic is not a zero quota; this reports success.
        Err(_) => Ok(0),
    }
}

fn main() {
    let total: u32 = [5, 0]
        .into_iter()
        .map(|n| attempt(n).unwrap_or(0))
        .sum();
    println!("total: {total}");
}
