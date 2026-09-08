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
//! `::` path the `visit` module computes (`Counter::new`, `tests::a::b`). A value
//! naming a CONTAINER selects every eligible function under it, and "under"
//! means equal, or a prefix ending at a `::` boundary. `Counter` therefore
//! selects `Counter::new` and not `Counters::new`, which is the one rule this
//! module's tests exist to pin: matching on a bare prefix would put a whole
//! unrelated type in a focus, and every statement of it in the trace.
//!
//! No globs, no crate name, no file paths. Python's recorder keeps its own
//! `pkg.module[:qualname]` spelling; the two commands are different and each
//! takes what its own `tree` prints.

use sensorium_rt::sha256;

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
        sha256::hex(self.canonical().join("\n").as_bytes())[..16].to_owned()
    }

    /// This focus as a SET: sorted and de-duplicated (design A10).
    ///
    /// The form [`Focus::focus_hash`] hashes, and therefore the form every
    /// OTHER "is this the same focus?" question must be asked in. Two spellings
    /// that share a hash share a shim path, artifacts and manifests, so a
    /// consumer comparing them any other way -- ordered `Vec` equality, say --
    /// answers "different" about one indivisible build.
    #[must_use]
    pub fn canonical(&self) -> Vec<String> {
        canonical_values(&self.0)
    }
}

/// [`Focus::canonical`] for a list that is not a [`Focus`]: a manifest's
/// recorded `focus.values`, which the converter compares against an
/// invocation's list.
#[must_use]
pub fn canonical_values(values: &[String]) -> Vec<String> {
    let mut out = values.to_vec();
    out.sort_unstable();
    out.dedup();
    out
}

/// One fn item of a file, as the transform itself classifies it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FnItem {
    /// The file-local `::` path -- exactly the spelling a focus value takes.
    pub qualname: String,
    /// `None` for a fn a focus CAN select; the transform's own skip reason
    /// (`"const"`, `"extern"`, `"async"`, `"macro"`) for one it cannot.
    pub skipped: Option<&'static str>,
}

