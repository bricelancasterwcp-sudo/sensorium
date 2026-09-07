//! The focus tier: which functions are selected, where a LINE probe goes, what
//! it carries, and what a manifest says about all of it.
//!
//! Golden pairs live in `tests/golden_focus/`, apart from `tests/golden/`,
//! because five other tests transform every case in THAT directory with no focus
//! and require the bytes not to move. Keeping the focused cases out of it is
//! what lets "an empty focus is byte-identical to the build before this task"
//! stay a measurement rather than a promise.
//!
//! The probe's text is written a second time in `tests/common/mod.rs` (`@N`), so
//! the bytes these goldens pin are the TEST's statement of what amendment A7
//! says and never a read-back of `lines::line_fragment`.

mod common;

use std::collections::BTreeSet;

use common::{
    err_sites, line_sites, read_focus, run_focus, sites, COMPILE_FAIL_CASES, FOCUS_CASES, META,
};

use sensorium_transform::{transform, Focus, Manifest, RetKind, SiteKind};

/// Every case's focus value, by name.
fn focus_for(case: &str) -> Focus {
    let (_, value) = FOCUS_CASES
        .iter()
        .find(|(name, _)| *name == case)
        .unwrap_or_else(|| panic!("{case} is not in common::FOCUS_CASES"));
    Focus::parse(value)
}

fn run(case: &str) -> sensorium_transform::Transformed {
    run_focus(case, 7, &focus_for(case))
}

// ---------------------------------------------------------------------------
// Where a probe goes, and what it carries
// ---------------------------------------------------------------------------

#[test]
fn a_focused_fn_mints_a_parameters_line_and_one_line_per_statement() {
    let t = run("focus_fill");
    assert_eq!(sites(&t), [(7, "fill", 3, RetKind::Unit)]);
    assert_eq!(
        line_sites(&t),
        [
            // The parameters LINE is at the `fn` line, like the fn's own site.
            (8, "fill", 3),
            (9, "fill", 4),
            (10, "fill", 5),
            (11, "fill", 6),
        ]
    );
}

#[test]
fn a_loop_pattern_enters_the_body_and_a_compound_assignment_writes_its_left() {
    let t = run("focus_loop");
    assert_eq!(sites(&t), [(7, "sum_to_three", 5, RetKind::Value)]);
    assert_eq!(
        line_sites(&t),
        [
            (8, "sum_to_three", 5),
            (9, "sum_to_three", 6),
            // The loop-entry probe is at the `for` line, once per iteration ...
            (10, "sum_to_three", 7),
            (11, "sum_to_three", 8),
            // ... and the loop is itself a statement, whose LINE is also the
            // `for` line but is spliced past the body's closing brace.
            (12, "sum_to_three", 7),
        ]
    );
}

#[test]
fn an_arm_that_binds_gets_an_entry_line_and_an_arm_that_does_not_gets_none() {
    let t = run("focus_match");
    // Four LINEs for five arm-ish places: the `match` is the fn's TAIL and is
    // not a statement, and `None => {}` binds nothing (amendment A3).
    assert_eq!(
        line_sites(&t),
        [
            (8, "classify", 5),
            (9, "classify", 7),
            (10, "classify", 8),
            (11, "classify", 9),
        ]
    );
    assert_eq!(t.source.matches("::sensorium_rt::line(").count(), 4);
}

#[test]
fn a_bare_expression_arm_body_is_wrapped_in_a_block_amendment_a1() {
    let t = run("focus_arm_bare");
    assert_eq!(
        line_sites(&t),
        [(8, "pick", 6), (9, "pick", 8)],
        "the parameters LINE and the one arm that binds"
    );
    // The block the wrap added is the arm's value, and the exit wrap is INSIDE
    // it: `Some(n) => { <probe> ret(.., n * 2) }` would be the shape if the
    // operand were per-arm. It is not -- the whole `match` is the operand -- so
    // the two never share a byte, which is what this pins.
    assert!(t.source.contains("Some(n) => { ::sensorium_rt::line("));
    assert!(t.source.contains("n * 2 },"));
}

