//! THROWAWAY SPIKE CODE. RETURN outcomes.

mod common;

use common::{KIND_RETURN, OUTCOME_NONE, OUTCOME_PANIC};

/// A guard dropped during unwinding writes outcome 3; a guard dropped on a
/// normal return writes outcome 0.
#[test]
fn a_guard_dropped_while_unwinding_writes_outcome_panic() {
    let (dir, _run) = common::run_recording("panic");
    let returns = dir.spool(1).kinds(KIND_RETURN);
    assert_eq!(
        returns.len(),
        2,
        "the scenario has exactly two frames: {returns:?}"
    );

    let unwound = returns
        .iter()
        .find(|r| r.site_index() == 1)
        .expect("the panicking frame's RETURN (site 1)");
    assert_eq!(
        unwound.outcome, OUTCOME_PANIC,
        "a guard dropped during unwinding must record outcome 3, got {}",
        unwound.outcome
    );
    assert_eq!(OUTCOME_PANIC, 3, "the brief pins panic at 3");

    let normal = returns
        .iter()
        .find(|r| r.site_index() == 2)
        .expect("the normal frame's RETURN (site 2)");
    assert_eq!(
        normal.outcome, OUTCOME_NONE,
        "a normal return must record outcome 0, got {}",
        normal.outcome
    );
    assert_eq!(OUTCOME_NONE, 0, "the brief pins none at 0");
}

/// CALL records never carry an outcome: outcome is a property of the RETURN.
#[test]
fn call_records_carry_outcome_none() {
    let (dir, _run) = common::run_recording("panic");
    for r in dir.spool(1).kinds(common::KIND_CALL) {
        assert_eq!(r.outcome, OUTCOME_NONE, "CALL must carry outcome 0: {r:?}");
    }
}
