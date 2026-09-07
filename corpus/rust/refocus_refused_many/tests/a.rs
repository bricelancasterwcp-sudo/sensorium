//! One of the two test binaries `cargo test` builds here. Together they make
//! the invocation two processes, which is what `refocus` refuses on.

fn double(n: u32) -> u32 {
    n * 2
}

#[test]
fn a_doubles() {
    assert_eq!(double(2), 4);
}
