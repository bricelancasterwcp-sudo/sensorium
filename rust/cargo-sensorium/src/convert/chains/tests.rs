//! §2a of the design, one test per row. The machine is pure, so a thread is
//! stated here as data -- a list of records -- and the chains are read back
//! from what `mint` returns.

use super::*;
fn text(type_name: &str, msg: &str) -> ErrText {
    ErrText {
        type_name: Some(type_name.to_owned()),
        msg: Some(msg.to_owned()),
    }
}

fn call(seq: u64) -> Input {
    Input {
        seq,
        rec: Rec::Call {
            test: false,
            main: false,
        },
    }
}

fn call_marked(seq: u64, test: bool, main: bool) -> Input {
    Input {
        seq,
        rec: Rec::Call { test, main },
    }
}

fn ret(seq: u64, outcome: Outcome) -> Input {
    Input {
        seq,
        rec: Rec::Return {
            outcome,
            text: ErrText::default(),
        },
    }
}

fn ret_err(seq: u64, type_name: &str, msg: &str) -> Input {
    Input {
        seq,
        rec: Rec::Return {
            outcome: Outcome::Err,
            text: text(type_name, msg),
        },
    }
}

fn flow(seq: u64, how: How, type_name: &str, msg: &str) -> Input {
    Input {
        seq,
        rec: Rec::ErrFlow {
            how,
            text: text(type_name, msg),
        },
    }
}

fn serials(events: &[ChainEvent]) -> Vec<u64> {
    let mut s: Vec<u64> = events.iter().map(|e| e.serial).collect();
    s.sort_unstable();
    s.dedup();
    s
}

/// The last event of the chain carrying `serial`, which is where the
/// machine writes that chain's terminal.
fn last_of(events: &[ChainEvent], serial: u64) -> &ChainEvent {
    events
        .iter()
        .rfind(|e| e.serial == serial)
        .expect("no event for that serial")
}

/// §2a row 1 + row 3 (`none` close), the `err_propagation` shape: `?`
/// through three frames is ONE chain, and each frame it crossed is a hop.
#[test]
fn a_try_through_three_frames_is_one_chain_with_three_hops() {
    let events = mint(
        &[
            call(0),
            call(1),
            call(2),
            ret_err(3, "io::Error", "E1"),
            flow(4, How::Try, "io::Error", "E1"),
            ret(5, Outcome::None),
            flow(6, How::Try, "io::Error", "E1"),
            ret(7, Outcome::None),
            Input {
                seq: 8,
                rec: Rec::ThreadEnd,
            },
        ],
        false,
    );
    assert_eq!(events.len(), 3, "{events:#?}");
    assert_eq!(serials(&events).len(), 1, "one chain: {events:#?}");
    assert_eq!(
        events.iter().map(|e| e.hop).collect::<Vec<_>>(),
        vec![1, 2, 3]
    );
    assert_eq!(events[0].at, At::ExitBefore, "the origin is the err close");
    assert_eq!(events[1].at, At::Record);
    assert!(events.iter().all(|e| e.origin == Origin::Workspace));
    assert_eq!(events[2].terminal, Some(Terminal::Propagated));
}

/// §2a row 1, `Open(c)` with a DIFFERENT text: the `interleaved_chains`
/// shape. Two serials, both merged, and neither is ever a swallow
/// candidate.
#[test]
fn a_second_different_err_raised_in_the_holder_merges_both_chains() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "io::Error", "E1"),
            flow(3, How::Try, "io::Error", "E2"),
            ret(4, Outcome::Ok),
        ],
        false,
    );
    let s = serials(&events);
    assert_eq!(s.len(), 2, "two serials: {events:#?}");
    assert_eq!(last_of(&events, s[0]).terminal, Some(Terminal::Merged));
    assert_eq!(last_of(&events, s[1]).terminal, Some(Terminal::Merged));
}

