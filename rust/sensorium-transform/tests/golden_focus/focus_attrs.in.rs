//! Only `cfg` and `cfg_attr` can take a statement out of the build, so only
//! those decline its LINE (fix round 1, I2). `#[allow(..)]` leaves the
//! statement -- and its bindings -- exactly where they were.

pub fn attributed() -> i32 {
    #[allow(unused_mut)]
    let mut c = 3;
    #[cfg(any())]
    let d = 4;
    c
}
