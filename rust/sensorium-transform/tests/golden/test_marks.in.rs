//! The manifest marks (design R1b): a `#[test]`- or `#[bench]`-attributed fn
//! is `test: true`, and a bin crate root's `fn main` is `main: true`. Neither
//! changes a byte of the source -- they are facts about the manifest row, not
//! about the rewrite -- so this golden's `.out.rs` is an ordinary one and
//! `tests/golden_errflow.rs` is where the marks themselves are asserted.

pub fn main() {
    println!("{}", helper());
}

fn helper() -> u8 {
    7
}

#[test]
fn plain_test() {
    assert_eq!(helper(), 7);
}

/// `#[test]` resolves to this path, and macro-expanded code writes it out.
#[core::prelude::v1::test]
fn qualified_test() {
    assert_eq!(helper(), 7);
}

pub mod inner {
    /// Not the crate root's `main`: a `main` inside a module is an ordinary
    /// fn and carries no mark.
    pub fn main() -> u8 {
        8
    }
}