/// Final review, item 3. `let x;` writes nothing at its own line -- the guard
/// is `statement_deltas`'s `local.init.is_some()` -- and the binding appears at
/// the assignment instead. The two assertions below pin BOTH halves, because a
/// guard that dropped the row entirely would also satisfy "no `x` at line 10".
///
/// The build-breaking direction is why this is a golden PAIR and not an
/// assertion about `line_sites` alone, and it is carried by two links: this
/// test pins the BYTES against the real transform's output, and `oracle.rs`
/// hands those same bytes to the real rustc. The mutant breaks the first link
/// (measured: red here and in `every_focus_case_numbers_its_sites_...`), and
/// its output compiled by hand gives `error[E0381]: used binding `x` is
/// possibly-uninitialized`. The oracle cannot be the one that catches it: it
/// compiles what is checked in, and a mutant changes what the transform
/// emits.
#[test]
fn a_let_with_no_initializer_writes_its_binding_at_the_assignment_instead() {
    let t = run("focus_deferred_init");
    assert_eq!(
        line_sites(&t),
        [
            (8, "deferred", 20),
            (9, "deferred", 21),
            (10, "deferred", 22),
            (11, "deferred", 23),
        ],
        "the declaration still takes a row: the line RAN"
    );
    assert!(
        t.source
            .contains("let x;::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 9, || []);"),
        "the declaration's probe names nothing"
    );
    assert!(
        t.source.contains(
            "x = 1;::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 10, \
             || [(\"x\", ::sensorium_rt::probe_cap!(&x))]);"
        ),
        "the assignment is where `x` is written, and where its delta belongs"
    );
}

#[test]
fn a_closure_inside_a_focused_fn_gets_no_probes() {
    let t = run("focus_closure");
    assert_eq!(line_sites(&t), [(8, "outer", 4), (9, "outer", 5)]);
    // Nothing between the closure's `{` and its `}`.
    let body = t
        .source
        .split_once("|x: i32| {")
        .expect("the closure is still there")
        .1;
    let closed = body.split_once("};").expect("the closure still closes").0;
    assert!(
        !closed.contains("::sensorium_rt::"),
        "a closure body carried instrumentation: {closed}"
    );
}

#[test]
fn parameters_are_read_including_a_receiver_and_a_destructured_pattern() {
    let t = run("focus_params");
    assert_eq!(
        sites(&t),
        [
            (7, "Counter::bump", 11, RetKind::Value),
            (10, "Counter::zero", 16, RetKind::Value),
        ],
        "the container value `Counter` selects both methods"
    );
    assert_eq!(
        line_sites(&t),
        [
            (8, "Counter::bump", 11),
            (9, "Counter::bump", 12),
            // Amendment A2: no parameters, and still a LINE.
            (11, "Counter::zero", 16),
        ]
    );
    assert!(t.source.contains(
        "|| [(\"self\", ::sensorium_rt::probe_cap!(&self)), \
         (\"lo\", ::sensorium_rt::probe_cap!(&lo)), \
         (\"hi\", ::sensorium_rt::probe_cap!(&hi))]"
    ));
    // `self.n += lo + hi;` is a PLACE write: the row says the line ran and
    // names nothing (design §3.2).
    assert!(t
        .source
        .contains("self.n += lo + hi;::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 9, || []);"));
}

#[test]
fn a_value_a_later_statement_moves_is_still_captured() {
    let t = run("focus_moved_value");
    assert_eq!(
        line_sites(&t),
        [
            (8, "move_it", 7),
            (9, "move_it", 8),
            (10, "move_it", 9),
            (11, "move_it", 10),
            (12, "move_it", 11),
            (13, "move_it", 12),
        ]
    );
    // `let w = v;` moves `v`, and the probe on the line before still borrowed
    // it. `tests/oracle.rs` compiles this output, which is the actual proof.
    assert!(t.source.contains("let w = v;::sensorium_rt::line("));
}