/// §2a row 1, `None` in the callee: a callee raising its own `Err` while an
/// outer chain is in flight opens a NESTED chain, never a merge.
#[test]
fn a_callee_raising_its_own_err_opens_a_nested_chain_not_a_merge() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "io::Error", "outer"),
            call(3),
            flow(4, How::Try, "ParseError", "inner"),
            ret_err(5, "ParseError", "inner"),
            ret(6, Outcome::Ok),
        ],
        false,
    );
    let s = serials(&events);
    assert_eq!(s.len(), 2, "two chains: {events:#?}");
    for serial in s {
        assert_eq!(
            last_of(&events, serial).terminal,
            Some(Terminal::AmbiguousEscaped),
            "a nested chain must not be read as merged: {events:#?}"
        );
    }
}

/// §2a row 2, `F == H` with a different type: one chain, the hop labelled
/// `translated` (design R8's `From` conversion).
#[test]
fn an_err_close_with_a_new_type_is_the_same_chain_labelled_translated() {
    let events = mint(
        &[
            call(0),
            call(1),
            flow(2, How::ArmPropagate, "io::Error", "E1"),
            ret_err(3, "AppError", "wrapped"),
            ret(4, Outcome::Ok),
        ],
        false,
    );
    assert_eq!(serials(&events).len(), 1, "{events:#?}");
    assert!(!events[0].translated);
    assert!(events[1].translated, "the type changed on the way out");
    assert_eq!(events[1].hop, 2);
    assert_eq!(
        events[0].origin_type.as_deref(),
        Some("io::Error"),
        "the chain keeps the type it was born with"
    );
}

/// §2a row 1, `None` column: a `?` in a frame that holds no chain OPENS one --
/// and it is born at an instrumented site, so its origin is the workspace.
/// `outside` belongs to a HANDLED with nothing to continue and to nothing else
/// (design R8): reading a `?` as `outside` would report every error the
/// recording watched being raised as one it had never seen made.
#[test]
fn a_try_with_no_open_chain_opens_a_workspace_chain() {
    let events = mint(
        &[
            call(0),
            flow(1, How::Try, "io::Error", "ENOENT"),
            ret(2, Outcome::None),
        ],
        false,
    );
    assert_eq!(events.len(), 1, "{events:#?}");
    assert_eq!(events[0].origin, Origin::Workspace);
    assert_eq!(events[0].serial, FIRST_CHAIN_SERIAL);
    assert_eq!(events[0].hop, 1);
    assert_eq!(
        events[0].origin_type.as_deref(),
        Some("io::Error"),
        "the chain is born with the type the `?` recorded"
    );
}

/// The same for a propagating arm, which is the other RAISE-class `how`.
#[test]
fn a_propagating_arm_with_no_open_chain_opens_a_workspace_chain() {
    let events = mint(
        &[
            call(0),
            flow(1, How::ArmPropagate, "io::Error", "ENOENT"),
            ret(2, Outcome::None),
        ],
        false,
    );
    assert_eq!(events[0].origin, Origin::Workspace);
}

/// §2a row 6, `None` column: a HANDLED with no chain to continue is its own
/// chain, born outside instrumented code (design R8's `dependency_swallow`).
#[test]
fn a_handled_with_no_open_chain_gets_its_own_serial_and_an_outside_origin() {
    let events = mint(
        &[
            call(0),
            flow(1, How::SinkLetUnderscore, "io::Error", "ENOENT"),
            ret(2, Outcome::Ok),
        ],
        false,
    );
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].serial, FIRST_CHAIN_SERIAL);
    assert_eq!(events[0].origin, Origin::Outside);
    assert_eq!(events[0].hop, 1);
}

/// §2a row 4, `c.sink` set: the `silent_swallow` shape.
#[test]
fn a_sink_then_an_ok_close_ends_the_chain_as_a_swallowed_candidate() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "io::Error", "E1"),
            flow(3, How::SinkOk, "io::Error", "E1"),
            ret(4, Outcome::Ok),
        ],
        false,
    );
    assert_eq!(serials(&events).len(), 1, "{events:#?}");
    assert_eq!(events[1].terminal, Some(Terminal::SwallowedCandidate));
    assert_eq!(events[0].origin, Origin::Workspace);
}

