//! An `async` block is never framed and the `?` inside it is DECLARED rather
//! than wrapped (design R5/R6): the future may be polled on a thread other
//! than the one that built it, so a probe inside would record against
//! whichever thread happened to poll it. A plain closure created inside an
//! async block is a different thing -- its body runs when it is CALLED -- so
//! it is framed like any other.
@W
use std::future::Future;

fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

pub fn later() -> impl Future<Output = Result<u8, String>> {@G(8)
    @R(8)async {
        let v = one()?;
        Ok(v + 1)
    }@E
}

pub fn closure_inside() -> impl Future<Output = Result<u8, String>> {@G(9)
    @R(9)async {
        let f = |n: u8| -> Result<u8, String> {@K(10) @R(10)Ok(@T(11)one()@TE? + n)@E };
        f(1)
    }@E
}

/// An `async` CLOSURE is a future-maker too: `asyncness` is what decides,
/// not `move` and not the shape of the body. Never framed, its `?` declared,
/// and not one byte of it moved.
pub fn async_closure() -> impl Future<Output = Result<u8, String>> {@G(12)
    let f = async |n: u8| -> Result<u8, String> { Ok(one()? + n) };
    @R(12)f(1)@E
}@U
