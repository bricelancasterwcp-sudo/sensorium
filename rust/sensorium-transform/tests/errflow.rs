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
            (16, "returned", 32, RetKind::Value),
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
            // A `return` operand meets both wraps exactly as a tail does.
            (17, "returned", 34, SiteKind::Try, "try"),
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
        [
            (10, "printed", SiteKind::Try, "macro-arg"),
            (17, "both", SiteKind::Try, "macro-arg"),
        ]
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
fn a_place_expression_receiver_is_wrapped_like_any_other() {
    // Design R2 as amended 2026-09-04: all four written sinks take `self` BY
    // VALUE, so the call moves the receiver exactly as the wrap does -- an
    // E0507 the wrap could cause is one the sink caused already.
    // `tests/oracle.rs::a_place_receiver_is_not_the_e0507_the_predicates_are`
    // is the measurement; this is the placement.
    let t = run("sink_place_receiver", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "returns_ref_result", 15, RetKind::Value),
            (8, "Holder::defaulted", 22, RetKind::Value),
            (10, "indexed", 27, RetKind::Value),
            (12, "dereferenced", 33, RetKind::Value),
            (14, "a_local", 37, RetKind::Value),
            (16, "ref_result", 44, RetKind::Unit),
            (18, "place_let", 49, RetKind::Unit),
        ]
    );
    assert_eq!(
        err_sites(&t),
        [
            // A field behind `&self`, a slice index, a deref inside the
            // source's own parentheses, an owned local ...
            (9, "Holder::defaulted", 23, SiteKind::Sink, "sink_unwrap_or"),
            (11, "indexed", 28, SiteKind::Sink, "sink_unwrap_or"),
            (13, "dereferenced", 34, SiteKind::Sink, "sink_unwrap_or"),
            (15, "a_local", 38, SiteKind::Sink, "sink_unwrap_or"),
            // ... and design R16's `&Result<T, E>` blind spot, which compiles
            // and records nothing.
            (17, "ref_result", 45, SiteKind::Sink, "sink_let_underscore"),
        ]
    );
    // Nothing is declined here any more: the `sink-place` reason is retired.
    assert!(t.partial.is_empty(), "{:?}", t.partial);
    // `let _ = r;` on a place is still left alone -- `_` does not bind.
    assert_eq!(t.source.matches("::sensorium_rt::err_site(").count(), 5);
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
                .matches("#![allow(clippy::match_single_binding, clippy::needless_borrow)]")
                .count(),
            1,
            "{case}: exactly one crate-root allow, naming BOTH lints the wrap \
             provokes"
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
        // A `struct-literal` row can mark a sink as well as a `?`, so the
        // subtraction is over the rows whose KIND is `try` -- which is what
        // `Partial::kind` is on the row for. `async-block` joined it in rung 3
        // (task 3): a `?` inside a future IS a `syn::ExprTry`, so it is in
        // `try_syn` and has to be subtracted by name like any other decline.
        let unreached = t
            .partial
            .iter()
            .filter(|p| {
                p.kind == SiteKind::Try && matches!(p.reason, "struct-literal" | "async-block")
            })
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

// ---------------------------------------------------------------------------
// The struct-literal fence, and the crate root's inner attributes
// ---------------------------------------------------------------------------

#[test]
fn a_struct_literal_in_any_exterior_position_is_declared_not_wrapped() {
    // rustc forbids a struct literal in EVERY exterior position of a `match`
    // scrutinee, not just the leftmost, and a wrap that emitted one would give
    // the unit a file rustc rejects. The fence is a post-condition: the wrap is
    // re-parsed, and a site whose wrap does not parse is declared.
    let t = run("struct_literal_partial", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "C::go", 13, RetKind::Value),
            (8, "leftmost", 19, RetKind::Value),
            (9, "exterior", 27, RetKind::Unit),
            (10, "protected", 35, RetKind::Value),
        ]
    );
    // The ONE wrap in the file is the parenthesised fence.
    assert_eq!(err_sites(&t), [(11, "protected", 36, SiteKind::Try, "try")]);
    assert_eq!(
        partials(&t),
        [
            // The leftmost shape, which the fast path answers with no parse:
            // once as a `?` and once as a `let _`.
            (20, "leftmost", SiteKind::Try, "struct-literal"),
            (21, "leftmost", SiteKind::Sink, "struct-literal"),
            // The three the fast path cannot see: a binary operand, a range
            // end and a closure body.
            (28, "exterior", SiteKind::Sink, "struct-literal"),
            (29, "exterior", SiteKind::Sink, "struct-literal"),
            (30, "exterior", SiteKind::Sink, "struct-literal"),
        ]
    );
    // And the identity still closes: two `?` nodes, one wrapped and one
    // declared AS A `?`.
    assert_eq!(census(&read("struct_literal_partial", "in")).try_syn, 2);
}

#[test]
fn a_crate_root_with_real_inner_attributes_keeps_its_line_count() {
    // The allow goes just past the LAST inner attribute's `]`, on the line that
    // was already there. `#![deny(warnings)]` is the golden's own, so the
    // oracle compiles this file under a workspace-style deny.
    let t = run("crate_root_attrs", 7);
    assert_eq!(
        sites(&t),
        [(7, "f", 9, RetKind::Value), (9, "g", 14, RetKind::Value),]
    );
    assert_eq!(err_sites(&t), [(8, "f", 10, SiteKind::Try, "try")]);
    assert!(t
        .source
        .starts_with("#![deny(warnings)]\n#![allow(dead_code)] #![allow("));
}
