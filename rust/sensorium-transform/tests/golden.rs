//! Golden pairs for the byte-offset splicer: one `.in.rs`/`.out.rs` pair per
//! rule, byte-exact, with the line count and a re-parse asserted on every one.
//!
//! The rung-1 and rung-2 rules are here; rung 3's err-flow cases are in
//! `tests/errflow.rs`, and `common::CASES` is what keeps the two files and the
//! directory in agreement.
//!
//! The placeholders every `.out.rs` is written with -- and the fragments they
//! expand to -- live in `tests/common/mod.rs`, so the text the transformer
//! emits is pinned by the TESTS and is never read back out of the
//! implementation under test. Change a fragment and every golden diff fails,
//! which is the point.
//!
//! **Every case is transformed as a crate root**, so every `.out.rs` is a
//! self-contained crate `tests/oracle.rs` can hand to the real rustc -- and
//! every one of them carries the crate-root `allow` (`@W`) as well as the unit
//! static.

mod common;

use common::{run, sites, FILE};

use sensorium_transform::{RetKind, Transformed};

fn skips(t: &Transformed) -> Vec<(&str, u32, &str)> {
    t.skipped
        .iter()
        .map(|s| (s.qualname.as_str(), s.line, s.reason))
        .collect()
}

fn spawns(t: &Transformed) -> Vec<(u32, bool, Option<&str>)> {
    t.spawns
        .iter()
        .map(|s| (s.line, s.wrapped, s.reason))
        .collect()
}

/// `(line, qualname, ordinal, wrapped, reason)`.
type SpawnName<'a> = (u32, &'a str, Option<u32>, bool, Option<&'a str>);

/// Every field of a spawn entry that names the task, in one tuple: the manifest
/// promises `qualname` on every entry and `ordinal` on exactly the wrapped ones,
/// so both are read here rather than assumed.
fn spawn_names(t: &Transformed) -> Vec<SpawnName<'_>> {
    t.spawns
        .iter()
        .map(|s| (s.line, s.qualname.as_str(), s.ordinal, s.wrapped, s.reason))
        .collect()
}

// ---------------------------------------------------------------------------
// The rung-1 shapes: where the guard and the static go
// ---------------------------------------------------------------------------

#[test]
fn free_fn() {
    let t = run("free_fn", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "add", 3, RetKind::Value),
            (8, "main_ish", 7, RetKind::Unit)
        ]
    );
    assert!(t.skipped.is_empty());
    assert!(t.spawns.is_empty());
    assert!(t.sites.iter().all(|s| s.file == FILE));
}

#[test]
fn impl_method() {
    let t = run("impl_method", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "Counter::new", 6, RetKind::Value),
            (8, "Counter::bump", 10, RetKind::Value),
            // `impl<T> Holder<T>` renders as the bare self type: no generics ...
            (9, "Holder::push", 21, RetKind::Unit),
            // ... and `impl self::deep::Nested` drops the path, which the
            // generic case cannot pin -- Python's `Type::method` (spec §5.4).
            (10, "Nested::pathed", 31, RetKind::Unit),
        ]
    );
}

#[test]
fn trait_default() {
    let t = run("trait_default", 7);
    // `fn name(&self) -> String;` has no body: not a site, and not a skip
    // either -- there is nothing there to instrument or to excuse.
    assert_eq!(sites(&t), [(7, "Greeter::greet", 4, RetKind::Value)]);
    assert!(t.skipped.is_empty());
}

#[test]
fn nested_fn_and_impl_inside_a_fn_body() {
    let t = run("nested_fn", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "outer", 1, RetKind::Value),
            (8, "outer::helper", 2, RetKind::Value),
            (9, "outer::Local::method", 9, RetKind::Value),
        ]
    );
}

#[test]
fn nested_mod() {
    let t = run("nested_mod", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "outer::top", 2, RetKind::Unit),
            (8, "outer::inner::deep", 5, RetKind::Value),
        ]
    );
}

#[test]
fn generic_fn() {
    let t = run("generic_fn", 7);
    // `where_clause`'s brace is on line 10; `firstlineno` is the `fn` keyword.
    assert_eq!(
        sites(&t),
        [
            (7, "show", 3, RetKind::Value),
            (8, "where_clause", 7, RetKind::Value)
        ]
    );
}