/// Ruling G1 (`sensorium-transform` 0.4.1). A BRACE-delimited macro that is a
/// block's tail takes no probe, because a tail is not a statement whichever syn
/// node spells it -- the same answer `Stmt::Expr(_, None)` already gives.
///
/// Four functions, because the guard has four distinguishable effects and one of
/// them is a NEGATIVE.
///
/// * `wrapped` and `spoken` are the two halves of the shape it repairs, and they
///   failed differently. In `wrapped` the LINE landed after the RETURN wrap's
///   closing paren -- `..., pick! { 1 })::sensorium_rt::line(..)` -- a PARSE
///   error that took the whole unit; in `spoken` there is no wrap to collide
///   with, so the extra LINE compiled and quietly recorded a completed statement
///   for what is the function's value.
/// * `declared` is the negative: a brace macro that is NOT a tail keeps its
///   probe, spliced after the closing brace and carrying no deltas (a macro's
///   expansion is not inspected). Widening the arm to `None` for every brace
///   macro passes every other assertion here; this one is what stops it.
/// * `looped` is a brace-macro tail of a NESTED block. Nothing claims a loop
///   body's tail as an operand -- only a FN body's tail is one -- so the reason
///   it takes no probe is the plainer half of the guard's justification, and the
///   count is what says so: three LINE sites before the guard, two after.
///
/// The LINE sites are derived, not read back. Per design §3.2 a focused fn mints
/// one parameters row plus one row per completed STATEMENT, and an entry probe
/// per binding site: `wrapped` and `spoken` mint parameters alone; `declared`
/// mints parameters and the non-tail macro; `looped` mints parameters and the
/// loop-entry row for `x`, its `for` being the fn body's own tail and its body's
/// tail being the macro. The loop-entry SITE is minted once and fires once per
/// iteration -- twice here -- which is a run-time count and not a site count.
///
/// `tests/oracle.rs::every_focus_golden_output_compiles_with_zero_diagnostics`
/// compiles the checked-in `.out.rs` with `-D warnings`; `run_focus` asserts
/// three lines below that the transform's output IS those bytes, and the two
/// together are what say the value half is repaired rather than re-spelled.
#[test]
fn a_brace_delimited_macro_in_tail_position_takes_no_line() {
    let t = run("focus_macro_tail");
    assert_eq!(
        sites(&t),
        [
            (7, "wrapped", 48, RetKind::Value),
            (9, "spoken", 52, RetKind::Unit),
            (11, "declared", 56, RetKind::Value),
            (14, "looped", 61, RetKind::Unit),
        ]
    );
    assert_eq!(
        line_sites(&t),
        [
            (8, "wrapped", 48),   // parameters, and nothing for the tail macro
            (10, "spoken", 52),   // parameters
            (12, "declared", 56), // parameters
            (13, "declared", 57), // the NON-tail macro keeps its probe
            (15, "looped", 61),   // parameters
            (16, "looped", 62),   // the loop entry binding `x`
        ]
    );
    // Positively: the non-tail brace macro's probe is spliced after its closing
    // brace and carries no deltas. This is the assertion a widened arm fails.
    assert!(t
        .source
        .contains("decl! { a }::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 13, || []);"));
    // And negatively, for the three tails -- the fn body's, the unit fn's, and
    // the loop body's: exactly one `}::sensorium_rt::line(` in the whole file,
    // and it belongs to `decl!`.
    assert_eq!(t.source.matches("}::sensorium_rt::line(").count(), 1);
}

/// Fix round 1, I1. `exits::diverges` says a `loop` with no VALUED `break`
/// diverges, which is the right answer to "may this operand be wrapped" and the
/// wrong one to "does this statement complete". Before the repair this fn's
/// `loop` and everything the reviewer measured -- the `if`, the `n += 1;` and
/// the loop's own row -- were simply absent.
#[test]
fn a_loop_a_plain_break_leaves_completes_and_takes_its_line() {
    let t = run("focus_loop_break");
    assert_eq!(
        line_sites(&t),
        [
            (8, "wait_then", 7),   // parameters
            (9, "wait_then", 8),   // let mut n = a;
            (10, "wait_then", 10), // the `if` statement, past its `}`
            (11, "wait_then", 13), // n += 1;
            (12, "wait_then", 9),  // the `loop` STATEMENT, past its `}`
            (13, "wait_then", 15), // let b = n + 1;
            // `spins`: the parameters LINE and NOTHING else -- see below.
            (15, "spins", 24),
            (17, "labelled", 34), // parameters
            (18, "labelled", 37), // n += 1; inside the INNER loop
            (19, "labelled", 35), // the labelled loop STATEMENT, past its `}`
            (20, "labelled", 41), // let b = n;
        ]
    );
    // The `break;` itself takes none: a probe after it is unreachable code.
    assert!(t.source.contains("break;\n"));
    assert!(t
        .source
        .contains("    }::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 12, || []);"));
}