/// Design R8's named blind spot (`cleanup_then_fail`): the sink fired, then
/// the frame failed for its own reason. The absorbed chain ends as
/// `handled_then_failed`, and the `Err` that leaves is a chain of its own.
#[test]
fn a_sink_then_an_err_close_ends_that_chain_as_handled_then_failed() {
    let events = mint(
        &[
            call(0),
            call(1),
            flow(2, How::SinkOk, "io::Error", "cleanup"),
            ret_err(3, "AppError", "work"),
            ret(4, Outcome::Ok),
        ],
        false,
    );
    let s = serials(&events);
    assert_eq!(
        s.len(),
        2,
        "the swallow and the failure are two: {events:#?}"
    );
    assert_eq!(
        last_of(&events, s[0]).terminal,
        Some(Terminal::HandledThenFailed)
    );
    assert_eq!(
        last_of(&events, s[1]).terminal,
        Some(Terminal::AmbiguousEscaped),
        "the born-at-exit chain is the caller's to answer for"
    );
}

/// §2a row 4, no sink: "left the grammar in F".
#[test]
fn an_ok_close_with_no_sink_ends_the_chain_as_ambiguous() {
    let events = mint(
        &[call(0), call(1), ret_err(2, "E", "x"), ret(3, Outcome::Ok)],
        false,
    );
    assert_eq!(events[0].terminal, Some(Terminal::AmbiguousEscaped));
}

/// §2a row 4, `F != H`: a callee returning `ok` while the chain is in
/// flight (`identity(inner())`) moves nothing.
#[test]
fn a_frame_closing_ok_that_is_not_the_holder_does_not_move_the_chain() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "E", "x"),
            call(3),
            ret(4, Outcome::Ok),
            ret(5, Outcome::Ok),
        ],
        false,
    );
    assert_eq!(events.len(), 1, "{events:#?}");
    assert_eq!(events[0].hop, 1, "the callee's ok close is not a hop");
    assert_eq!(events[0].terminal, Some(Terminal::AmbiguousEscaped));
}

/// §2a row 5: the frame holding it unwound.
#[test]
fn a_panic_close_on_the_holder_ends_the_chain_as_panicked() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "E", "x"),
            ret(3, Outcome::Panic),
        ],
        false,
    );
    assert_eq!(events[0].terminal, Some(Terminal::Panicked));
}

/// §2a row 7, `Open(c)`: an `arm_ambiguous` closes the chain where it sits.
/// CLOSES it -- a `?` on the same `Err` in the same frame afterwards starts a
/// chain of its own, which is what "close c" means and what tells it apart
/// from merely recording an event against a chain that stays open.
#[test]
fn an_ambiguous_arm_on_the_held_chain_closes_it_as_escaped() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "E", "x"),
            flow(3, How::ArmAmbiguous, "E", "x"),
            flow(4, How::Try, "E", "x"),
            ret(5, Outcome::Ok),
        ],
        false,
    );
    assert_eq!(
        events[1].terminal,
        Some(Terminal::AmbiguousEscaped),
        "the terminal belongs to the arm's own event: {events:#?}"
    );
    assert_eq!(serials(&events).len(), 2, "{events:#?}");
    assert_eq!(events[2].serial, events[0].serial + 1);
    assert_eq!(events[2].hop, 1, "a new chain, not a hop of the old one");
}

/// §2a row 8 on a `test: true` holder (`returned_to_harness`).
#[test]
fn a_chain_left_open_on_a_test_frame_returned_to_the_harness() {
    let events = mint(
        &[
            call_marked(0, true, false),
            call(1),
            ret_err(2, "E", "x"),
            ret_err(3, "E", "x"),
            Input {
                seq: 4,
                rec: Rec::ThreadEnd,
            },
        ],
        false,
    );
    assert_eq!(
        last_of(&events, FIRST_CHAIN_SERIAL).terminal,
        Some(Terminal::ReturnedToHarness)
    );
}