#[test]
fn unsafe_fn() {
    let t = run("unsafe_fn", 7);
    assert_eq!(sites(&t), [(7, "raw", 1, RetKind::Value)]);
    assert_eq!(skips(&t), [("later", 5, "async"), ("frozen", 9, "const")]);
}

#[test]
fn test_fn() {
    let t = run("test_fn", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "under_test", 1, RetKind::Value),
            (8, "tests::setup", 8, RetKind::Value),
            (9, "tests::it_works", 13, RetKind::Unit),
        ]
    );
}

#[test]
fn const_fn_is_skipped() {
    let t = run("const_fn", 7);
    assert_eq!(sites(&t), [(7, "runtime", 9, RetKind::Value)]);
    assert_eq!(skips(&t), [("limit", 1, "const"), ("doubled", 5, "const")]);
}

#[test]
fn extern_fn_is_skipped() {
    let t = run("extern_fn", 7);
    assert_eq!(sites(&t), [(7, "ordinary", 10, RetKind::Value)]);
    // The `fn abs(..);` inside `extern "C" { .. }` has no body at all, so it is
    // neither instrumented nor excused; only the `extern "C" fn` with a body is.
    assert_eq!(skips(&t), [("callback", 2, "extern")]);
}

#[test]
fn async_fn_is_skipped() {
    // A guard inside a future is dropped WITH the future -- possibly on another
    // thread, and never at the `.await` a reader would call a return. Spec §3.2
    // says the guard's Drop is the sole emitter of RETURN, so at this tier an
    // `async fn` is declared and left alone (plan decision D6).
    let t = run("async_fn", 7);
    assert_eq!(sites(&t), [(7, "sync_fn", 17, RetKind::Value)]);
    assert_eq!(
        skips(&t),
        [
            ("plain", 1, "async"),
            ("public", 5, "async"),
            ("S::method", 12, "async"),
        ]
    );
}

#[test]
fn macro_rules_body_is_skipped() {
    let t = run("macro_rules", 7);
    assert_eq!(sites(&t), [(7, "ordinary", 11, RetKind::Value)]);
    assert_eq!(skips(&t), [("make_fn!", 3, "macro")]);
}

#[test]
fn inner_attribute_at_body_start() {
    // `#![..]` must stay the first thing in the block: a guard spliced ahead of
    // it is E0752-class garbage rustc rejects, which would show up as a unit
    // falling back rather than as the transformer bug it is.
    let t = run("inner_attr", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "with_inner_attr", 1, RetKind::Value),
            (8, "two_inner_attrs", 7, RetKind::Unit),
        ]
    );
}

#[test]
fn an_inner_doc_comment_at_body_start_does_not_refuse_the_file() {
    // A doc comment reaches this code as an inner ATTRIBUTE whose bracket span
    // covers the comment TEXT, so the guard has to move past that line's
    // newline. Requiring the span to end on `]` rejected the whole file, which
    // is a build failure on legal Rust.
    let t = run("body_inner_doc", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "line_doc", 1, RetKind::Value),
            (8, "block_doc", 6, RetKind::Value),
        ]
    );
}

#[test]
fn body_starting_with_an_attribute_or_doc_comment() {
    let t = run("body_attr", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "with_inner_stmt_attr", 1, RetKind::Unit),
            (8, "with_doc_on_first_item", 7, RetKind::Unit),
        ]
    );
}

#[test]
fn empty_body() {
    let t = run("empty_body", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "nothing", 3, RetKind::Unit),
            (8, "Empty::also_nothing", 6, RetKind::Unit),
        ]
    );
}

#[test]
fn one_line_body() {
    let t = run("one_line_body", 7);
    assert_eq!(
        sites(&t),
        [(7, "f", 1, RetKind::Unit), (8, "g", 3, RetKind::Value)]
    );
}

#[test]
fn shebang_and_non_ascii_offsets() {
    // `syn::parse_file` strips the BOM and the shebang before `proc-macro2` ever
    // sees the text, so every span offset is short by that prefix; and
    // `Span::start().column` counts CHARS, not bytes. Either mistake mis-splices
    // this file.
    let t = run("shebang_utf8", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "ünïcödé", 4, RetKind::Value),
            (8, "after", 8, RetKind::Unit)
        ]
    );
}

