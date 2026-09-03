//! One arm per wire outcome, read off the spool bytes.
//!
//! The runtime carries no per-site knowledge: a `?` that propagated past the
//! tail and a `-> ()` function that returned normally are the SAME two bytes on
//! the wire (outcome 0, tag 0). The manifest's `ret: unit` is what separates
//! them at conversion (Task 6) -- see `rust/HONESTY.md` §1.

mod common;

use common::{
    Spec, TempDir, KIND_RETURN, OUTCOME_ERR, OUTCOME_NONE, OUTCOME_OK, OUTCOME_PANIC, TAG_DEBUG,
    TAG_NO_VALUE,
};

#[test]
fn an_ok_return_reads_outcome_ok_with_its_debug_text() {
    let dir = TempDir::reserved("outcomes-ok");
    Spec::new("ret-ok").spool(dir.path()).run();
    let r = dir.spool(1).the_return(10);
    assert_eq!(r.outcome, OUTCOME_OK);
    let (tag, trunc, text) = r.ret_value();
    assert_eq!(tag, TAG_DEBUG);
    assert!(!trunc);
    assert_eq!(text, "Ok(3)");
}

#[test]
fn an_err_return_reads_outcome_err_with_its_debug_text() {
    let dir = TempDir::reserved("outcomes-err");
    Spec::new("ret-err").spool(dir.path()).run();
    let r = dir.spool(1).the_return(11);
    assert_eq!(r.outcome, OUTCOME_ERR);
    let (tag, trunc, text) = r.ret_value();
    assert_eq!(tag, TAG_DEBUG);
    assert!(!trunc);
    assert_eq!(text, r#"Err("x")"#);
}

#[test]
fn a_question_mark_that_bypassed_the_tail_reads_none_with_no_value() {
    let dir = TempDir::reserved("outcomes-question");
    Spec::new("ret-question").spool(dir.path()).run();
    let s = dir.spool(1);

    let inner = s.the_return(12);
    assert_eq!(
        inner.outcome, OUTCOME_ERR,
        "the inner frame did reach its tail"
    );

    let outer = s.the_return(13);
    assert_eq!(
        outer.outcome, OUTCOME_NONE,
        "the ? propagated, so nothing was stashed at site 13"
    );
    let (tag, trunc, text) = outer.ret_value();
    assert_eq!(tag, TAG_NO_VALUE);
    assert!(!trunc);
    assert_eq!(text, "");
}

#[test]
fn a_frame_unwound_by_a_panic_reads_outcome_panic() {
    let dir = TempDir::reserved("outcomes-panic");
    Spec::new("ret-panic").spool(dir.path()).run();
    let r = dir.spool(1).the_return(14);
    assert_eq!(r.outcome, OUTCOME_PANIC);
    let (tag, _, text) = r.ret_value();
    assert_eq!(
        tag, TAG_NO_VALUE,
        "an unwound frame returned no value to read"
    );
    assert_eq!(text, "");
}

#[test]
fn a_unit_returning_fn_reads_outcome_none_with_tag_zero() {
    let dir = TempDir::reserved("outcomes-unit");
    Spec::new("ret-unit").spool(dir.path()).run();
    let r = dir.spool(1).the_return(15);
    assert_eq!(
        r.outcome, OUTCOME_NONE,
        "the transformer emits no ret for a -> () fn, so the wire says none"
    );
    let (tag, trunc, text) = r.ret_value();
    assert_eq!(tag, TAG_NO_VALUE);
    assert!(!trunc);
    assert_eq!(text, "");
}

#[test]
fn a_stash_from_another_site_cannot_poison_the_frame_that_closes_next() {
    let dir = TempDir::reserved("outcomes-mismatch");
    let run = Spec::new("ret-mismatch").spool(dir.path()).run();
    assert_eq!(
        run.says("orphan"),
        "Ok(7)",
        "the value itself is returned unchanged"
    );
    let s = dir.spool(1);
    assert_eq!(
        s.of_kind(common::KIND_CALL).len(),
        1,
        "only site 61 opened a frame"
    );
    let r = s.the_return(61);
    assert_eq!(
        r.outcome, OUTCOME_NONE,
        "site 61 stashed nothing of its own, so its frame closes knowing nothing"
    );
    let (tag, _, text) = r.ret_value();
    assert_eq!(tag, TAG_NO_VALUE);
    assert_eq!(
        text, "",
        "site 60's Ok(7) must not be attributed to site 61"
    );
}

/// A local whose `Drop` calls instrumented code runs a whole frame BETWEEN the
/// outer frame's exit operand and its guard. With one stash slot that inner
/// frame's guard cleared the slot, and the outer frame -- which really did
/// return `Err` -- recorded `none`: a silent err-to-none.
#[test]
fn a_drop_that_calls_instrumented_code_cannot_take_the_outer_frames_value() {
    let dir = TempDir::reserved("outcomes-dropcalls");
    let run = Spec::new("drop-calls-instrumented").spool(dir.path()).run();
    assert_eq!(run.says("returned"), r#"Err("outer")"#);
    let s = dir.spool(1);

    let outer = s.the_return(70);
    assert_eq!(
        outer.outcome, OUTCOME_ERR,
        "the outer frame really did return Err"
    );
    let (tag, _, text) = outer.ret_value();
    assert_eq!(tag, TAG_DEBUG);
    assert_eq!(text, r#"Err("outer")"#);

    let inner = s.the_return(71);
    assert_eq!(
        inner.outcome, OUTCOME_NONE,
        "the -> () fn the Drop called stashed nothing of its own"
    );
    assert_eq!(inner.ret_value().0, TAG_NO_VALUE);
    assert_eq!(
        s.of_kind(common::KIND_CALL).len(),
        s.of_kind(KIND_RETURN).len()
    );
}

/// The same window, but the `Drop` calls the SAME function one level down, so
/// both pending captures carry site 72 and only the frame depth separates them.
#[test]
fn a_drop_that_re_enters_the_same_site_keeps_each_frames_own_value() {
    let dir = TempDir::reserved("outcomes-droprecurses");
    let run = Spec::new("drop-recurses").spool(dir.path()).run();
    assert_eq!(run.says("returned"), "Ok(1)");
    let s = dir.spool(1);

    let mut rets: Vec<_> = s
        .of_kind(KIND_RETURN)
        .into_iter()
        .filter(|r| r.site_index() == 72)
        .collect();
    rets.sort_by_key(|r| r.seq);
    assert_eq!(rets.len(), 2, "two frames at one site");
    let texts: Vec<String> = rets.iter().map(|r| r.ret_value().2).collect();
    assert_eq!(
        texts,
        vec!["Ok(0)".to_owned(), "Ok(1)".to_owned()],
        "the inner frame closes first and with ITS value, the outer with its own"
    );
    assert!(rets.iter().all(|r| r.outcome == OUTCOME_OK));
}

/// The bound, measured rather than asserted. Each level of this `Drop` chain
/// leaves one capture pending while it recurses, so 70 nested frames ask for 70
/// pending captures and the stack holds 64. The six frames whose push was
/// refused close `none` -- which is what `rust/HONESTY.md` §1 says they do.
#[test]
fn the_pending_capture_stack_is_bounded_at_sixty_four() {
    const FRAMES: usize = 70;
    const BOUND: usize = 64;

    let dir = TempDir::reserved("outcomes-stashbound");
    let run = Spec::new("drop-recurses")
        .arg(&(FRAMES - 1).to_string())
        .spool(dir.path())
        .run();
    assert_eq!(run.says_u64("frames"), FRAMES as u64);

    let s = dir.spool(1);
    let rets: Vec<_> = s
        .of_kind(KIND_RETURN)
        .into_iter()
        .filter(|r| r.site_index() == 72)
        .collect();
    assert_eq!(rets.len(), FRAMES, "every frame still closes");
    let carried = rets.iter().filter(|r| r.ret_value().0 == TAG_DEBUG).count();
    let refused = rets
        .iter()
        .filter(|r| r.ret_value().0 == TAG_NO_VALUE)
        .count();
    assert_eq!(carried, BOUND, "exactly the bound many captures survived");
    assert_eq!(
        refused,
        FRAMES - BOUND,
        "and the rest closed knowing nothing"
    );
    assert!(
        rets.iter()
            .filter(|r| r.ret_value().0 == TAG_NO_VALUE)
            .all(|r| r.outcome == OUTCOME_NONE),
        "a refused push closes the frame none, not ok"
    );
}

/// The case the frame depth is load-bearing for: the inner frame at the same
/// site leaves by `?` and stashes nothing, so the top of the stack is the OUTER
/// frame's still-pending capture. Matching on the site alone would hand `Ok(9)`
/// to the inner frame and leave the outer with `none` -- both wrong, and neither
/// visible in the trace.
#[test]
fn a_re_entered_site_that_stashes_nothing_does_not_take_the_outer_capture() {
    let dir = TempDir::reserved("outcomes-dropbypass");
    let run = Spec::new("drop-recurses-bypass").spool(dir.path()).run();
    assert_eq!(run.says("returned"), "Ok(9)");
    let s = dir.spool(1);

    let helper = s.the_return(75);
    assert_eq!(helper.outcome, OUTCOME_ERR);
    assert_eq!(helper.ret_value().2, r#"Err("bypass")"#);

    let mut rets: Vec<_> = s
        .of_kind(KIND_RETURN)
        .into_iter()
        .filter(|r| r.site_index() == 74)
        .collect();
    rets.sort_by_key(|r| r.seq);
    assert_eq!(rets.len(), 2);

    let (inner, outer) = (&rets[0], &rets[1]);
    assert_eq!(
        inner.outcome, OUTCOME_NONE,
        "the ? bypassed the inner frame's tail, so it knows nothing"
    );
    assert_eq!(inner.ret_value().0, TAG_NO_VALUE);
    assert_eq!(inner.ret_value().2, "");
    assert_eq!(
        outer.outcome, OUTCOME_OK,
        "and the outer frame still has its own"
    );
    assert_eq!(outer.ret_value().2, "Ok(9)");
}

#[test]
fn every_recorded_call_gets_exactly_one_return() {
    for scenario in [
        "ret-ok",
        "ret-err",
        "ret-question",
        "ret-panic",
        "ret-unit",
        "ret-mismatch",
    ] {
        let dir = TempDir::reserved(&format!("outcomes-pairs-{scenario}"));
        Spec::new(scenario).spool(dir.path()).run();
        for s in dir.spools() {
            let calls = s.of_kind(common::KIND_CALL).len();
            let rets = s.of_kind(KIND_RETURN).len();
            assert_eq!(
                calls, rets,
                "{scenario}: {calls} CALLs and {rets} RETURNs on serial {}",
                s.serial
            );
        }
    }
}
