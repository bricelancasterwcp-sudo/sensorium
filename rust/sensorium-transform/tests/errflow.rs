//! Golden pairs for rung 3's err-flow sites: every `?`, the four written sinks
//! and `let _ = <value expression>`, plus the shapes that are DECLARED instead
//! of wrapped.
//!
//! Same discipline as `tests/golden.rs` (which holds the rung-1 and rung-2
//! cases): the bytes are pinned by an `.out.rs` written with the placeholders
//! from `tests/common/mod.rs`, so the fragments are never read back out of the
//! implementation under test. `tests/oracle.rs` compiles every one of these at
//! `-D warnings`, which is what says the wrap is legal Rust and not just the
//! bytes the test expected.

mod common;

use common::{err_sites, partials, read, run, sites, FILE, META};

use sensorium_transform::{census, transform, RetKind, SiteKind};

// ---------------------------------------------------------------------------
// `?`
// ---------------------------------------------------------------------------

#[test]
fn every_question_mark_is_wrapped_around_its_operand() {
    let t = run("try_stmt", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 5, RetKind::Value),
            (8, "discard", 9, RetKind::Value),
            (10, "bound", 14, RetKind::Value),
            (12, "parenthesised", 21, RetKind::Value),
        ]
    );
    // Statement position, `let` position, and one inside its own parentheses:
    // three `?`, three sites, each on the `?`'s own line.
    assert_eq!(
        err_sites(&t),
        [
            (9, "discard", 10, SiteKind::Try, "try"),
            (11, "bound", 15, SiteKind::Try, "try"),
            (13, "parenthesised", 22, SiteKind::Try, "try"),
        ]
    );
    assert!(t.partial.is_empty());
}

#[test]
fn an_err_wrap_nests_inside_an_exit_wrap_and_inside_itself() {
    // The splice ORDER, pinned by bytes: at one offset an exit wrap opens
    // before an err wrap and closes after it, and two err wraps opened on one
    // byte close innermost-first. `run` is a byte-exact diff, so the `.out.rs`
    // is the assertion; these are the site numbers that go with it.
    let t = run("try_tail_and_stmt", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 5, RetKind::Value),
            (8, "twice", 9, RetKind::Value),
            (9, "wrapped_tail", 14, RetKind::Value),
            (11, "try_is_the_tail", 19, RetKind::Value),
            (13, "nested_try", 25, RetKind::Value),
        ]
    );
    assert_eq!(
        err_sites(&t),
        [
            (10, "wrapped_tail", 15, SiteKind::Try, "try"),
            (12, "try_is_the_tail", 20, SiteKind::Try, "try"),
            // The OUTER `?` is met first and takes the lower number; the inner
            // one closes first.
            (14, "nested_try", 26, SiteKind::Try, "try"),
            (15, "nested_try", 26, SiteKind::Try, "try"),
        ]
    );
}

#[test]
fn a_question_mark_on_an_option_is_wrapped_like_any_other() {
    // The transformer cannot see types, so the site exists; design R2's "an
    // `Option::None` writes nothing" is the RUNTIME ladder's job, and
    // `sensorium-rt`'s `the_ladder_reads_nothing_at_all_from_a_non_result` is
    // where that half is pinned.
    let t = run("try_option", 7);
    assert_eq!(err_sites(&t), [(9, "chained", 10, SiteKind::Try, "try")]);
    assert!(t.partial.is_empty());
}

#[test]
fn a_question_mark_inside_a_macro_argument_is_declared_not_wrapped() {
    let t = run("try_in_macro_arg", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 5, RetKind::Value),
            (8, "printed", 9, RetKind::Value),
            (9, "both", 16, RetKind::Value),
        ]
    );
    // One real `?` node, and two `?` TOKENS inside `println!` arguments that no
    // node exists for.
    assert_eq!(err_sites(&t), [(10, "both", 18, SiteKind::Try, "try")]);
    assert_eq!(
        partials(&t),
        [(10, "printed", "macro-arg"), (17, "both", "macro-arg"),]
    );
}

// ---------------------------------------------------------------------------
// Sinks
// ---------------------------------------------------------------------------

#[test]
fn the_four_written_sinks_are_wrapped_at_their_receiver() {
    let t = run("sinks", 7);
    assert_eq!(
        err_sites(&t),
        [
            (9, "dropped", 9, SiteKind::Sink, "sink_ok"),
            (11, "defaulted", 13, SiteKind::Sink, "sink_unwrap_or"),
            (13, "lazily", 17, SiteKind::Sink, "sink_unwrap_or"),
            (15, "zeroed", 21, SiteKind::Sink, "sink_unwrap_or"),
        ]
    );
    // `.is_err()`, `.is_ok()` and a workspace's own `ok(1)` are none of them:
    // not wrapped, and not declared either -- there is no sink there to miss.
    assert!(t.partial.is_empty(), "{:?}", t.partial);
    assert_eq!(t.source.matches("::sensorium_rt::err_site(").count(), 4);
}

