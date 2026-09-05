//! The four written sinks (design R2). The wrap goes around the RECEIVER and
//! the method call stays outside it, so what the sink does is untouched.

fn one() -> Result<u8, String> {
    Ok(1)
}

pub fn dropped() -> Option<u8> {
    one().ok()
}

pub fn defaulted() -> u8 {
    one().unwrap_or(0)
}

pub fn lazily() -> u8 {
    one().unwrap_or_else(|_| 0)
}

pub fn zeroed() -> u8 {
    one().unwrap_or_default()
}

/// The two predicates design R2 refuses to probe -- they take `&self`, so the
/// wrap would move where the original autorefs -- and `unwrap`, which the panic
/// hook covers instead. No site, no wrap, no `partial` row.
pub fn never_probed() -> bool {
    one().is_err() || one().is_ok()
}

pub struct Mine;

impl Mine {
    pub fn ok(&self, n: u8) -> u8 {
        n
    }

    pub fn unwrap_or_default(&self, n: u8) -> u8 {
        n
    }
}

fn mine() -> Mine {
    Mine
}

/// A workspace's own `ok` is not `Result::ok`, and the ARITY is what says so:
/// neither of these is a sink, so neither receiver is wrapped and neither is
/// declared.
pub fn not_the_sink() -> u8 {
    mine().ok(1) + mine().unwrap_or_default(2)
}
