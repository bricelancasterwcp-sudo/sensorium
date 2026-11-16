//! Async drive futures, polled by hand. The tokio sample is `tokio_sample.rs`.

mod common;

use common::{
    Spec, TempDir, KIND_CALL, KIND_RESUME, KIND_RETURN, KIND_SUSPEND, OUTCOME_NONE, OUTCOME_OK,
    OUTCOME_PANIC, TAG_DEBUG, TAG_NO_VALUE,
};

fn kinds(dir: &TempDir) -> Vec<(u8, u32, u8)> {
    dir.spool(1)
        .records
        .iter()
        .filter(|r| r.kind != common::KIND_THREAD_END)
        .map(|r| (r.kind, r.site_index(), r.outcome))
        .collect()
}

#[test]
fn a_pending_poll_parks_the_frame_and_the_ready_poll_returns_the_value() {
    let dir = TempDir::reserved("async-pending-ready");
    Spec::new("async-pending-ready").spool(dir.path()).run();
    let spool = dir.spool(1);
    assert_eq!(
        kinds(&dir),
        vec![
            (KIND_CALL, 40, OUTCOME_NONE),
            (KIND_SUSPEND, 40, OUTCOME_NONE),
            (KIND_RESUME, 40, OUTCOME_NONE),
            (KIND_RETURN, 40, OUTCOME_OK),
        ]
    );
    let call = spool.the_record(KIND_CALL, 40);
    assert!(
        call.payload.contains(&b'n') && call.payload.contains(&b'7'),
        "the argument capture is on the CALL, got {:?}",
        call.payload
    );
    let ret = spool.the_return(40);
    let (tag, trunc, value) = ret.ret_value();
    assert_eq!(tag, TAG_DEBUG);
    assert!(!trunc);
    assert_eq!(value, "9");
    let suspend = spool.the_record(KIND_SUSPEND, 40);
    let resume = spool.the_record(KIND_RESUME, 40);
    assert_eq!(suspend.payload.len(), 8);
    assert_eq!(suspend.payload, resume.payload);
}

#[test]
fn a_sync_call_during_the_poll_sits_between_call_and_suspend() {
    let dir = TempDir::reserved("async-nested");
    Spec::new("async-nested").spool(dir.path()).run();
    assert_eq!(
        kinds(&dir),
        vec![
            (KIND_CALL, 40, OUTCOME_NONE),
            (KIND_CALL, 41, OUTCOME_NONE),
            (KIND_RETURN, 41, OUTCOME_NONE),
            (KIND_SUSPEND, 40, OUTCOME_NONE),
            (KIND_RESUME, 40, OUTCOME_NONE),
            (KIND_RETURN, 40, OUTCOME_NONE),
        ]
    );
}

#[test]
fn dropping_a_parked_future_resumes_then_returns_no_value() {
    let dir = TempDir::reserved("async-drop-pending");
    Spec::new("async-drop-pending").spool(dir.path()).run();
    let spool = dir.spool(1);
    assert_eq!(
        kinds(&dir),
        vec![
            (KIND_CALL, 42, OUTCOME_NONE),
            (KIND_SUSPEND, 42, OUTCOME_NONE),
            (KIND_RESUME, 42, OUTCOME_NONE),
            (KIND_RETURN, 42, OUTCOME_NONE),
        ]
    );
    let ret = spool.the_return(42);
    let (tag, _, _) = ret.ret_value();
    assert_eq!(tag, TAG_NO_VALUE);
}

#[test]
fn a_panic_during_the_poll_returns_panic_and_propagates() {
    let dir = TempDir::reserved("async-panic");
    Spec::new("async-panic").spool(dir.path()).run();
    let spool = dir.spool(1);
    let relevant: Vec<(u8, u32, u8)> = spool
        .records
        .iter()
        .filter(|r| r.site_index() == 43 && r.kind != common::KIND_PANIC)
        .map(|r| (r.kind, r.site_index(), r.outcome))
        .collect();
    assert_eq!(
        relevant,
        vec![
            (KIND_CALL, 43, OUTCOME_NONE),
            (KIND_RETURN, 43, OUTCOME_PANIC)
        ]
    );
    assert!(
        spool.records.iter().any(|r| r.kind == common::KIND_PANIC),
        "the panic hook still records the panic"
    );
}