/// §2a row 8 on a bin crate root's `main`.
#[test]
fn a_chain_left_open_on_the_main_frame_returned_to_the_harness() {
    let events = mint(
        &[
            call_marked(0, false, true),
            call(1),
            ret_err(2, "E", "x"),
            ret_err(3, "E", "x"),
            Input {
                seq: 4,
                rec: Rec::ThreadEnd,
            },
        ],
        false,
    );
    assert_eq!(
        last_of(&events, FIRST_CHAIN_SERIAL).terminal,
        Some(Terminal::ReturnedToHarness)
    );
}

/// §2a row 8 judges the frame the chain SITS in, which on an INCOMPLETE thread
/// is a frame that never closed. Judging the frame it last LEFT instead would
/// report a `#[test]` fn that was still running as a propagation -- the one
/// disposition R8 reserves for a thread whose frames were not all instrumented.
#[test]
fn a_chain_still_inside_an_unclosed_test_frame_returned_to_the_harness() {
    let events = mint(
        &[
            call_marked(0, true, false),
            call(1),
            ret_err(2, "E", "x"),
            // No RETURN for the test frame: the recording ended inside it.
            Input {
                seq: 3,
                rec: Rec::ThreadEnd,
            },
        ],
        false,
    );
    assert_eq!(
        last_of(&events, FIRST_CHAIN_SERIAL).terminal,
        Some(Terminal::ReturnedToHarness),
        "the holder is the test frame, which is still open: {events:#?}"
    );
}

/// §2a row 8 on a spawned thread's outermost frame: into a `JoinHandle`.
#[test]
fn a_chain_that_left_a_spawned_threads_outermost_frame_left_the_thread() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "E", "x"),
            ret_err(3, "E", "x"),
            Input {
                seq: 4,
                rec: Rec::ThreadEnd,
            },
        ],
        true,
    );
    assert_eq!(
        last_of(&events, FIRST_CHAIN_SERIAL).terminal,
        Some(Terminal::LeftThread)
    );
}

/// §2a row 8, neither marked nor spawned: an INCOMPLETE or partly
/// instrumented thread.
#[test]
fn a_chain_left_open_on_an_unmarked_main_thread_frame_is_propagated() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "E", "x"),
            ret_err(3, "E", "x"),
            Input {
                seq: 4,
                rec: Rec::ThreadEnd,
            },
        ],
        false,
    );
    assert_eq!(
        last_of(&events, FIRST_CHAIN_SERIAL).terminal,
        Some(Terminal::Propagated)
    );
}

/// Chain serials are a namespace of their own, disjoint from the per-thread
/// panic serials `frames.rs` mints from 1 (design R7).
#[test]
fn chain_serials_start_at_the_thirty_third_bit_and_count_up() {
    let events = mint(
        &[
            call(0),
            flow(1, How::SinkOk, "A", "1"),
            flow(2, How::SinkOk, "B", "2"),
            ret(3, Outcome::Ok),
        ],
        false,
    );
    assert_eq!(events[0].serial, 1 << 32);
    assert_eq!(events[1].serial, (1 << 32) + 1);
}

/// An `Err(_) =>` arm records neither type nor text, so it must not look
/// like a different `Err` and split the chain it continues (design R4).
#[test]
fn an_unbound_arms_record_continues_the_chain_it_lands_in() {
    let events = mint(
        &[
            call(0),
            call(1),
            ret_err(2, "io::Error", "E1"),
            Input {
                seq: 3,
                rec: Rec::ErrFlow {
                    how: How::ArmPropagate,
                    text: ErrText::default(),
                },
            },
            ret(4, Outcome::Ok),
        ],
        false,
    );
    assert_eq!(serials(&events).len(), 1, "{events:#?}");
    assert_eq!(events[1].hop, 2);
    assert_eq!(
        events[1].origin_type.as_deref(),
        Some("io::Error"),
        "an unbound arm takes its type from the chain it continues"
    );
}

/// An err-flow record on a thread with no open frame is not this machine's
/// business: `frames.rs` counts it and writes no event, so no chain may be
/// invented for it.
#[test]
fn an_err_flow_record_with_no_open_frame_mints_nothing() {
    let events = mint(&[flow(0, How::Try, "E", "x")], false);
    assert!(events.is_empty());
}