#[test]
fn crate_root_static_lands_after_the_last_token() {
    // The file's last LINE is a comment. Appending there would comment the
    // static out; appending after the final newline would add a line. The last
    // TOKEN is the only point that is both.
    let t = run("crate_root", 7);
    assert_eq!(sites(&t), [(7, "root_fn", 3, RetKind::Value)]);
    assert!(t
        .source
        .ends_with("// Another one, and then a blank line.\n\n"));
}

#[test]
fn a_trailing_line_doc_comment_does_not_swallow_the_static() {
    // `proc-macro2` hands a `//!` doc comment back as tokens whose span covers
    // the comment TEXT, so "after the last token" is inside a line comment and
    // the static would be silently commented out -- the file parses, the line
    // count holds, and the unit is simply gone.
    for (case, appended) in [
        ("crate_root_docs", true),
        ("crate_root_docs2", true),
        ("crate_root_docs_todo", false),
    ] {
        let t = run(case, 7);
        assert!(t.sites.is_empty(), "{case}: no fns to instrument");
        assert_eq!(t.appended_line, appended, "{case}: appended_line");
    }
}

// ---------------------------------------------------------------------------
// The rung-2 shapes: which operands are wrapped, and which are not
// ---------------------------------------------------------------------------

#[test]
fn a_function_with_nothing_to_return_gets_no_wrap() {
    // `-> ()` and no return type are the same thing to this transformer, and
    // neither has an exit operand to probe (HONESTY §1). The `return;` in
    // `early_return_unit` has no expression, so there is nothing to wrap there
    // either.
    let t = run("unit_fn", 7);
    // The three `let _ = <literal>` sinks take 8, 10 and 12 from the same
    // counter, which is why the fn sites are not contiguous here.
    assert_eq!(
        sites(&t),
        [
            (7, "nothing", 3, RetKind::Unit),
            (9, "explicit_unit", 7, RetKind::Unit),
            (11, "early_return_unit", 11, RetKind::Unit),
        ]
    );
}

#[test]
fn a_never_returning_function_gets_no_wrap() {
    let t = run("never_fn", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "stop", 3, RetKind::Never),
            (8, "spin", 7, RetKind::Never)
        ]
    );
}

#[test]
fn ordinary_value_tails_are_wrapped() {
    let t = run("value_tail", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "literal", 4, RetKind::Value),
            (8, "call", 8, RetKind::Value),
            (9, "chain", 12, RetKind::Value),
            (10, "deref_coercion", 16, RetKind::Value),
            (11, "boxed", 20, RetKind::Value),
            (12, "generic", 24, RetKind::Value),
            (13, "optional", 28, RetKind::Value),
        ]
    );
}

#[test]
fn an_attribute_on_the_operand_stays_outside_the_wrap() {
    // `attribute_prefix_len` re-tokenises the operand rather than matching forty
    // `Expr` variants for their `attrs` field, so a doc comment -- which
    // `proc-macro2` hands back as the same two tokens -- is handled by the same
    // rule.
    let t = run("attr_operand", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one_attribute", 5, RetKind::Value),
            (8, "two_attributes", 10, RetKind::Value),
        ]
    );
    assert_eq!(t.source.matches("::sensorium_rt::ret(").count(), 2);
}

#[test]
fn a_struct_literal_tail_is_wrapped() {
    let t = run("struct_tail", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "Counter::new", 8, RetKind::Value),
            (8, "Counter::default", 14, RetKind::Value),
        ]
    );
}

#[test]
fn a_try_tail_is_wrapped() {
    let t = run("try_tail", 7);
    // 8 and 10 are the two `?` sites, minted between the fn sites.
    assert_eq!(
        sites(&t),
        [
            (7, "forwarded", 6, RetKind::Value),
            (9, "tail_is_try", 10, RetKind::Value),
        ]
    );
}