/// Fix round 2, F1. The depth rule in the break walk -- an UNLABELLED `break`
/// belongs to the innermost loop -- is the one direction that breaks a build if
/// it is wrong: read it as "any break counts" and `loop { loop { break; } }`
/// reads as completing, a probe lands after a statement of type `!`, and the
/// unit fails `-D warnings`. `spins` is that shape and `oracle.rs` compiles it;
/// `labelled` is the control that a `break 'o` from inside the inner loop DOES
/// leave the outer one.
#[test]
fn an_unlabelled_break_belongs_to_the_innermost_loop_and_a_labelled_one_does_not() {
    let t = run("focus_loop_break");
    let spins: Vec<_> = line_sites(&t)
        .into_iter()
        .filter(|(_, q, _)| *q == "spins")
        .collect();
    assert_eq!(
        spins,
        [(15, "spins", 24)],
        "the outer loop never completes: only the parameters LINE"
    );
    assert!(
        t.source.contains("    };\n}"),
        "nothing may follow a `!` statement"
    );
    // The labelled loop DOES complete, so its own LINE sits past its `}`.
    assert!(t
        .source
        .contains("    }::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 19, || []);"));
}

/// Fix round 2, F2. `syn::Expr` is `#[non_exhaustive]`, so `expr_attrs`'s
/// catch-all answers "no attributes" -- and a variant it forgot would take a
/// probe on a statement a `cfg` can strip. `RawAddr` was the one it forgot.
#[test]
fn a_cfg_on_a_raw_address_statement_declines_its_line() {
    let source = "static X: i32 = 1;\npub fn f() {\n    #[cfg(any())]\n    \
                  &raw const X;\n    let a = 1;\n}\n";
    let t = transform(source, "src/lib.rs", META, 7, true, &Focus::parse("f")).expect("transform");
    assert_eq!(
        line_sites(&t),
        [(8, "f", 2), (9, "f", 5)],
        "the parameters LINE and `let a = 1;` -- nothing for the `cfg`-able statement"
    );
}

/// Fix round 1, I2. Only `cfg`/`cfg_attr` can take the statement out of the
/// build, so only those decline its LINE; `#[allow(..)]` is far more common on
/// a statement and used to cost it its row and its delta.
#[test]
fn only_a_cfg_attribute_declines_a_statements_line() {
    let t = run("focus_attrs");
    assert_eq!(
        line_sites(&t),
        [
            (8, "attributed", 5),
            // The `let` line, not the `#[allow]` line above it.
            (9, "attributed", 7),
        ]
    );
    assert!(t.source.contains("let mut c = 3;::sensorium_rt::line("));
    assert!(
        t.source.contains("let d = 4;\n"),
        "a `cfg`-able statement takes no probe at all"
    );
}

/// Fix round 1, I3. The `?` keeps its err wrap and the statement's LINE goes
/// after the `;`, so the LINE runs only where the `?` did not propagate.
#[test]
fn a_try_statement_keeps_its_err_wrap_and_takes_its_line_after_the_semicolon() {
    let t = run("focus_try");
    assert_eq!(
        line_sites(&t),
        [(8, "read_one", 5), (9, "read_one", 6), (10, "read_one", 7)]
    );
    assert_eq!(
        err_sites(&t),
        [(11, "read_one", 6, SiteKind::Try, "try")],
        "the try site is minted by the MAIN walk, after this fn's LINE sites"
    );
    assert!(t.source.contains("?;::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 9, || [(\"v\", ::sensorium_rt::probe_cap!(&v))]);"));
}

/// Fix round 1, I3. An arm-entry LINE and an `Err(..) =>` arm probe land on the
/// same byte, and the two forms of an arm body must not disagree about which
/// comes first. Both put the LINE outside: a block body writes it in front of
/// the arm probe (`Kind::LineEntry`), a bare-expression body wraps the arm
/// probe's own wrap. `oracle.rs` compiles the result.
#[test]
fn an_arm_entry_line_sits_outside_an_err_arm_probe_in_both_arm_forms() {
    let t = run("focus_err_arm");
    assert_eq!(
        sites(&t),
        [
            (7, "handled", 6, RetKind::Value),
            (13, "bare", 16, RetKind::Value)
        ]
    );
    assert_eq!(
        err_sites(&t),
        [
            (12, "handled", 9, SiteKind::Arm, "arm_handled"),
            (17, "bare", 19, SiteKind::Arm, "arm_ambiguous"),
        ]
    );
    assert_eq!(
        line_sites(&t),
        [
            (8, "handled", 6),
            (9, "handled", 8),
            (10, "handled", 9),
            (11, "handled", 10),
            (14, "bare", 16),
            (15, "bare", 18),
            (16, "bare", 19),
        ]
    );
    // BLOCK body: LINE first, then the arm probe, both as statements.
    assert!(t.source.contains(
        "Err(e) => {::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 10, \
         || [(\"e\", ::sensorium_rt::probe_cap!(&e))]);::sensorium_rt::err_site_value("
    ));
    // BARE body: the LINE wrap is OUTSIDE the arm probe's wrap, same order.
    assert!(t.source.contains(
        "Err(e) => { ::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 16, \
         || [(\"e\", ::sensorium_rt::probe_cap!(&e))]); \
         { ::sensorium_rt::err_site_value("
    ));
    assert!(t.source.contains("e.len() as i32 } },"));
}

