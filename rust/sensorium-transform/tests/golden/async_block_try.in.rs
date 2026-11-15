//! An `async` block is a frame. The drive future parks that frame on the
//! thread that polls it. A `?` inside the block is still DECLARED rather than
//! wrapped (design R5/R6). A plain closure created inside an async block is a
//! different thing -- its body runs when it is CALLED -- so it is framed like
//! any other.

use std::future::Future;

fn one() -> Result<u8, String> {
    Ok(1)
}

pub fn later() -> impl Future<Output = Result<u8, String>> {
    async {
        let v = one()?;
        Ok(v + 1)
    }
}

pub fn closure_inside() -> impl Future<Output = Result<u8, String>> {
    async {
        let f = |n: u8| -> Result<u8, String> { Ok(one()? + n) };
        f(1)
    }
}

/// An `async` CLOSURE is a future-maker too: `asyncness` is what decides,
/// not `move` and not the shape of the body. Never framed, its `?` declared,
/// and not one byte of it moved.
pub fn async_closure() -> impl Future<Output = Result<u8, String>> {
    let f = async |n: u8| -> Result<u8, String> { Ok(one()? + n) };
    f(1)
}
