//! A `?` tail is wrapped. The `?` still leaves before `ret` is reached when it
//! propagates, so that frame closes `none` -- HONESTY §1.
@W
use std::num::ParseIntError;

pub fn forwarded(v: &str) -> Result<u8, ParseIntError> {@G(7)
    @R(7)Ok(@T(8)v.parse::<u8>()@TE?)@E
}

pub fn tail_is_try(r: Result<Result<u8, ParseIntError>, ParseIntError>) -> Result<u8, ParseIntError> {@G(9)
    @R(9)@T(10)r@TE?@E
}@U
