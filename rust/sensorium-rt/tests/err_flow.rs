//! Err-flow sites, read off the spool bytes: which shapes write a record, which
//! kind and `how` each writes, and what the ladder could read (design R1-R4).
//!
//! The parser is `common/mod.rs`, written from the wire-format block rather than
//! from `src/spool.rs`. Type names are asserted by SUFFIX, never in full: `R12`
//! forbids a std type string from pinning anything, because its spelling is the
//! compiler's to change.

mod common;

use common::{
    ErrSite, Spec, TempDir, HOW_ARM_AMBIGUOUS, HOW_ARM_HANDLED, HOW_ARM_PROPAGATE,
    HOW_SINK_LET_UNDERSCORE, HOW_SINK_OK, HOW_SINK_UNWRAP_OR, HOW_TRY, KIND_HANDLED, KIND_RAISE,
    KIND_RETURN, MSG_CAP, OUTCOME_ERR, OUTCOME_NONE, OUTCOME_OK, TAG_DEBUG, TAG_UNREAD, TYPE_CAP,
};

/// Run one scenario and return its main thread's spool.
fn run(name: &str) -> (TempDir, common::SpoolFile) {
    let dir = TempDir::reserved(&format!("errflow-{name}"));
    Spec::new(name).spool(dir.path()).run();
    let s = dir.spool(1);
    (dir, s)
}

fn type_of(e: &ErrSite) -> &str {
    e.type_name
        .as_deref()
        .unwrap_or_else(|| panic!("no type recorded: {e:?}"))
}

// ---------------------------------------------------------------------------
// Invariant 1: a record only where the ladder saw an `Err`
// ---------------------------------------------------------------------------

