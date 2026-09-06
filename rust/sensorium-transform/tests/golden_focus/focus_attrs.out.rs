//! Only `cfg` and `cfg_attr` can take a statement out of the build, so only
//! those decline its LINE (fix round 1, I2). `#[allow(..)]` leaves the
//! statement -- and its bindings -- exactly where they were.
@W
pub fn attributed() -> i32 {@G(7)@N(8)
    #[allow(unused_mut)]
    let mut c = 3;@N(9,c)
    #[cfg(any())]
    let d = 4;
    @R(7)c@E
}@U
