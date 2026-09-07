//! A closure inside a focused function gets no probes of its own (design §3.3):
//! its statements run when it is CALLED, not where it is written.

pub fn outer() -> i32 {
    let f = |x: i32| {
        let y = x + 1;
        y
    };
    f(1)
}
