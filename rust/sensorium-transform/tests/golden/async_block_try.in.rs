//! An `async` block is never framed and the `?` inside it is DECLARED rather
//! than wrapped (design R5/R6): the future may be polled on a thread other
//! than the one that built it, so a probe inside would record against
//! whichever thread happened to poll it. A plain closure created inside an
//! async block is a different thing -- its body runs when it is CALLED -- so
//! it is framed like any other.

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
