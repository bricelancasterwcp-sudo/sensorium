//! Golden pairs for rung 3's classified sites: `Err(..) =>` arms, `if let
//! Err(..)` bodies, the frames `?`-bearing closures get, the `?` inside an
//! `async` block that is declared rather than wrapped, and the two manifest
//! marks.
//!
//! Same discipline as `tests/golden.rs` and `tests/errflow.rs`: the bytes are
//! pinned by an `.out.rs` written with the placeholders from
//! `tests/common/mod.rs`, so no fragment is ever read back out of the
//! implementation under test, and `tests/oracle.rs` compiles every one of these
//! at `-D warnings` -- which is what says the emitted block is legal Rust and
//! not merely the bytes the test expected.
//!
//! This file exists rather than more of `tests/golden.rs` because that file is
//! at 764 lines and the crate's ceiling is 800.

mod common;

use common::{closure_sites, err_sites, marked, partials, read, run, run_role, sites};

use sensorium_transform::{census, FileRole, RetKind, SiteKind};

/// The role every ordinary golden is transformed under.
const LIB_ROOT: FileRole = FileRole {
    is_crate_root: true,
    is_bin_root: false,
};

/// The role a BIN crate's root is transformed under, which is the only way a
/// `main: true` mark is ever written.
const BIN_ROOT: FileRole = FileRole {
    is_crate_root: true,
    is_bin_root: true,
};

// ---------------------------------------------------------------------------
// `Err(..) =>` arms
// ---------------------------------------------------------------------------

#[test]
fn an_err_arm_is_classified_propagate_panic_or_handled() {
    let t = run("err_arms_three_ways", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 6, RetKind::Value),
            (8, "propagates", 11, RetKind::Value),
            (10, "propagates_by_try", 20, RetKind::Value),
            (13, "panics", 29, RetKind::Value),
            (14, "handles", 38, RetKind::Value),
            (16, "note", 49, RetKind::Unit),
            (17, "asserted", 53, RetKind::Value),
        ]
    );
    assert_eq!(
        err_sites(&t),
        [
            // An `Err(..)` tail: the error leaves the frame.
            (9, "propagates", 14, SiteKind::Arm, "arm_propagate"),
            // A `?` at depth 0, with nothing bound to name.
            (11, "propagates_by_try", 23, SiteKind::Arm, "arm_propagate"),
            (12, "propagates_by_try", 23, SiteKind::Try, "try"),
            // The PANIC arm at line 32 is absent: no site, no probe.
            (15, "handles", 41, SiteKind::Arm, "arm_handled"),
            // `assert!` is not one of the four diverging macros.
            (18, "asserted", 56, SiteKind::Arm, "arm_handled"),
        ]
    );
    assert!(t.partial.is_empty(), "{:?}", t.partial);

    // The classification the census reports is the classification that placed
    // those probes -- one decision, counted once.
    let c = census(&read("err_arms_three_ways", "in"));
    assert_eq!(
        (
            c.arms_propagate,
            c.arms_panic,
            c.arms_escaped,
            c.arms_handled
        ),
        (2, 1, 0, 2)
    );
}

#[test]
fn a_panic_arm_is_left_byte_for_byte_where_it_was() {
    // Endpoint E7 measures panic LINES and COLUMNS. A probe in front of a
    // `panic!` would move its column, so a PANIC-classified arm gets nothing at
    // all -- and this is that promise as a measurement rather than an argument.
    let input = read("err_arms_three_ways", "in");
    let t = run("err_arms_three_ways", 7);
    let before: Vec<&str> = input.lines().collect();
    let after: Vec<&str> = t.source.lines().collect();
    let panic_line = before
        .iter()
        .position(|l| l.contains("panic!(\"no: {e}\")"))
        .expect("the golden has a panic arm");
    assert_eq!(
        before[panic_line], after[panic_line],
        "the panic arm's line moved"
    );
    assert_eq!(
        before[panic_line].find("panic!"),
        after[panic_line].find("panic!"),
        "the `panic!`'s column moved"
    );

    // ... and the test measures something: the arm three lines above it, which
    // IS probed, did change.
    let propagate_line = before
        .iter()
        .position(|l| l.trim() == "Err(e) => Err(e),")
        .expect("the golden has a propagating arm");
    assert_ne!(before[propagate_line], after[propagate_line]);
}

