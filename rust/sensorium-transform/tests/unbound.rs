//! The unbind rule: which names a block-like statement's completion row says
//! went out of scope with it (design §5.2, R4, R5).
//!
//! A new file rather than more of `golden.rs` or `edges.rs`, both of which sit
//! within twelve lines of the repository's 800-line ceiling (R8).
//!
//! Every case here is a golden PAIR in `tests/golden_focus/`, so three links
//! carry each claim and no one of them alone would: the `.out.rs` is the
//! TEST's statement of the bytes -- written by hand from the rule before the
//! transform could emit them, and expanded through `common`'s `@B`, which
//! spells the fragment a second time; `run_focus` diffs it against the real
//! transform's output; and `oracle.rs` hands the same bytes to the real rustc
//! with `-D warnings`. The assertions below are the fourth thing, and they are
//! what makes a mutant's failure READ as the rule it broke rather than as a
//! wall of unified diff: each one names the unbind list its case is about.
//!
//! # What is NOT here, and why
//!
//! * A `let` inside a nested CLOSURE or `async` block. The LINE walk stops at
//!   both (`visit_expr_closure`, `visit_expr_async`), so no probe ever bound
//!   such a name and no row may say it died -- design §5.2's "a row that said
//!   a name went out of scope where none came in would be a row that invents".
//!   `focus_closure` is the standing fixture for the walk stopping there, and
//!   it gains no `line_unbinding` fragment:
//!   `exactly_these_focus_goldens_carry_an_unbinding_fragment` below is what
//!   says so, over the whole directory at once.
//! * A block-like expression that is not a STATEMENT -- the value block
//!   `let y = { let x = 1; x };`. `x` is bound by a probe (the walk reaches
//!   inner blocks at every depth) and there is no completion row to pop it,
//!   because the statement is a `Stmt::Local` and the rule runs on block-like
//!   STATEMENTS. Design §5.2 does not cover the shape; it is a stated gap and
//!   not a row this file invents. `focus_unbound_tail`'s `tailing` is its
//!   sibling in the same family -- a tail is not a statement either.

mod common;

use common::{run_focus, FOCUS_CASES};

use sensorium_transform::{Focus, Transformed};

fn run(case: &str) -> Transformed {
    let (_, focus) = FOCUS_CASES
        .iter()
        .find(|(name, _)| *name == case)
        .unwrap_or_else(|| panic!("{case} is not in common::FOCUS_CASES"));
    run_focus(case, 7, &Focus::parse(focus))
}

/// Every `line_unbinding` fragment's unbound list, in emission order, as the
/// source spells it: `["\"n\", \"big\""]` for one row naming two names.
///
/// Read off the emitted TEXT rather than off a site or a manifest, because the
/// text is what rustc compiles and what the recorder's names come from; a
/// structured accessor would be a second model of the fragment to keep in step.
fn unbound_lists(t: &Transformed) -> Vec<String> {
    t.source
        .match_indices("::sensorium_rt::line_unbinding(")
        .map(|(at, _)| {
            let tail = &t.source[at..];
            let open = tail
                .find("], &[")
                .expect("a line_unbinding fragment opens an unbound list");
            let close = tail[open..]
                .find("]);")
                .expect("a line_unbinding fragment closes its unbound list");
            tail[open + "], &[".len()..open + close].to_owned()
        })
        .collect()
}

/// How many plain `line(` probes a result carries. `line_unbinding(` does not
/// match it -- the two entry points are distinguishable by name, which is the
/// whole of R5's mechanism.
fn plain_lines(t: &Transformed) -> usize {
    t.source.matches("::sensorium_rt::line(").count()
}

// ---------------------------------------------------------------------------
// One shape per case
// ---------------------------------------------------------------------------

/// A plain block statement pops the `let`s of its own block.
#[test]
fn a_plain_block_unbinds_the_lets_of_its_own_block() {
    let t = run("focus_unbound_block");
    assert_eq!(unbound_lists(&t), ["\"x\""]);
}

/// An `if let`'s head pattern is popped by the statement that opened it --
/// the entry row bound `first`, and this is the row that says it ended.
#[test]
fn an_if_let_unbinds_its_head_pattern() {
    let t = run("focus_unbound_iflet");
    assert_eq!(unbound_lists(&t), ["\"first\""]);
}

/// The same rule read on a loop pattern. Dropping the head-pattern branch of
/// `unbound_of` leaves this case with no fragment at all.
#[test]
fn a_for_loop_unbinds_its_pattern() {
    let t = run("focus_unbound_for");
    assert_eq!(unbound_lists(&t), ["\"item\""]);
}