#[test]
fn a_question_mark_on_an_err_writes_one_raise_with_the_type_and_the_text() {
    let (_dir, s) = run("try-err");
    let sites = s.err_sites();
    assert_eq!(sites.len(), 1, "one probed ? saw one Err: {sites:?}");
    let (kind, site, e) = &sites[0];
    assert_eq!(*kind, KIND_RAISE, "a ? lets the Err OUT of the frame");
    assert_eq!(*site, 501);
    assert_eq!(e.how, HOW_TRY);
    assert!(type_of(e).ends_with("String"), "{e:?}");
    assert_eq!(e.msg.as_deref(), Some(r#""boom""#));
    assert!(!e.msg_truncated);
    assert!(!e.type_truncated);
    // And the frame the `?` left closes `none`: its tail was never reached.
    assert_eq!(s.the_return(500).outcome, OUTCOME_NONE);
}

#[test]
fn a_question_mark_on_an_ok_writes_nothing() {
    let (_dir, s) = run("try-ok");
    assert_eq!(
        s.err_sites(),
        vec![],
        "the very same site, with an Ok operand"
    );
    assert_eq!(s.the_return(500).outcome, OUTCOME_OK);
}

/// `None` is not an error in this model (design §6), and the ladder's third
/// level is what keeps it out of the trace.
#[test]
fn a_question_mark_on_an_option_writes_nothing() {
    let (_dir, s) = run("try-option");
    assert_eq!(s.err_sites(), vec![]);
    assert_eq!(
        s.the_return(502).outcome,
        OUTCOME_NONE,
        "the ? still bypassed the tail"
    );
}

#[test]
fn a_sink_that_absorbed_an_err_writes_a_handled_and_the_frame_still_closes_ok() {
    let (_dir, s) = run("sink-ok-err");
    let sites = s.err_sites();
    assert_eq!(sites.len(), 1, "{sites:?}");
    let (kind, site, e) = &sites[0];
    assert_eq!(*kind, KIND_HANDLED, ".ok() absorbs the Err");
    assert_eq!(*site, 511);
    assert_eq!(e.how, HOW_SINK_OK);
    assert!(type_of(e).ends_with("String"));
    assert_eq!(e.msg.as_deref(), Some(r#""boom""#));
    assert_eq!(
        s.the_return(510).outcome,
        OUTCOME_OK,
        "the frame that swallowed it returned normally -- which is what makes \
         SWALLOWED computable at conversion"
    );
}

#[test]
fn a_sink_on_an_ok_writes_nothing() {
    let (_dir, s) = run("sink-ok-ok");
    assert_eq!(s.err_sites(), vec![]);
    assert_eq!(s.the_return(510).outcome, OUTCOME_OK);
}

#[test]
fn each_sink_writes_its_own_how() {
    let (_dir, s) = run("let-underscore-err");
    let sites = s.err_sites();
    assert_eq!(sites.len(), 2, "{sites:?}");
    assert_eq!(
        sites
            .iter()
            .map(|(k, site, e)| (*k, *site, e.how))
            .collect::<Vec<_>>(),
        vec![
            (KIND_HANDLED, 513, HOW_SINK_LET_UNDERSCORE),
            (KIND_HANDLED, 514, HOW_SINK_UNWRAP_OR),
        ],
        "the how byte separates one sink from another; the kind does not"
    );
}

// ---------------------------------------------------------------------------
// Invariants 2 and 3: what each ladder could read
// ---------------------------------------------------------------------------

#[test]
fn an_arm_that_bound_a_debug_error_records_its_type_and_its_text() {
    let (_dir, s) = run("arm-value-debug");
    let r = s.the_record(KIND_HANDLED, 521);
    let e = r.err_site();
    assert_eq!(e.how, HOW_ARM_HANDLED);
    assert!(type_of(&e).ends_with("String"), "{e:?}");
    assert_eq!(e.msg.as_deref(), Some(r#""boom""#));
}

#[test]
fn an_arm_that_bound_an_error_without_debug_records_only_its_type() {
    let (_dir, s) = run("arm-value-nodebug");
    let r = s.the_record(KIND_HANDLED, 523);
    let e = r.err_site();
    assert_eq!(e.how, HOW_ARM_AMBIGUOUS);
    assert!(type_of(&e).ends_with("NoDbgErr"), "{e:?}");
    assert_eq!(e.msg, None, "no Debug impl is unread, never empty");
    assert!(!e.msg_truncated);
}

#[test]
fn an_unbound_arm_records_neither_a_type_nor_a_message() {
    let (_dir, s) = run("arm-unbound");
    let r = s.the_record(KIND_RAISE, 525);
    assert_eq!(
        r.payload.len(),
        3,
        "flags and a zero type_len, and nothing else: {:?}",
        r.payload
    );
    let e = r.err_site();
    assert_eq!(e.how, HOW_ARM_PROPAGATE);
    assert_eq!(e.type_name, None);
    assert_eq!(e.msg, None);
    assert!(!e.msg_truncated && !e.type_truncated);
}

/// The ladder's second level over the wire: `Result<T, E>` with no `Debug` on
/// `E`. A two-level ladder would read this as unread with no type at all.
#[test]
fn a_question_mark_on_an_error_without_debug_records_its_type_and_no_message() {
    let (_dir, s) = run("err-nodebug");
    let r = s.the_record(KIND_RAISE, 531);
    let e = r.err_site();
    assert_eq!(e.how, HOW_TRY);
    assert!(type_of(&e).ends_with("NoDbgErr"), "{e:?}");
    assert_eq!(e.msg, None);
}

// ---------------------------------------------------------------------------
// Invariant 5: the two caps
// ---------------------------------------------------------------------------

#[test]
fn each_cap_bites_at_its_own_length_and_sets_its_own_flag() {
    let (_dir, s) = run("err-big");
    let r = s.the_record(KIND_HANDLED, 541);
    let e = r.err_site();
    let ty = type_of(&e);
    assert_eq!(ty.len(), TYPE_CAP, "the type cap is 120 bytes: {ty:?}");
    assert!(e.type_truncated, "and bit 2 says it cut");
    let msg = e.msg.as_deref().expect("the Debug impl was readable");
    assert_eq!(msg.len(), MSG_CAP, "the message cap is 200 bytes");
    assert!(e.msg_truncated, "and bit 1 says it cut");
    assert!(
        msg.starts_with("AnErrorTypeWhoseName"),
        "the message is the Debug rendering, cut: {msg:?}"
    );
    assert!(
        msg.ends_with('é'),
        "the cut landed on a char boundary, not inside a two-byte 'é': {:?}",
        &msg[msg.len() - 8..]
    );
    assert_eq!(
        r.payload.len(),
        3 + TYPE_CAP + MSG_CAP,
        "the widest payload an err site can write"
    );
}

// ---------------------------------------------------------------------------
// Invariant 4: the typed `err` RETURN
// ---------------------------------------------------------------------------

#[test]
fn an_err_return_carries_the_error_type_and_the_value_text_v2_wrote() {
    let (_dir, s) = run("typed-err-return");

    let err = s.the_return(550);
    assert_eq!(err.outcome, OUTCOME_ERR);
    let (ty, truncated) = err.ret_err_type();
    assert!(
        ty.as_deref()
            .expect("an err knows its E")
            .ends_with("Error"),
        "{ty:?}"
    );
    assert!(!truncated);
    let (tag, cut, text) = err.ret_value();
    assert_eq!(tag, TAG_DEBUG);
    assert!(!cut);
    assert!(
        text.starts_with("Err(") && text.contains("nope"),
        "the value text is what wire v2 wrote: {text:?}"
    );

    // The sibling that returned `Ok` carries no type block at all, so its
    // payload is byte-for-byte v2.
    let ok = s.the_return(551);
    assert_eq!(ok.outcome, OUTCOME_OK);
    assert_eq!(
        ok.payload,
        vec![1, 0, b'O', b'k', b'(', b'9', b')'],
        "tag 1, not truncated, then the text -- no type block on an ok"
    );
}

#[test]
fn an_unread_err_value_still_names_its_type() {
    let (_dir, s) = run("typed-err-return");
    let r = s.the_return(552);
    assert_eq!(r.outcome, OUTCOME_ERR);
    let (tag, cut, text) = r.ret_value();
    assert_eq!(tag, TAG_UNREAD, "NoDbgErr has no Debug impl");
    assert!(!cut);
    assert_eq!(text, "");
    let (ty, _) = r.ret_err_type();
    assert!(
        ty.as_deref()
            .expect("the type is static")
            .ends_with("NoDbgErr"),
        "{ty:?}"
    );
}

// ---------------------------------------------------------------------------
// Invariant 6: the version and the capability
// ---------------------------------------------------------------------------

#[test]
fn the_spool_says_version_three_and_the_header_declares_err_flow() {
    let dir = TempDir::reserved("errflow-header");
    let subject = Spec::new("try-err").spool(dir.path()).run();
    assert_eq!(dir.spool(1).version, 3, "wire version");
    let h = dir.proc_header(subject.pid);
    assert_eq!(h.get("rt_version").str(), "sensorium-rt 0.3.0");
    assert!(
        h.get("capabilities").get("err_flow").bool(),
        "a rung-3 runtime declares the capability whose records it writes"
    );
}

// ---------------------------------------------------------------------------
// Invariant 7: kinds 4 and 5 go through `record()` unchanged
// ---------------------------------------------------------------------------

/// Every err record carries the process-global sequence, ascends within its
/// thread, and sits between the CALL and the RETURN of the frame it was written
/// in -- the ordinary `record()` contract, with nothing special for the new
/// kinds.
#[test]
fn err_records_sit_in_the_frame_that_wrote_them_and_carry_ascending_seqs() {
    let (_dir, s) = run("sink-ok-err");
    let kinds: Vec<u8> = s.records.iter().map(|r| r.kind).collect();
    assert_eq!(
        kinds,
        vec![1, KIND_HANDLED, KIND_RETURN, 255],
        "CALL, HANDLED, RETURN, THREAD_END"
    );
    let seqs: Vec<u64> = s.records.iter().map(|r| r.seq).collect();
    let mut sorted = seqs.clone();
    sorted.sort_unstable();
    sorted.dedup();
    assert_eq!(seqs, sorted, "seqs ascend and never repeat: {seqs:?}");
}