// ---------------------------------------------------------------------------
// What is NOT focused
// ---------------------------------------------------------------------------

#[test]
fn an_async_fn_named_in_the_focus_is_skipped_with_its_existing_reason() {
    let t = run("focus_skipped");
    assert!(t.sites.is_empty(), "an async fn is not instrumented at all");
    assert_eq!(
        t.skipped
            .iter()
            .map(|s| (s.qualname.as_str(), s.line, s.reason))
            .collect::<Vec<_>>(),
        [("spun", 5, "async")]
    );
    assert!(t.focused.is_empty(), "a skipped fn is not a match");
    assert!(!t.source.contains("::sensorium_rt::line("));
}

#[test]
fn a_focus_that_matches_nothing_here_leaves_the_file_unfocused() {
    let t = run("focus_unmatched");
    assert!(line_sites(&t).is_empty());
    assert!(t.focused.is_empty());
    assert!(
        !t.source.contains("::sensorium_rt::line("),
        "a focused-but-unmatched file must carry no LINE probe at all"
    );
}

#[test]
fn an_empty_focus_and_a_focus_that_matches_nothing_produce_the_same_bytes() {
    let input = read_focus("focus_unmatched", "in");
    let unfocused = transform(&input, "src/lib.rs", META, 7, true, &Focus::EMPTY).expect("plain");
    let missed = transform(
        &input,
        "src/lib.rs",
        META,
        7,
        true,
        &Focus::parse("nothing_here"),
    )
    .expect("focused");
    assert_eq!(unfocused.source, missed.source);
    assert_eq!(unfocused.sites, missed.sites);
}

/// The other half of "an empty focus changes nothing": every case in
/// `tests/golden_focus` transformed with NO focus is byte-identical to the same
/// case transformed with a focus that misses. (`tests/golden`'s own cases are
/// covered by `golden.rs`, which passes them an empty focus and diffs the
/// checked-in bytes.)
#[test]
fn no_golden_focus_case_moves_a_byte_under_an_empty_focus() {
    for (case, _) in FOCUS_CASES {
        let input = read_focus(case, "in");
        let plain = transform(&input, "src/lib.rs", META, 7, true, &Focus::EMPTY)
            .unwrap_or_else(|e| panic!("{case}: {e}"));
        let missed = transform(
            &input,
            "src/lib.rs",
            META,
            7,
            true,
            &Focus::parse("a_name_no_file_here_uses"),
        )
        .unwrap_or_else(|e| panic!("{case}: {e}"));
        assert_eq!(plain.source, missed.source, "{case}");
        assert!(
            !plain.source.contains("::sensorium_rt::line("),
            "{case}: an unfocused build carries no LINE probe"
        );
    }
}

// ---------------------------------------------------------------------------
// The manifest
// ---------------------------------------------------------------------------

#[test]
fn a_line_site_is_a_line_row_with_a_line_and_no_firstlineno() {
    let t = run("focus_fill");
    let mut manifest = Manifest::new("m", "c", "lib");
    manifest.set_focus(&Focus::parse("fill"));
    manifest.add_file("src/lib.rs", &t);
    let json: serde_json::Value =
        serde_json::from_str(&manifest.to_json().expect("json")).expect("parse");
    let rows = json["files"]["src/lib.rs"].as_array().expect("rows");
    assert_eq!(rows.len(), 5);
    assert_eq!(rows[0]["kind"], "fn");
    assert_eq!(rows[0]["firstlineno"], 3);
    for (i, line) in [3u64, 4, 5, 6].iter().enumerate() {
        let row = &rows[i + 1];
        assert_eq!(row["kind"], "line", "row {i}");
        assert_eq!(row["line"], *line, "row {i}");
        assert_eq!(row["qualname"], "fill", "row {i}");
        assert!(row.get("firstlineno").is_none(), "row {i}");
        assert!(row.get("how").is_none(), "row {i}");
        assert!(row.get("ret").is_none(), "row {i}");
    }
    assert_eq!(json["focus"]["values"][0], "fill");
    assert_eq!(json["focus"]["matched"][0], "fill");
}