#[test]
fn a_macro_call_tail_that_does_not_diverge_is_wrapped() {
    // `format!` and `vec!` are ordinary expressions; only the four diverging
    // macro names are left alone. The third case is the brace-delimited
    // statement-macro spelling, which `syn` hands back as a `Stmt::Macro` rather
    // than as an expression -- a shape the tail walk has to handle on its own.
    let t = run("format_tail", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "formatted", 10, RetKind::Value),
            (8, "vector", 14, RetKind::Value),
            (9, "brace_macro_tail", 18, RetKind::Value),
        ]
    );
    // `macro_rules! pick` has no `fn` token in its body, so it declares nothing.
    assert!(t.skipped.is_empty());
}

#[test]
fn syntactically_diverging_tails_are_not_wrapped() {
    // Wrapping one of these makes the `ret` call itself unreachable, which rustc
    // reports under `-D warnings` (measured 2026-09-02) -- and the frame closes
    // `none`, which is what HONESTY §1 says it means.
    let t = run("diverging_tails", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "not_yet", 4, RetKind::Value),
            (8, "never_here", 8, RetKind::Value),
            (9, "no_impl", 12, RetKind::Value),
            (10, "boom", 16, RetKind::Value),
            (11, "leave", 20, RetKind::Value),
            (12, "stop_now", 24, RetKind::Value),
            (13, "tail_return", 28, RetKind::Value),
        ]
    );
    // Six tails left alone, and `tail_return`'s two `return` operands wrapped:
    // the exit wrap opens exactly twice in this whole file.
    assert_eq!(t.source.matches("::sensorium_rt::ret(").count(), 2);
}

#[test]
fn a_composite_every_arm_of_which_diverges_is_not_wrapped() {
    // Ruling F3. Wrapping one makes the `ret` call itself unreachable, which
    // rustc reports as `unreachable_code` under `-D warnings` -- a build error
    // under a workspace's own `#![deny(warnings)]`.
    let t = run("composite_diverging", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "both_branches_diverge", 8, RetKind::Value),
            (8, "every_arm_diverges", 16, RetKind::Value),
            (9, "a_block_whose_tail_diverges", 24, RetKind::Value),
            (
                10,
                "an_unsafe_block_whose_tail_diverges",
                31,
                RetKind::Value
            ),
            // 11 is the `let _ = abs(-1)` sink inside the fn above.
            (12, "nested_composites_diverge", 38, RetKind::Value),
        ]
    );
    assert_eq!(
        t.source.matches("::sensorium_rt::ret(").count(),
        0,
        "not one of these five operands may be wrapped"
    );
    // The bodiless `fn abs(..);` inside `extern "C" { .. }` is neither a site
    // nor a skip -- there is nothing there to instrument or to excuse.
    assert!(t.skipped.is_empty());
}

#[test]
fn one_value_carrying_arm_keeps_a_composite_wrapped() {
    // The fence for the rule above: `ret(.., match x { A => panic!(), B => 1 })`
    // is legal and warning-free, and `tests/oracle.rs` compiles this golden's
    // output under `-D warnings` to say so.
    let t = run("mixed_arms", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "one_arm_panics", 5, RetKind::Value),
            (8, "one_branch_exits", 12, RetKind::Value),
            (9, "an_if_without_else_is_not_the_tail", 20, RetKind::Value),
            (10, "a_block_whose_tail_is_a_value", 27, RetKind::Value),
            (11, "panic_free", 34, RetKind::Value),
            // A labelled block a `break '<label> <value>` can leave does not
            // diverge, however its tail ends -- so it is wrapped, and the
            // `break` is what says so.
            (
                12,
                "a_labelled_block_a_break_can_leave_is_wrapped",
                38,
                RetKind::Value
            ),
        ]
    );
    assert_eq!(
        t.source.matches("::sensorium_rt::ret(").count(),
        6,
        "every one of these six operands is ordinary and is wrapped"
    );
}