/// SOURCE ORDER (ruling P7): the arm's pattern, then the arm body's `let`.
/// The arm that binds nothing adds nothing.
#[test]
fn a_match_unbinds_each_arms_pattern_then_its_body_in_source_order() {
    let t = run("focus_unbound_match");
    assert_eq!(
        unbound_lists(&t),
        ["\"n\", \"big\""],
        "the arm pattern is written before the arm body's let, so it is listed first"
    );
}

/// R4: a shadowing block pops the name it shadowed. The row names `x` once,
/// and the reader's cost -- the outer `x` reported NOT IN SCOPE after it --
/// is design §5.5's, measured through the recorder by the corpus case.
#[test]
fn a_shadowing_block_pops_the_name_it_shadowed() {
    let t = run("focus_unbound_shadow");
    assert_eq!(unbound_lists(&t), ["\"x\""]);
}

/// A nested block-like statement unbinds its OWN. Recursing into it would put
/// `inner` on the outer block's row too, and this is the assertion that reads.
#[test]
fn a_nested_block_like_statement_unbinds_its_own_and_the_outer_row_is_not_told() {
    let t = run("focus_unbound_nested");
    assert_eq!(
        unbound_lists(&t),
        ["\"inner\"", "\"outer\""],
        "the inner `if`'s row carries `inner` and the block's row only `outer`"
    );
}

/// Ruling P13: an `else if` is the outer `if`'s `else_branch` EXPRESSION and
/// never a statement, so it has no completion row of its own and the outer
/// `if`'s row is the only one that can end the chain's names. The row walks
/// every link -- `p` from the head, `q` from the second link's `let`-chain,
/// `r` from its body, `s` from the final `else` -- in source order.
///
/// Under P7's withdrawn clause this row said `["p"]` alone and the other
/// three names were bound by rows nothing balanced.
#[test]
fn an_else_if_chain_is_unbound_by_the_outer_ifs_row_because_it_has_no_other() {
    let t = run("focus_unbound_elseif");
    assert_eq!(unbound_lists(&t), ["\"p\", \"q\", \"r\", \"s\""]);
}

/// A `cfg`'d `let` is neither a delta nor an unbind: the probe after it is
/// declined, so the name never entered, so no row may say it left.
#[test]
fn a_cfg_stripped_let_is_not_unbound_and_its_neighbour_still_is() {
    let t = run("focus_unbound_cfg");
    assert_eq!(unbound_lists(&t), ["\"b\""]);
    assert!(
        !t.source.contains("\"a\""),
        "no fragment may name the binding `cfg` took out of the build"
    );
}

/// R5, and the tail. A block with nothing to unbind keeps `line(...)` byte for
/// byte, and a block-like expression in TAIL position takes no completion row
/// at all -- so `tailing`'s `n` is bound by an entry row and popped by none.
#[test]
fn a_statement_with_nothing_to_unbind_keeps_the_line_fragment_and_a_tail_takes_no_row() {
    let t = run("focus_unbound_tail");
    assert_eq!(unbound_lists(&t), Vec::<String>::new());
    assert!(
        t.source
            .contains("::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 11, || []);"),
        "the block's own row is the fragment `line_fragment` has always written"
    );
    assert_eq!(
        plain_lines(&t),
        6,
        "two parameters rows, `plain`'s three statements, and `tailing`'s arm entry"
    );
}

// ---------------------------------------------------------------------------
// The rule's reach over the whole golden directory
// ---------------------------------------------------------------------------

/// Which focus goldens the rule reaches, named one by one.
///
/// Every other case in `tests/golden_focus/` is byte-identical to what it was
/// before 0.5.0, and its `.out.rs` says so by carrying no `@B`. This test is
/// what turns that from a thing someone checked once into a standing claim: a
/// widened rule that started emitting `line_unbinding` for, say, a closure's
/// `let` or a tail would have to add a case here to stay green.
#[test]
fn exactly_these_focus_goldens_carry_an_unbinding_fragment() {
    let mut reached: Vec<&str> = Vec::new();
    for (case, _) in FOCUS_CASES {
        if !unbound_lists(&run(case)).is_empty() {
            reached.push(case);
        }
    }
    assert_eq!(
        reached,
        [
            // The one pre-existing golden the rule reaches: a `for` statement
            // whose pattern binds. Expected, and named rather than absorbed.
            "focus_loop",
            "focus_unbound_block",
            "focus_unbound_cfg",
            "focus_unbound_elseif",
            "focus_unbound_for",
            "focus_unbound_iflet",
            "focus_unbound_match",
            "focus_unbound_nested",
            "focus_unbound_shadow",
        ]
    );
}