#[test]
fn the_manifest_records_the_values_as_given_and_the_matches_sorted() {
    let t = run("focus_params");
    let mut manifest = Manifest::new("m", "c", "lib");
    manifest.set_focus(&Focus::parse("Counter, missing"));
    manifest.add_file("src/lib.rs", &t);
    let record = manifest.focus.as_ref().expect("a focus record");
    assert_eq!(record.values, ["Counter", "missing"], "as given, in order");
    assert_eq!(
        record.matched,
        BTreeSet::from(["Counter::bump".to_owned(), "Counter::zero".to_owned()])
    );
}

#[test]
fn an_unfocused_manifest_has_no_focus_key_at_all() {
    let t = run_focus("focus_unmatched", 7, &Focus::EMPTY);
    let mut manifest = Manifest::new("m", "c", "lib");
    manifest.set_focus(&Focus::EMPTY);
    manifest.add_file("src/lib.rs", &t);
    let json: serde_json::Value =
        serde_json::from_str(&manifest.to_json().expect("json")).expect("parse");
    assert!(
        json.get("focus").is_none(),
        "an absent key and an empty one are different facts to a reader"
    );
    assert!(manifest.focus.is_none());
}

// ---------------------------------------------------------------------------
// The directory and the list agree
// ---------------------------------------------------------------------------

#[test]
fn tests_golden_focus_and_common_focus_cases_hold_the_same_cases() {
    let dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/golden_focus");
    let mut on_disk: Vec<String> = std::fs::read_dir(&dir)
        .expect("the focus golden directory")
        .filter_map(Result::ok)
        .filter_map(|e| {
            let name = e.file_name().to_string_lossy().into_owned();
            name.strip_suffix(".in.rs").map(ToOwned::to_owned)
        })
        .collect();
    on_disk.sort();
    let mut listed: Vec<String> = FOCUS_CASES.iter().map(|(c, _)| (*c).to_owned()).collect();
    listed.sort();
    assert_eq!(
        on_disk, listed,
        "tests/golden_focus and FOCUS_CASES disagree"
    );
}

/// The same identity for the compile-fail inputs. They are not goldens -- there
/// is no legal output to check in -- so nothing else walks that directory, and
/// a file dropped there without a `COMPILE_FAIL_CASES` row would be measured by
/// nothing at all.
#[test]
fn tests_focus_compile_fail_and_common_compile_fail_cases_hold_the_same_cases() {
    let dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/focus_compile_fail");
    let mut on_disk: Vec<String> = std::fs::read_dir(&dir)
        .expect("the compile-fail directory")
        .filter_map(Result::ok)
        .filter_map(|e| {
            let name = e.file_name().to_string_lossy().into_owned();
            name.strip_suffix(".rs").map(ToOwned::to_owned)
        })
        .collect();
    on_disk.sort();
    let mut listed: Vec<String> = COMPILE_FAIL_CASES
        .iter()
        .map(|(c, _, _)| (*c).to_owned())
        .collect();
    listed.sort();
    assert_eq!(
        on_disk, listed,
        "tests/focus_compile_fail and COMPILE_FAIL_CASES disagree"
    );
}

/// Every focus golden's sites are contiguous from `first_site` and every LINE
/// row is named after a fn the focus actually matched. Both are identities the
/// wrapper depends on: it advances `next_site` by `sites.len()`.
#[test]
fn every_focus_case_numbers_its_sites_contiguously_and_names_them_after_a_match() {
    for (case, _) in FOCUS_CASES {
        let t = run(case);
        for (i, site) in t.sites.iter().enumerate() {
            assert_eq!(
                site.site,
                7 + u32::try_from(i).expect("a small index"),
                "{case}: sites are contiguous from first_site, in push order"
            );
        }
        for site in t.sites.iter().filter(|s| s.kind == SiteKind::Line) {
            assert!(
                t.focused.contains(&site.qualname),
                "{case}: a LINE row named {} which was not focused",
                site.qualname
            );
        }
    }
}