#[test]
fn a_bare_block_tail_is_wrapped_inside_its_braces() {
    // Ruling F3's other half: `ret(.., { e })` puts braces around a call
    // argument, which rustc reports as `unused_braces`. `{ ret(.., e) }` is the
    // same value and the same measurement with no braces added.
    let t = run("block_tail", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "bare_block", 13, RetKind::Value),
            (8, "nested_bare_blocks", 17, RetKind::Value),
            (
                9,
                "a_block_with_statements_is_wrapped_whole",
                21,
                RetKind::Value
            ),
            (10, "a_labelled_block_is_wrapped_whole", 28, RetKind::Value),
            // The label is the reason the descent stops here: this block IS one
            // unsemicoloned expression, and descending would put the wrap
            // inside braces a `break 'value 6` leaves without passing through
            // it -- an exit the frame would then close `none`.
            (
                11,
                "a_labelled_bare_block_is_wrapped_whole",
                37,
                RetKind::Value
            ),
        ]
    );
    // The descent stops at a block that has statements and at a labelled one:
    // both of those are wrapped whole, and neither trips the lint.
    assert!(t
        .source
        .contains("{ ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, 7"));
    assert!(t
        .source
        .contains("{{ ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, 8"));
    for site in [10, 11] {
        assert!(
            t.source
                .contains(&format!("{}'value: {{", common::ret_open(site))),
            "site {site}: a labelled block is wrapped WHOLE, never descended into"
        );
    }
}

#[test]
fn a_loop_tail_is_wrapped_only_when_a_break_gives_it_a_value() {
    let t = run("loop_tail", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "counted", 3, RetKind::Value),
            (8, "labelled", 13, RetKind::Value),
            (9, "inner_break_only", 25, RetKind::Value),
        ]
    );
    // `counted` and `labelled` are wrapped; `inner_break_only`'s only valued
    // `break` belongs to the INNER loop, so the outer one never produces a
    // value and is left alone.
    assert_eq!(t.source.matches("::sensorium_rt::ret(").count(), 2);
}

#[test]
fn every_return_at_closure_depth_zero_is_wrapped() {
    let t = run("return_in_blocks", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "in_if", 3, RetKind::Value),
            (8, "in_match", 10, RetKind::Value),
            (9, "in_loop", 18, RetKind::Value),
            (10, "in_nested_block", 27, RetKind::Value),
        ]
    );
    // Four `return`s and four tails.
    assert_eq!(t.source.matches("::sensorium_rt::ret(").count(), 8);
}

#[test]
fn a_return_inside_a_closure_or_an_async_block_is_not_wrapped() {
    // A closure gets no guard at this rung (spec §3.3's closure frames are rung
    // 3), and a `return` inside one leaves the CLOSURE. Wrapping it would stash
    // a capture the enclosing frame's guard would then take as its own.
    let t = run("return_in_closure", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "with_closure", 4, RetKind::Value),
            (8, "with_async_block", 14, RetKind::Value),
        ]
    );
    // The two tails, and neither of the two inner `return`s.
    assert_eq!(t.source.matches("::sensorium_rt::ret(").count(), 2);
}

// ---------------------------------------------------------------------------
// Spawn sites
// ---------------------------------------------------------------------------

#[test]
fn thread_spawn_is_rewritten_in_both_spellings() {
    let t = run("spawn_thread", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "fully_qualified", 5, RetKind::Value),
            (8, "imported", 10, RetKind::Value),
            // The `let _ = <spawn>` pair: the two `let` sinks take 10 and 11.
            (9, "discarded_handles", 16, RetKind::Unit),
        ]
    );
    assert_eq!(
        spawns(&t),
        [
            (6, true, None),
            (11, true, None),
            (17, true, None),
            (18, true, None),
        ]
    );
    assert!(t.spawns.iter().all(|s| s.file == FILE));
    // Kind ordering, pinned by bytes: an err wrap's `match ` opens on the same
    // byte the spawn callee's REPLACED range starts at, in both spellings, and
    // has to be spliced in first or `assemble` refuses the pair.
    assert_eq!(
        t.source
            .matches("match ::sensorium_rt::spawn_child(")
            .count(),
        2
    );
}

#[test]
fn spawn_shapes_that_are_left_alone_are_declared_with_a_reason() {
    // HONESTY §3: a spawn shape the transformer does not rewrite is declared,
    // not silently missed. `Command::spawn()` takes no argument and is not a
    // thread at all, so it is not a spawn site and is not listed.
    let t = run("spawn_shapes", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "builder", 6, RetKind::Value),
            (8, "scoped", 15, RetKind::Value),
            (9, "command_spawn_is_not_a_thread", 24, RetKind::Value),
        ]
    );
    assert_eq!(
        spawns(&t),
        [
            (9, false, Some("builder")),
            (17, false, Some("scoped")),
            (18, false, Some("method")),
        ]
    );
    assert!(
        !t.source.contains("spawn_child"),
        "none of these shapes may be rewritten"
    );
}