#[test]
fn a_bound_name_that_escapes_writes_arm_ambiguous() {
    let t = run("err_arm_escaped", 7);
    assert_eq!(
        err_sites(&t),
        [
            // Pushed into a `Vec`, handed to a fn by value, assigned into an
            // `Option`: three shapes a SWALLOWED verdict would be a false
            // accusation on.
            (11, "stored", 20, SiteKind::Arm, "arm_ambiguous"),
            (13, "handed_over", 31, SiteKind::Arm, "arm_ambiguous"),
            (15, "remembered", 42, SiteKind::Arm, "arm_ambiguous"),
            // The R2 amendment of 2026-09-05: `format!` hands the arm the
            // rendered text, and here that text is what the function returns.
            (
                17,
                "rendered_into_value",
                55,
                SiteKind::Arm,
                "arm_ambiguous"
            ),
            // The control: a LOGGING macro's bare argument and a shared borrow
            // are the only two uses design R2 still calls provable.
            (19, "printed", 64, SiteKind::Arm, "arm_handled"),
        ]
    );
    let c = census(&read("err_arm_escaped", "in"));
    assert_eq!(
        (
            c.arms_propagate,
            c.arms_panic,
            c.arms_escaped,
            c.arms_handled
        ),
        (0, 0, 4, 1)
    );
}

#[test]
fn an_if_let_err_body_is_classified_exactly_as_an_arm_is() {
    let t = run("if_let_err", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 4, RetKind::Value),
            (8, "note", 8, RetKind::Unit),
            (9, "bound", 11, RetKind::Unit),
            (11, "unbound", 18, RetKind::Value),
            (13, "propagating", 27, RetKind::Value),
        ]
    );
    assert_eq!(
        err_sites(&t),
        [
            (10, "bound", 12, SiteKind::Arm, "arm_handled"),
            (12, "unbound", 19, SiteKind::Arm, "arm_handled"),
            (14, "propagating", 28, SiteKind::Arm, "arm_propagate"),
        ]
    );
    // The `else` branch of `unbound` is not an `Err` body: exactly one probe
    // went into that function, and it went into the `then`.
    assert_eq!(t.source.matches("err_site_unbound(").count(), 1);
}

// ---------------------------------------------------------------------------
// Closures
// ---------------------------------------------------------------------------

#[test]
fn a_closure_holding_a_question_mark_gets_its_own_frame() {
    let t = run("closure_try", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 6, RetKind::Value),
            (8, "block_body", 12, RetKind::Value),
            (11, "expression_body", 23, RetKind::Value),
            (14, "two_of_them", 29, RetKind::Value),
            (19, "returning", 39, RetKind::Value),
        ]
    );
    assert_eq!(
        closure_sites(&t),
        [
            (9, "block_body::{{closure}}#1", 13),
            (12, "expression_body::{{closure}}#1", 24),
            // `plain` on line 31 holds no `?` and takes no number: `b` is #2.
            (15, "two_of_them::{{closure}}#1", 30),
            (17, "two_of_them::{{closure}}#2", 32),
            // An expression body holding a `return`: the `return` operand and
            // the tail are both this closure's exits.
            (20, "returning::{{closure}}#1", 40),
        ]
    );
    // Invariant 4: a `?` inside a framed closure belongs to the CLOSURE's
    // qualname, not to the fn around it.
    assert_eq!(
        err_sites(&t),
        [
            (10, "block_body::{{closure}}#1", 14, SiteKind::Try, "try"),
            (
                13,
                "expression_body::{{closure}}#1",
                24,
                SiteKind::Try,
                "try"
            ),
            (16, "two_of_them::{{closure}}#1", 30, SiteKind::Try, "try"),
            (18, "two_of_them::{{closure}}#2", 32, SiteKind::Try, "try"),
            (21, "returning::{{closure}}#1", 40, SiteKind::Try, "try"),
        ]
    );
    assert!(t.partial.is_empty(), "{:?}", t.partial);
    assert_eq!(census(&read("closure_try", "in")).closures_framed, 5);
    // The `return` inside the last closure is that CLOSURE's exit, wrapped with
    // the closure's site and never with the fn's: two `ret(.., 20, ..)` calls,
    // one for the `return` operand and one for the tail.
    assert_eq!(
        t.source
            .matches("::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, 20,")
            .count(),
        2
    );
}

#[test]
fn a_closure_without_a_question_mark_is_left_exactly_as_it_was() {
    let t = run("closure_no_try", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "mapped", 6, RetKind::Value),
            (8, "nested", 10, RetKind::Value),
        ]
    );
    assert!(closure_sites(&t).is_empty(), "{:?}", closure_sites(&t));
    assert!(err_sites(&t).is_empty(), "{:?}", err_sites(&t));
    // Three closures in the file, none of them framed: exactly the two fn
    // guards were emitted.
    assert_eq!(t.source.matches("::sensorium_rt::enter(").count(), 2);
    assert_eq!(census(&read("closure_no_try", "in")).closures_framed, 0);
}

