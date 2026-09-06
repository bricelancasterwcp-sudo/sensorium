//! The compile-time focus: which functions get per-statement LINE probes.
//!
//! Design 2026-09-06 ruling F2 -- *where a Rust focus is decided* -- is the
//! whole reason this type exists in the TRANSFORMER rather than in the runtime.
//! A LINE probe borrows the bindings it captures, and a moved binding cannot be
//! borrowed, so "which statements carry a probe" is a static decision. Made per
//! focus, it confines borrow risk to the focused functions and leaves every
//! unfocused file byte-identical to the unfocused build.
//!
//! # The boundary rule (design §2.1)
//!
//! A value is the qualname the trace already prints for Rust -- the file-local
//! `::` path [`crate::visit`] computes (`Counter::new`, `tests::a::b`). A value
//! naming a CONTAINER selects every eligible function under it, and "under"
//! means equal, or a prefix ending at a `::` boundary. `Counter` therefore
//! selects `Counter::new` and not `Counters::new`, which is the one rule this
//! module's tests exist to pin: matching on a bare prefix would put a whole
//! unrelated type in a focus, and every statement of it in the trace.
//!
//! No globs, no crate name, no file paths. Python's recorder keeps its own
//! `pkg.module[:qualname]` spelling; the two commands are different and each
//! takes what its own `tree` prints.

use crate::sha256;

/// The focus values, in the order the caller gave them, de-duplicated.
///
/// Order is kept because the manifest and the trace's meta record `values` as
/// GIVEN -- a person reading a trace should see the flags they typed -- while
/// [`Focus::focus_hash`], which is a cache key and not a record, sorts first so
/// that two spellings of the same focus do not rebuild the mirror twice.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Focus(Vec<String>);

impl Focus {
    /// No focus at all, in const position: what a census and every unfocused
    /// caller passes.
    pub const EMPTY: Focus = Focus(Vec::new());

    /// The driver's `SENSORIUM_FOCUS`: values joined by `,` (design §2.3).
    ///
    /// Empty entries are dropped rather than kept as an empty value, which
    /// would match every qualname's prefix and focus the whole workspace: a
    /// trailing comma is a typo, not a request to instrument everything.
    #[must_use]
    pub fn parse(csv: &str) -> Focus {
        let mut values: Vec<String> = Vec::new();
        for value in csv.split(',') {
            let value = value.trim();
            if value.is_empty() || values.iter().any(|v| v == value) {
                continue;
            }
            values.push(value.to_owned());
        }
        Focus(values)
    }

    /// The values as given, de-duplicated. What the manifest records.
    #[must_use]
    pub fn values(&self) -> &[String] {
        &self.0
    }

    /// No focus: the unfocused build, byte-identical to a build of this crate
    /// before the focus tier existed.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }

    /// Does this focus select `qualname` (design §2.1)?
    ///
    /// Equal, or a prefix ending at a `::` boundary -- and NOTHING else. The
    /// boundary is the two characters `::`: a name that merely shares a longer
    /// prefix (`Counters::new` under `Counter`), and a name whose next
    /// character is a single `:`, are both misses.
    #[must_use]
    pub fn matches(&self, qualname: &str) -> bool {
        self.0.iter().any(|value| {
            qualname == value
                || qualname
                    .strip_prefix(value.as_str())
                    .is_some_and(|rest| rest.starts_with("::"))
        })
    }

    /// The mirror's cache-key component (design §2.3): the first 16 hex
    /// characters of sha256 over the SORTED, de-duplicated values joined by
    /// `\n`, and `"0"` when there is no focus.
    ///
    /// Sorted, so `--focus a --focus b` and `--focus b --focus a` are one cache
    /// key and not two rebuilds of identical bytes. `"0"` rather than the hash
    /// of the empty string, so an unfocused stamp reads as the absence of a
    /// focus at a glance instead of as a hash a reader has to recognise.
    #[must_use]
    pub fn focus_hash(&self) -> String {
        if self.0.is_empty() {
            return "0".to_owned();
        }
        let mut sorted: Vec<&str> = self.0.iter().map(String::as_str).collect();
        sorted.sort_unstable();
        sorted.dedup();
        sha256::hex(sorted.join("\n").as_bytes())[..16].to_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::Focus;

    #[test]
    fn a_value_selects_the_function_it_names_and_everything_under_it() {
        let focus = Focus::parse("Counter");
        assert!(focus.matches("Counter"));
        assert!(focus.matches("Counter::new"));
        assert!(focus.matches("Counter::inner::deep"));
    }

    #[test]
    fn a_value_does_not_select_a_name_that_merely_shares_its_prefix() {
        let focus = Focus::parse("Counter");
        assert!(!focus.matches("Counters::new"));
        assert!(!focus.matches("Counterparty"));
        assert!(!focus.matches("MyCounter::new"));
    }

    /// The boundary is `::` and not `:`. No Rust qualname holds a lone colon,
    /// so this is the assertion -- rather than any qualname the walk can
    /// produce -- that reddens when the rule is written with one colon.
    #[test]
    fn the_boundary_is_two_colons_and_not_one() {
        let focus = Focus::parse("a");
        assert!(focus.matches("a::b"));
        assert!(!focus.matches("a:b"));
        assert!(!focus.matches("a:"));
    }

    #[test]
    fn a_multi_segment_value_selects_what_is_under_it() {
        let focus = Focus::parse("tests");
        assert!(focus.matches("tests::a::b"));
        assert!(!focus.matches("testsuite::a"));
        assert!(Focus::parse("nested::inner").matches("nested::inner::f"));
        assert!(!Focus::parse("nested::inner").matches("nested::inner2::f"));
    }

    #[test]
    fn an_empty_focus_matches_nothing() {
        let focus = Focus::default();
        assert!(focus.is_empty());
        assert!(!focus.matches("anything"));
        assert!(!focus.matches(""));
        assert_eq!(Focus::parse(""), Focus::default());
        assert_eq!(Focus::parse(" , ,"), Focus::default());
    }

    #[test]
    fn parse_trims_drops_empties_and_de_duplicates_keeping_the_given_order() {
        let focus = Focus::parse(" b , a ,b,,a ");
        assert_eq!(focus.values(), ["b", "a"]);
        assert!(!focus.is_empty());
    }

    #[test]
    fn the_hash_is_over_the_sorted_de_duplicated_values() {
        assert_eq!(
            Focus::parse("b,a,a").focus_hash(),
            Focus::parse("a,b").focus_hash()
        );
        assert_ne!(
            Focus::parse("a").focus_hash(),
            Focus::parse("a,b").focus_hash()
        );
        assert_eq!(Focus::default().focus_hash(), "0");
        assert_eq!(Focus::parse("a").focus_hash().len(), 16);
        // The value, not just its shape: sha256("a\nb")[..16].
        assert_eq!(Focus::parse("b,a").focus_hash(), "7e18f737311b2dc3");
    }
}