#[test]
fn a_spawn_site_is_named_by_its_enclosing_fn_and_its_ordinal() {
    // The seven shapes the name rule has to get right, plus a `Builder::spawn`
    // between two wrapped sites of one fn: it is declared, takes no ordinal,
    // and does not renumber the wrapped sites around it.
    let t = run("spawn_ordinals", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "a", 13, RetKind::Value),
            (8, "T::m", 23, RetKind::Value),
            (9, "outer", 35, RetKind::Value),
            (10, "outer::inner", 36, RetKind::Value),
            (11, "c", 42, RetKind::Value),
            (12, "X::drop", 48, RetKind::Unit),
            // The twins: two `fn fmt` for one self type, two sites, one
            // qualname. A `const`/`static` is not a fn item and is no site.
            (13, "T::fmt", 58, RetKind::Value),
            (14, "T::fmt", 65, RetKind::Value),
            (15, "tests::t", 95, RetKind::Unit),
        ]
    );
    assert_eq!(
        spawn_names(&t),
        [
            // Two wrapped sites in one fn, numbered in source order ...
            (14, "a", Some(1), true, None),
            // ... with a declared shape between them that consumes no ordinal.
            (16, "a", None, false, Some("builder")),
            (18, "a", Some(2), true, None),
            // An inherent method: `Type::method`, the manifest's own spelling.
            (24, "T::m", Some(1), true, None),
            // An associated const's initialiser: the CONST names it, not the
            // `impl` -- `T::F`, not `T` (and not shared with `T::m`).
            (30, "T::F", Some(1), true, None),
            // A fn item nested in a fn body.
            (37, "outer::inner", Some(1), true, None),
            // A closure pushes no scope: the spawn belongs to the fn item.
            (43, "c", Some(1), true, None),
            // A trait impl names the SELF TYPE, never the trait.
            (49, "X::drop", Some(1), true, None),
            // N6-iv: `Display::fmt` and `Debug::fmt` share `T::fmt`, so the
            // ordinals CONTINUE across the twins in source order.
            (59, "T::fmt", Some(1), true, None),
            (66, "T::fmt", Some(2), true, None),
            // Initialisers at file scope: a `static`, a `const`, a `static`
            // whose closure is nested in a slice of tuples, and a `static` in
            // an inline module. None is a fn item; each still names its child.
            (72, "F", Some(1), true, None),
            (77, "G", Some(1), true, None),
            (82, "TABLE", Some(1), true, None),
            (88, "m::H", Some(1), true, None),
            // An inline module.
            (96, "tests::t", Some(1), true, None),
        ]
    );
    // `F` the file-scope static and `T::F` the associated const are two
    // qualnames, not one: each child is named `F#1` and `T::F#1`.
    assert!(
        t.source.contains(r#"spawn_child("F#1", "#),
        "got: {}",
        t.source
    );
    assert!(
        t.source.contains(r#"spawn_child("T::F#1", "#),
        "got: {}",
        t.source
    );
}

#[test]
fn the_run_probes_are_goldens_too() {
    // They are compiled AND RUN by `tests/oracle.rs`; here they are held to the
    // same byte-exact, line-count and re-parse invariants as every other case.
    let t = run("run_drop_order", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "note", 10, RetKind::Unit),
            (8, "Noisy::drop", 17, RetKind::Unit),
            (9, "through_tail", 22, RetKind::Value),
            (10, "through_return", 29, RetKind::Value),
            (11, "main", 38, RetKind::Unit),
        ]
    );

    let t = run("run_mutex_guard", 7);
    assert_eq!(
        sites(&t),
        [
            (7, "try_from_another_thread", 8, RetKind::Value),
            (8, "held_across_tail", 13, RetKind::Value),
            (9, "temporary_in_tail", 19, RetKind::Value),
            (10, "main", 23, RetKind::Unit),
        ]
    );
    assert_eq!(spawns(&t), [(10, true, None)]);
}