#[test]
fn a_question_mark_in_an_async_block_is_declared_and_the_closure_beside_it_is_not() {
    let t = run("async_block_try", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 10, RetKind::Value),
            (8, "later", 14, RetKind::Value),
            (9, "closure_inside", 21, RetKind::Value),
            (12, "async_closure", 31, RetKind::Value),
        ]
    );
    // Neither the async BLOCK nor the async CLOSURE is a frame, and the `?` in
    // each is declared rather than wrapped.
    assert_eq!(
        partials(&t),
        [
            (16, "later", SiteKind::Try, "async-block"),
            (32, "async_closure", SiteKind::Try, "async-block"),
        ]
    );
    // The closure INSIDE the second async block is framed anyway: its body runs
    // when it is called, on the caller's thread.
    assert_eq!(
        closure_sites(&t),
        [(10, "closure_inside::{{closure}}#1", 23)]
    );
    assert_eq!(
        err_sites(&t),
        [(
            11,
            "closure_inside::{{closure}}#1",
            23,
            SiteKind::Try,
            "try"
        )]
    );
    let c = census(&read("async_block_try", "in"));
    assert_eq!((c.async_partials, c.closures_framed, c.try_syn), (2, 1, 3));
}

// ---------------------------------------------------------------------------
// The marks
// ---------------------------------------------------------------------------

#[test]
fn test_and_main_marks_are_written_where_design_r1b_says() {
    let t = run_role("test_marks", 7, BIN_ROOT);
    assert_eq!(
        sites(&t),
        [
            (7, "main", 7, RetKind::Unit),
            (8, "helper", 11, RetKind::Value),
            (9, "plain_test", 16, RetKind::Unit),
            (10, "qualified_test", 22, RetKind::Unit),
            (11, "inner::main", 29, RetKind::Value),
        ]
    );
    assert_eq!(
        marked(&t),
        [
            ("main", false, true),
            ("plain_test", true, false),
            ("qualified_test", true, false),
        ],
        "a `main` inside a module is an ordinary fn and `helper` is not a test"
    );
}

#[test]
fn a_lib_root_has_no_main_mark_at_all() {
    // `is_bin_root` is the driver's knowledge and the default is the honest
    // one: a caller that does not know the crate type marks nothing.
    let t = run_role("test_marks", 7, LIB_ROOT);
    assert_eq!(
        marked(&t),
        [("plain_test", true, false), ("qualified_test", true, false)]
    );
}

#[test]
fn the_marks_change_no_byte_of_the_source() {
    // They are facts about the manifest row, never about the rewrite -- which
    // is why one `.out.rs` serves both roles.
    let lib = run_role("test_marks", 7, LIB_ROOT);
    let bin = run_role("test_marks", 7, BIN_ROOT);
    assert_eq!(lib.source, bin.source);
}

// ---------------------------------------------------------------------------
// The census identities, per golden
// ---------------------------------------------------------------------------

#[test]
fn every_golden_classifies_exactly_the_arms_and_closures_it_probes() {
    // The counters and the sites come from ONE decision each, so these are
    // identities and not comparisons of two measurements: an arm that was
    // classified and not probed (or the reverse) shows up here.
    let mut with_arms = 0usize;
    let mut with_closures = 0usize;
    let mut with_async = 0usize;
    for case in common::CASES {
        let source = read(case, "in");
        let c = census(&source);
        let t = run_role(case, 7, LIB_ROOT);
        let kinds = |k: SiteKind| t.sites.iter().filter(|s| s.kind == k).count();
        let probed = c.arms_propagate + c.arms_escaped + c.arms_handled;
        assert_eq!(
            probed,
            kinds(SiteKind::Arm),
            "{case}: {probed} classified arms against {} arm sites (panic arms: {})",
            kinds(SiteKind::Arm),
            c.arms_panic
        );
        assert_eq!(
            c.closures_framed,
            kinds(SiteKind::Closure),
            "{case}: framed closures and closure sites disagree"
        );
        let declared = t
            .partial
            .iter()
            .filter(|p| p.reason == "async-block")
            .count();
        assert_eq!(
            c.async_partials, declared,
            "{case}: `?` in an async block, counted and declared, disagree"
        );
        with_arms += usize::from(probed + c.arms_panic > 0);
        with_closures += usize::from(c.closures_framed > 0);
        with_async += usize::from(c.async_partials > 0);
    }
    assert!(with_arms >= 3, "only {with_arms} goldens have an `Err` arm");
    assert!(
        with_closures >= 2,
        "only {with_closures} goldens have a framed closure"
    );
    assert_eq!(with_async, 1, "one golden has a `?` in an async block");
}