#[test]
fn a_place_expression_receiver_is_declared_rather_than_wrapped() {
    let t = run("sink_place_receiver", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "returns_ref_result", 11, RetKind::Value),
            (8, "Holder::defaulted", 19, RetKind::Value),
            (9, "indexed", 24, RetKind::Value),
            (10, "dereferenced", 28, RetKind::Value),
            (11, "a_local", 32, RetKind::Value),
            (12, "ref_result", 39, RetKind::Unit),
            (14, "place_let", 44, RetKind::Unit),
        ]
    );
    // The one wrap in the file is the `let _` on a CALL -- design R16's
    // `&Result<T, E>` blind spot, which compiles and records nothing.
    assert_eq!(
        err_sites(&t),
        [(13, "ref_result", 40, SiteKind::Sink, "sink_let_underscore")]
    );
    assert_eq!(
        partials(&t),
        [
            (20, "Holder::defaulted", "sink-place"),
            (25, "indexed", "sink-place"),
            (29, "dereferenced", "sink-place"),
            (33, "a_local", "sink-place"),
        ]
    );
    // `let _ = r;` is not among them: `_` does not bind, so that statement
    // moves nothing, drops nothing and absorbs no error.
    assert!(t.partial.iter().all(|p| p.line != 45));
}

#[test]
fn let_underscore_wraps_a_value_and_leaves_a_place_alone() {
    let t = run("let_underscore", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one", 4, RetKind::Value),
            (8, "discarded", 8, RetKind::Unit),
            (10, "literal", 14, RetKind::Unit),
            (12, "places", 19, RetKind::Unit),
            (13, "typed", 31, RetKind::Unit),
            (14, "both", 36, RetKind::Value),
        ]
    );
    assert_eq!(
        err_sites(&t),
        [
            (9, "discarded", 9, SiteKind::Sink, "sink_let_underscore"),
            (11, "literal", 15, SiteKind::Sink, "sink_let_underscore"),
            // The `let` wrap is opened first and so is the OUTER of the two.
            (15, "both", 37, SiteKind::Sink, "sink_let_underscore"),
            (16, "both", 37, SiteKind::Try, "try"),
        ]
    );
    // Three places and one `let _: T =` left alone, none of them declared.
    assert!(t.partial.is_empty(), "{:?}", t.partial);
}

// ---------------------------------------------------------------------------
// The crate-root allow
// ---------------------------------------------------------------------------

#[test]
fn the_crate_root_carries_the_allow_the_wraps_need() {
    // Every wrap is a `match` with one binding, which is what
    // `clippy::match_single_binding` is about. The attribute goes on the crate
    // ROOT because a wrap in any file of the unit is what needs it -- so it is
    // emitted even for a file with no wrap at all.
    for case in ["try_stmt", "sinks", "free_fn", "never_fn"] {
        let t = transform(&read(case, "in"), FILE, META, 7, true)
            .unwrap_or_else(|e| panic!("{case}: {e}"));
        assert_eq!(
            t.source
                .matches("#![allow(clippy::match_single_binding)]")
                .count(),
            1,
            "{case}: exactly one crate-root allow"
        );
    }
    // ... and only on the crate root: a module file of the same unit inherits
    // the attribute from the root and must not repeat it.
    let t = transform(&read("try_stmt", "in"), FILE, META, 7, false).expect("transform");
    assert!(!t.source.contains("match_single_binding"));
}

// ---------------------------------------------------------------------------
// The census identity, per golden
// ---------------------------------------------------------------------------

#[test]
fn every_golden_wraps_exactly_the_question_marks_the_census_counts() {
    // Invariant 6, on every case: the `try` rows and `census().try_syn` are the
    // same set by construction (one walk, one `visit_expr_try`), and the
    // `macro-arg` rows are the `?` TOKENS the census counts separately --
    // disjoint from `try_syn`, because no `ExprTry` node exists for them.
    let mut with_try = 0usize;
    let mut with_macro = 0usize;
    for case in common::CASES {
        let source = read(case, "in");
        let c = census(&source);
        let t = transform(&source, FILE, META, 7, true).unwrap_or_else(|e| panic!("{case}: {e}"));
        let try_rows = t.sites.iter().filter(|s| s.kind == SiteKind::Try).count();
        let macro_rows = t.partial.iter().filter(|p| p.reason == "macro-arg").count();
        let unreached = t
            .partial
            .iter()
            .filter(|p| p.reason == "struct-literal")
            .count();
        assert_eq!(
            try_rows + unreached,
            c.try_syn,
            "{case}: try rows {try_rows} + unreached {unreached} != try_syn {}",
            c.try_syn
        );
        assert_eq!(
            macro_rows, c.try_macro_tokens,
            "{case}: macro-arg rows {macro_rows} != try_macro_tokens {}",
            c.try_macro_tokens
        );
        with_try += usize::from(try_rows > 0);
        with_macro += usize::from(macro_rows > 0);
    }
    assert!(with_try >= 5, "only {with_try} goldens have a `?`");
    assert_eq!(with_macro, 1, "one golden has a `?` in a macro argument");
}

// ---------------------------------------------------------------------------
// The run probe
// ---------------------------------------------------------------------------

#[test]
fn the_err_run_probe_is_a_golden_too() {
    // Compiled AND RUN by `tests/oracle.rs`, transformed and not, with the
    // printed lines compared: that is where "the wrap moved no `Drop`" is
    // measured rather than argued.
    let t = run("run_err_drop_order", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "Noisy::drop", 13, RetKind::Unit),
            (8, "Noisy::value", 19, RetKind::Value),
            (9, "side", 25, RetKind::Value),
            (10, "through_try", 30, RetKind::Value),
            (12, "through_sink", 36, RetKind::Value),
            (14, "through_let", 42, RetKind::Unit),
            (16, "main", 47, RetKind::Unit),
        ]
    );
    assert_eq!(
        err_sites(&t),
        [
            (11, "through_try", 31, SiteKind::Try, "try"),
            (13, "through_sink", 37, SiteKind::Sink, "sink_unwrap_or"),
            (15, "through_let", 43, SiteKind::Sink, "sink_let_underscore"),
        ]
    );
}
