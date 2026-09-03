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
