//! The four written sinks (design R2). The wrap goes around the RECEIVER and
//! the method call stays outside it, so what the sink does is untouched.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

pub fn dropped() -> Option<u8> {@G(8)
    @R(8)@S(9,HOW_SINK_OK)one()@SE.ok()@E
}

pub fn defaulted() -> u8 {@G(10)
    @R(10)@S(11,HOW_SINK_UNWRAP_OR)one()@SE.unwrap_or(0)@E
}

pub fn lazily() -> u8 {@G(12)
    @R(12)@S(13,HOW_SINK_UNWRAP_OR)one()@SE.unwrap_or_else(|_| 0)@E
}

pub fn zeroed() -> u8 {@G(14)
    @R(14)@S(15,HOW_SINK_UNWRAP_OR)one()@SE.unwrap_or_default()@E
}

/// The two predicates design R2 refuses to probe -- they take `&self`, so the
/// wrap would move where the original autorefs -- and `unwrap`, which the panic
/// hook covers instead. No site, no wrap, no `partial` row.
pub fn never_probed() -> bool {@G(16)
    @R(16)one().is_err() || one().is_ok()@E
}

pub struct Mine;

impl Mine {
    pub fn ok(&self, n: u8) -> u8 {@G(17)
        @R(17)n@E
    }

    pub fn unwrap_or_default(&self, n: u8) -> u8 {@G(18)
        @R(18)n@E
    }
}

fn mine() -> Mine {@G(19)
    @R(19)Mine@E
}

/// A workspace's own `ok` is not `Result::ok`, and the ARITY is what says so:
/// neither of these is a sink, so neither receiver is wrapped and neither is
/// declared.
pub fn not_the_sink() -> u8 {@G(20)
    @R(20)mine().ok(1) + mine().unwrap_or_default(2)@E
}@U
