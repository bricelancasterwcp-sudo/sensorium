//! The two manifest MARKS a fn row can carry (design R1b), and the one of them
//! this crate can decide by itself.
//!
//! A mark is a fact about the row, never about the rewrite: neither changes a
//! byte of the source. The converter reads them for one disposition -- an `Err`
//! that left a `test: true` or `main: true` frame was RETURNED TO THE HARNESS,
//! which is a different thing from an `Err` that was lost (design R8).
//!
//! `main` cannot be decided here at all: whether a crate root is a BINARY's is
//! the driver's knowledge (`crate::FileRole::is_bin_root`), so this module only
//! answers the `test` half.

use syn::Attribute;

/// Does this fn item carry a test attribute?
///
/// The rule is the LAST path segment, and it is deliberately that loose. The
/// `#[test]` a person writes and the `#[core::prelude::v1::test]` a
/// macro-expanded file writes are the same attribute, `#[bench]` is design
/// R1b's second spelling, and `#[tokio::test]` and every other harness's
/// attribute end in `test` too -- all of them mark a fn the harness calls,
/// which is exactly what the mark means.
///
/// What the rule does NOT match is the far more common `#[cfg(test)]`, whose
/// path is `cfg`: a fn inside a test module is not itself a test, and marking
/// one would tell the converter that an `Err` reaching a helper had reached the
/// harness.
pub(crate) fn is_test_fn(attrs: &[Attribute]) -> bool {
    attrs.iter().any(|attr| {
        attr.path()
            .segments
            .last()
            .is_some_and(|s| s.ident == "test" || s.ident == "bench")
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn attrs_of(source: &str) -> Vec<Attribute> {
        let item: syn::ItemFn = syn::parse_str(source).expect("a fn item");
        item.attrs
    }

    #[test]
    fn every_spelling_of_a_test_attribute_marks_the_row() {
        for source in [
            "#[test] fn t() {}",
            "#[bench] fn t(_: &mut u8) {}",
            "#[core::prelude::v1::test] fn t() {}",
            "#[::core::prelude::v1::test] fn t() {}",
            "#[tokio::test] fn t() {}",
            "#[allow(dead_code)] #[test] fn t() {}",
        ] {
            assert!(is_test_fn(&attrs_of(source)), "{source} is a test fn");
        }
    }

    #[test]
    fn nothing_else_does_and_cfg_test_least_of_all() {
        for source in [
            "fn t() {}",
            "#[cfg(test)] fn t() {}",
            "#[cfg(not(test))] fn t() {}",
            "#[inline] fn t() {}",
            "#[doc = \"test\"] fn t() {}",
            "#[testing] fn t() {}",
        ] {
            assert!(!is_test_fn(&attrs_of(source)), "{source} is not a test fn");
        }
    }
}
