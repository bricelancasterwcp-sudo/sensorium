//! A `?` tail is wrapped. The `?` still leaves before `ret` is reached when it
//! propagates, so that frame closes `none` -- HONESTY §1.

use std::num::ParseIntError;

pub fn forwarded(v: &str) -> Result<u8, ParseIntError> {@G(7)
    @R(7)Ok(v.parse::<u8>()?)@E
}

pub fn tail_is_try(r: Result<Result<u8, ParseIntError>, ParseIntError>) -> Result<u8, ParseIntError> {@G(8)
    @R(8)r?@E
}@U