/// Every fn item of `source`, so that a caller can answer "would a focus
/// select this?" without guessing at the transform's rules.
///
/// It runs the transform's OWN walk and reads its rows back rather than
/// classifying a second time: a `Fn` site is exactly a fn this transform
/// instruments -- and therefore exactly one a focus can select -- and
/// [`crate::Transformed::skipped`] is exactly the set it will not, with the
/// reason it gives. A second classifier here could drift from the first, and
/// the drift would show up as a `--focus` the driver accepts and the transform
/// ignores.
///
/// The walk it runs is the CENSUS walk (`census::walk`, transform
/// 0.4.2): the same visitor with its splicing half switched off. Until 0.4.2
/// this ran the whole transform on every file of the workspace -- every offset
/// computed, every fragment placed, every rewritten source assembled and its
/// line count checked -- and discarded the source to read two lists off the side
/// of it. `tests/fn_census.rs` is what says the answer did not move.
///
/// A file that does not parse yields NO items: it is not instrumented either,
/// so it holds nothing a focus could select.
#[must_use]
pub fn fn_items(source: &str, file: &str) -> Vec<FnItem> {
    let Some(walked) = crate::census::walk(source, file) else {
        return Vec::new();
    };
    let mut items: Vec<FnItem> = walked
        .sites
        .iter()
        .filter(|site| site.kind == crate::SiteKind::Fn)
        .map(|site| FnItem {
            qualname: site.qualname.clone(),
            skipped: None,
        })
        .collect();
    items.extend(walked.skipped.iter().map(|s| FnItem {
        qualname: s.qualname.clone(),
        skipped: Some(s.reason),
    }));
    items
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

    /// The canonical form and the hash are ONE rule: whatever shares a
    /// `focus_hash` shares a shim path, artifacts and manifests, so every
    /// other consumer that asks "is this the same focus?" -- the converter
    /// matching a manifest's `values` against an invocation's -- has to reach
    /// the same answer or it will read `focus_matched: []` off a build that
    /// matched (design A10).
    #[test]
    fn the_canonical_form_is_sorted_de_duplicated_and_what_the_hash_is_over() {
        assert_eq!(Focus::parse("b,a,b").canonical(), ["a", "b"]);
        assert_eq!(Focus::parse("a,b").canonical(), ["a", "b"]);
        assert!(Focus::default().canonical().is_empty());
        assert_eq!(
            super::canonical_values(&["b".to_owned(), "a".to_owned(), "b".to_owned()]),
            ["a", "b"]
        );
        // The hash is the hash OF the canonical form, not a parallel rule.
        assert_eq!(
            Focus::parse("b,a").focus_hash(),
            sensorium_rt::sha256::hex(Focus::parse("b,a").canonical().join("\n").as_bytes())[..16]
        );
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

    /// The one check that the sha256 the focus hash is taken with is still
    /// sha256.
    ///
    /// This crate has no copy of the algorithm any more: `sensorium_rt::sha256`
    /// is the repository's only one (2026-09-08). The NIST vectors live with
    /// it, in `sensorium-rt/src/sha256.rs`; this says the module `focus_hash`
    /// reaches is that module and not something that merely compiles. It is
    /// what makes the literal above (`"7e18f737311b2dc3"`) mean sha256 rather
    /// than "whatever we hashed with".
    #[test]
    fn the_sha256_the_focus_hash_is_taken_with_is_the_runtimes() {
        assert_eq!(
            sensorium_rt::sha256::hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    /// The eligible set a `--focus` is resolved against IS the set this
    /// transform instruments -- the one rule `cargo-sensorium`'s resolver
    /// leans on entirely.
    #[test]
    fn fn_items_names_what_is_instrumented_and_what_is_skipped_with_the_reason() {
        let items = super::fn_items(
            "mod m {\n    pub fn f() {}\n    pub async fn g() {}\n    pub const fn c() {}\n}\n\
             fn h() {}\nstruct S;\nimpl S {\n    fn k(&self) {}\n}\n",
            "src/lib.rs",
        );
        let eligible: Vec<&str> = items
            .iter()
            .filter(|i| i.skipped.is_none())
            .map(|i| i.qualname.as_str())
            .collect();
        assert_eq!(eligible, ["m::f", "h", "S::k"]);
        let skipped: Vec<(&str, &str)> = items
            .iter()
            .filter_map(|i| i.skipped.map(|r| (i.qualname.as_str(), r)))
            .collect();
        assert_eq!(skipped, [("m::g", "async"), ("m::c", "const")]);
    }

    #[test]
    fn a_file_that_does_not_parse_holds_nothing_a_focus_could_select() {
        assert!(super::fn_items("fn (", "src/lib.rs").is_empty());
    }

    // -----------------------------------------------------------------------
    // The census walk behind `fn_items` (design 2026-09-07 §6)
    // -----------------------------------------------------------------------

    /// A file holding every shape the two walks have to agree about: each skip
    /// reason, both marks, a nested `mod`, an `impl` method, and -- ALL THREE
    /// of the emit gates the census path leans on -- a `?`, a `?`-bearing
    /// closure and an `Err(..) =>` arm.
    ///
    /// The last two are here because of review finding N1. Without them the
    /// gates at `closures.rs`'s `frame_closure` and `arms.rs`'s `err_arm` were
    /// untested from BOTH sides: the internal assertions below never met the
    /// shapes, and no differential test can ever meet them either, because
    /// [`fn_items`] filters to [`crate::SiteKind::Fn`] and drops every other
    /// kind on the floor. Both mutants survived the whole suite; both are
    /// killed now.
    const EVERY_SHAPE: &str = "\
mod m {
    pub fn f() -> Result<u8, u8> {
        // A closure whose body holds a `?` at its own depth: a FRAMED closure
        // with a guard and wrapped exits on the emitting walk, nothing at all
        // on the census walk.
        let c = || -> Result<u8, u8> { Ok(g()? + 1) };
        // An `Err(..) =>` arm the grammar classifies as PROPAGATE: an arm site
        // with a probe statement on the emitting walk, nothing on the census.
        match g() {
            Err(e) => return Err(e),
            Ok(_) => {}
        }
        let v = g()?;
        Ok(v + c()?)
    }
    pub async fn a() {}
    pub const fn c() -> u8 { 1 }
    extern \"C\" fn e() {}
    fn g() -> Result<u8, u8> { Ok(1) }
}
macro_rules! mac {
    () => {
        fn inside() {}
    };
}
#[test]
fn a_test() {}
#[tokio::test]
async fn an_async_test() {}
#[bench]
fn a_bench(_: &mut u8) {}
#[cfg(test)]
fn a_helper() {}
fn main() {}
struct S;
impl S {
    fn k(&self) -> u8 { 1 }
}
";

    /// Everything a `Fn` row carries EXCEPT its index: the index is minted from
    /// a counter the err-flow, closure and LINE sites also draw on, and the
    /// census walk mints none of those, so it is the one field the two walks
    /// are not expected to agree on (see [`crate::visit::Ctx::record_sites`]).
    fn rows(sites: &[crate::Site]) -> Vec<(&str, &str, u32, crate::RetKind, bool, bool)> {
        sites
            .iter()
            .filter(|s| s.kind == crate::SiteKind::Fn)
            .map(|s| {
                (
                    s.file.as_str(),
                    s.qualname.as_str(),
                    s.firstlineno,
                    s.ret.expect("a fn row carries what its signature returns"),
                    s.test,
                    s.main,
                )
            })
            .collect()
    }

    /// The whole promise of the census path: the rows are the transform's own.
    ///
    /// `fn_items` reads only `qualname` and the skip reason off these rows, so
    /// the comparison here is deliberately WIDER than its caller -- the `test`
    /// mark included, which `marks::is_test_fn` decides and which a converter
    /// reads to say a chain was returned to the harness rather than lost. A
    /// census that recorded rows without it would pass every `fn_items` test in
    /// this crate.
    #[test]
    fn the_census_walk_records_the_rows_the_transform_records() {
        let file = "src/lib.rs";
        let walked = crate::census::walk(EVERY_SHAPE, file).expect("the fixture parses");
        let spliced = crate::transform_file(
            EVERY_SHAPE,
            file,
            "d41d8cd98f00b204",
            0,
            crate::FileRole::default(),
            &Focus::EMPTY,
        )
        .expect("the fixture transforms");

        assert_eq!(rows(&walked.sites), rows(&spliced.sites));
        assert_eq!(walked.skipped, spliced.skipped);

        // Positively, so that "equal" cannot mean "equally empty": the marks
        // and the four reasons are all actually there.
        let marked: Vec<&str> = walked
            .sites
            .iter()
            .filter(|s| s.test)
            .map(|s| s.qualname.as_str())
            .collect();
        assert_eq!(marked, ["a_test", "a_bench"], "the test marks survive");
        let mut reasons: Vec<&str> = walked.skipped.iter().map(|s| s.reason).collect();
        reasons.sort_unstable();
        reasons.dedup();
        assert_eq!(reasons, ["async", "const", "extern", "macro"]);
        assert!(
            walked.sites.iter().all(|s| s.file == file),
            "a census row names the file it was asked about"
        );
    }

    /// The census walk places NOTHING. Not a splice, and not one of the site
    /// kinds that exist only because a fragment goes somewhere.
    #[test]
    fn the_census_walk_splices_nothing() {
        use crate::SiteKind::{Arm, Closure, Fn, Try};

        let walked = crate::census::walk(EVERY_SHAPE, "src/lib.rs").expect("the fixture parses");
        assert!(walked.splices.is_empty(), "a census walk splices nothing");
        assert!(walked.spawns.is_empty(), "and renames no spawn");
        assert!(walked.partial.is_empty(), "and declines no site");
        assert!(walked.focused.is_empty(), "and focuses nothing");
        assert!(
            walked.sites.iter().all(|s| s.kind == Fn),
            "every row a census walk records is a fn row, and it recorded {:?}",
            walked.sites.iter().map(|s| s.kind).collect::<Vec<_>>()
        );

        // The three gates, named. Each of these kinds exists ONLY because a
        // fragment goes somewhere, and each is suppressed by a different
        // `!self.emit` return -- `visit/walk.rs`'s `visit_expr_try` for TRY,
        // `closures.rs`'s `frame_closure` for CLOSURE, `arms.rs`'s `err_arm`
        // for ARM. Asserting the emitting walk mints all three on THIS fixture
        // is what turns the assertion above from a property of a file with
        // nothing in it into a measurement of all three gates (review N1: with
        // the closure and the arm missing from the fixture, deleting either
        // gate left the whole suite green).
        let spliced = crate::transform(EVERY_SHAPE, "src/lib.rs", "", 0, false, &Focus::EMPTY)
            .expect("the fixture transforms");
        for kind in [Try, Closure, Arm] {
            assert!(
                spliced.sites.iter().any(|s| s.kind == kind),
                "the fixture must reach the {kind:?} gate for this test to measure it"
            );
        }
        assert_ne!(
            spliced.source, EVERY_SHAPE,
            "the emitting walk on this fixture does rewrite it"
        );
    }

    /// `main` is the DRIVER's knowledge (which crate root is a binary's), and
    /// the resolver never had it: `fn_items` asked for a transform with
    /// `is_bin_root: false` before 0.4.2 and asks the census for the same
    /// silence now. Pinned rather than left to be discovered, because the row
    /// looks like the transform's and differs in this one field.
    #[test]
    fn a_census_row_never_carries_the_main_mark() {
        let walked = crate::census::walk(EVERY_SHAPE, "src/lib.rs").expect("the fixture parses");
        assert!(walked.sites.iter().all(|s| !s.main));
        let bin = crate::transform_file(
            EVERY_SHAPE,
            "src/main.rs",
            "d41d8cd98f00b204",
            0,
            crate::FileRole {
                is_crate_root: true,
                is_bin_root: true,
            },
            &Focus::EMPTY,
        )
        .expect("the fixture transforms");
        assert!(
            bin.sites.iter().any(|s| s.main),
            "the emitting walk carries it when its caller knows"
        );
    }
}
