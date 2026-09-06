//! A closure inside a focused function gets no probes of its own (design §3.3):
//! its statements run when it is CALLED, not where it is written.
@W
pub fn outer() -> i32 {@G(7)@N(8)
    let f = |x: i32| {
        let y = x + 1;
        y
    };@N(9,f)
    @R(7)f(1)@E
}@U
