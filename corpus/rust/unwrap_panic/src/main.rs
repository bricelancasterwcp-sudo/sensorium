//! Seeded bug: an account whose quota LOOKUP failed is not an account with
//! no quota, but `.unwrap()` cannot tell those apart. The refusal is turned
//! into a crash one frame above where it was produced, and the panic
//! message is the only thing that survives.

#[derive(Debug)]
struct Refused(u32);

fn quota(account: u32) -> Result<u32, Refused> {
    Err(Refused(account))
}

fn charge(account: u32) -> u32 {
    // BUG: the refusal is a fact about the lookup, not about the account.
    quota(account).unwrap()
}

fn main() {
    println!("charged: {}", charge(7));
}
