//! §2a of the design continued: the terminal each chain closes with, and the
//! boundary shapes that decide it. Split from `tests.rs` at its `row 8` item
//! (the file was near the 800-line ceiling); the eight fixture helpers stay
//! in `tests.rs` and are shared from there, never copied.

use super::tests::*;
use super::*;

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

/// The keep-first-error shape (design §3, CARRIED-DEBT 2026-09-05): A holds
/// TWO chains -- B1 from `first`, then C1 from `second` on top -- and returns
/// B1. The exit hop belongs to the chain whose text the RETURN carries, not to
/// the innermost; before the borrow-repair slice it went to C1 labelled
/// `translated`, and B1 was left without its hop.
#[test]
fn an_err_close_hops_the_held_chain_whose_text_it_carries_not_the_innermost() {
    let events = mint(
        &[
            call(0),                     // A
            call(1),                     // first
            ret_err(2, "demo::E", "B1"), // chain B1, holder A
            call(3),                     // second
            ret_err(4, "demo::E", "C1"), // chain C1, holder A, innermost
            ret_err(5, "demo::E", "B1"), // A returns the FIRST error
        ],
        false,
    );
    let s = serials(&events);
    assert_eq!(s.len(), 2, "two chains, no merge: {events:#?}");
    let (b1, c1) = (events[0].serial, events[1].serial);
    let exit = events
        .iter()
        .find(|e| e.seq == 5)
        .unwrap_or_else(|| panic!("no event at A's close: {events:#?}"));
    assert_eq!(
        exit.serial, b1,
        "the hop is B1's, whose text the RETURN carries"
    );
    assert!(
        !exit.translated,
        "same text, so not a translation: {exit:#?}"
    );
    assert_eq!(exit.hop, 2);
    assert!(
        !events.iter().any(|e| e.seq == 5 && e.serial == c1),
        "C1 took no exit hop: {events:#?}"
    );
    for serial in [b1, c1] {
        assert_ne!(last_of(&events, serial).terminal, Some(Terminal::Merged));
    }
}

/// Mutation guard for `preferred`'s `!c.sink` filter (design B3): the held
/// chain whose text the RETURN carries can be `sink` -- about to end
/// `handled_then_failed`, not take an exit hop -- and that must not make
/// `preferred` name it anyway. When the matching chain is `sink`, the
/// innermost NON-matching chain takes the fallback hop, exactly as when no
/// held chain matches at all; a `preferred` that ignored `sink` would instead
/// leave the fallback chain unhopped and open a THIRD chain at the exit.
#[test]
fn a_sink_chain_matching_the_return_text_still_falls_back_to_the_innermost() {
    let events = mint(
        &[
            call(0),                               // A
            call(1),                               // first
            ret_err(2, "demo::E", "B1"),           // chain B1, holder A
            call(3),                               // second
            ret_err(4, "demo::E", "C1"),           // chain C1, holder A, innermost
            flow(5, How::SinkOk, "demo::E", "B1"), // A absorbs B1: B1.sink = true
            ret_err(6, "demo::E", "B1"),           // A closes err with B1's text, but B1 is sink
        ],
        false,
    );
    let s = serials(&events);
    assert_eq!(
        s.len(),
        2,
        "no third chain is born at the exit: {events:#?}"
    );
    let (b1, c1) = (events[0].serial, events[1].serial);
    assert_eq!(
        last_of(&events, b1).terminal,
        Some(Terminal::HandledThenFailed),
        "B1 was absorbed, then its holder failed anyway: {events:#?}"
    );
    let exit = events
        .iter()
        .find(|e| e.seq == 6)
        .unwrap_or_else(|| panic!("no event at A's close: {events:#?}"));
    assert_eq!(
        exit.serial, c1,
        "B1 matches the text but is sink, so C1 -- the innermost eligible held \
         chain -- takes the fallback hop: {events:#?}"
    );
    assert_eq!(exit.hop, 2, "a hop of C1, not a fresh chain: {events:#?}");
    assert!(
        exit.translated,
        "the fallback hop carries B1's text onto C1's chain, a type/text \
         change from what C1 last recorded: {exit:#?}"
    );
}

/// Design B3's wildcard case, pinned: a RETURN with an UNREAD text (both
/// `ErrText` fields `None`, e.g. an untyped `err` close or one whose `Debug`
/// impl panicked) matches every held chain, so `preferred` resolves to the
/// innermost and the fallback IS today's pre-borrow-repair behaviour.
#[test]
fn an_err_close_with_an_unread_text_falls_back_to_the_innermost_held_chain() {
    let events = mint(
        &[
            call(0),                     // A
            call(1),                     // first
            ret_err(2, "demo::E", "B1"), // chain B1, holder A
            call(3),                     // second
            ret_err(4, "demo::E", "C1"), // chain C1, holder A, innermost
            ret(5, Outcome::Err),        // A closes err with an UNREAD (wildcard) text
        ],
        false,
    );
    let s = serials(&events);
    assert_eq!(s.len(), 2, "two chains, no merge: {events:#?}");
    let c1 = events[1].serial;
    let exit = events
        .iter()
        .find(|e| e.seq == 5)
        .unwrap_or_else(|| panic!("no event at A's close: {events:#?}"));
    assert_eq!(
        exit.serial, c1,
        "a wildcard text matches every chain, so the fallback is the \
         innermost: {events:#?}"
    );
    assert_eq!(exit.hop, 2);
}
