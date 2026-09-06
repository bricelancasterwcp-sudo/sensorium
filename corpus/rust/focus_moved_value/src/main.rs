//! The borrow-safety case. A probe captures by shared borrow immediately
//! after the write (design §3.2), so `v` is captured at its own `let`,
//! before the next statement moves it into `w`, and `w` at its own -- and
//! the moved-out `v` is never touched again. If that were not so, this crate
//! would not compile, which is why the case's first pin is that it BUILDS.

fn go() -> usize {
    let v = vec![1, 2];
    let w = v;
    let n = w.len();
    n
}

fn main() {
    println!("len: {}", go());
}
