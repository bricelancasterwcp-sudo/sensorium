//! The chained panic hook, read off the spool bytes and off the program's own
//! stderr.
//!
//! Three things are pinned here, and they pull in opposite directions:
//!
//! * a panic that crosses an instrumented frame leaves a PANIC record on that
//!   thread's spool, carrying the location and message the hook saw;
//! * a panic the *instrument itself* provoked -- a `Debug` impl that panics
//!   while the recorder is formatting it -- leaves nothing and says nothing;
//! * and in every case the program's own output is byte-for-byte what it would
//!   have been with no recorder linked in at all (endpoint E7). That last one is
//!   why the hook chains rather than replaces: a recorder that changed what a
//!   panicking program printed would be changing the thing it claims to observe.

mod common;

use common::{
    Spec, TempDir, KIND_CALL, KIND_PANIC, KIND_RETURN, OUTCOME_NONE, OUTCOME_OK, OUTCOME_PANIC,
    TAG_NO_VALUE,
};

/// The scenario prints `panic_site <file>:<line>` from the SAME source line as
/// the `panic!`, so this compares the hook's location against the source rather
/// than against a number written down twice. The column is whatever rustc gives
/// the macro; it is asserted present and non-zero, not equal to a constant.
fn assert_location(loc: &str, site: &str) {
    let rest = loc
        .strip_prefix(site)
        .and_then(|r| r.strip_prefix(':'))
        .unwrap_or_else(|| panic!("panic location {loc:?} is not at {site:?}"));
    let col: u32 = rest
        .parse()
        .unwrap_or_else(|e| panic!("panic location {loc:?} has no column: {e}"));
    assert!(col > 0, "columns are 1-based, got {col} in {loc:?}");
}

#[test]
fn a_panic_inside_a_frame_writes_a_panic_record_then_a_return_with_outcome_panic() {
    let dir = TempDir::reserved("panics-caught-uninstrumented");
    let run = Spec::new("ret-panic").spool(dir.path()).run();
    let s = dir.spool(1);

    let panics = s.of_kind(KIND_PANIC);
    assert_eq!(panics.len(), 1, "one panic, one PANIC record");
    let (loc, msg) = panics[0].panic_value();
    assert_location(&loc, &run.says("panic_site"));
    assert_eq!(msg, "boom");
    assert_eq!(
        panics[0].outcome, OUTCOME_NONE,
        "outcome is a RETURN's field; a PANIC record carries 0"
    );
    assert_eq!(
        panics[0].site, 0,
        "a panic is not AT an instrumented site: the site word is the same \
         not-a-site a THREAD_END record carries, and the location is in the \
         payload"
    );

    // Order on the wire: the frame opened, then the panic, then the frame
    // closed. A converter attaches the most recent PANIC on the thread to the
    // frame that then closes `panic`, so it depends on exactly this ordering.
    let kinds: Vec<u8> = s
        .records
        .iter()
        .filter(|r| r.kind != common::KIND_THREAD_END)
        .map(|r| r.kind)
        .collect();
    assert_eq!(kinds, vec![KIND_CALL, KIND_PANIC, KIND_RETURN]);
    let ret = s.the_return(14);
    assert_eq!(ret.outcome, OUTCOME_PANIC);
    assert!(
        panics[0].seq < ret.seq,
        "the PANIC record is minted before the RETURN it explains"
    );
}

#[test]
fn a_caught_panic_closes_the_inner_frame_panic_and_the_outer_frame_ok() {
    let dir = TempDir::reserved("panics-caught-instrumented");
    let run = Spec::new("panic-caught").spool(dir.path()).run();
    assert_eq!(run.says("caught"), "1");
    let s = dir.spool(1);

    let panics = s.of_kind(KIND_PANIC);
    assert_eq!(panics.len(), 1);
    let (loc, msg) = panics[0].panic_value();
    assert_location(&loc, &run.says("panic_site"));
    assert_eq!(msg, "caught boom");

    let inner = s.the_return(16);
    let outer = s.the_return(17);
    assert_eq!(inner.outcome, OUTCOME_PANIC, "the frame the panic crossed");
    assert_eq!(inner.ret_value().0, TAG_NO_VALUE);
    assert_eq!(
        outer.outcome, OUTCOME_OK,
        "the frame that CAUGHT it returned normally, and a caught panic is not \
         the catching frame's outcome"
    );
    assert!(
        panics[0].seq < inner.seq && inner.seq < outer.seq,
        "PANIC, then the inner frame, then the outer one"
    );
}

#[test]
fn a_payload_that_is_not_a_string_is_recorded_as_one_that_is_not() {
    let dir = TempDir::reserved("panics-non-string");
    let run = Spec::new("panic-non-string").spool(dir.path()).run();
    let panics = dir.spool(1).of_kind(KIND_PANIC);
    assert_eq!(panics.len(), 1);
    let (loc, msg) = panics[0].panic_value();
    assert_location(&loc, &run.says("panic_site"));
    assert_eq!(
        msg, "<non-string payload>",
        "the hook reads &str and String payloads; anything else it says it \
         could not read, rather than rendering it some other way"
    );
}

#[test]
fn a_long_panic_message_is_cut_on_a_char_boundary_and_counted_in_the_header() {
    let dir = TempDir::reserved("panics-long");
    let run = Spec::new("panic-long").spool(dir.path()).run();
    assert_eq!(
        run.says_u64("msg_bytes"),
        6000,
        "the scenario's message is longer than the cap, or this pins nothing"
    );
    let s = dir.spool(1);
    let panics = s.of_kind(KIND_PANIC);
    assert_eq!(panics.len(), 1);
    let (_loc, msg) = panics[0].panic_value();
    // '€' is three bytes and the 4096-byte cap lands inside one, so the cut
    // steps back to 4095. `panic_value` has already refused a non-UTF-8 cut.
    assert_eq!(
        msg.len(),
        4095,
        "the message is cut at the cap, on a char boundary"
    );
    assert!(msg.chars().all(|c| c == '\u{20ac}'), "and nowhere else");
    assert!(
        panics[0].payload.len() <= u16::MAX as usize,
        "the payload fits the wire format's length field"
    );
    assert_eq!(
        s.truncated, 1,
        "a cut the hook made is counted in the thread header, which is the only \
         witness a PANIC record has -- it carries no truncated byte of its own"
    );
}

#[test]
fn the_hook_is_silent_for_a_panic_the_instrument_provoked() {
    let dir = TempDir::reserved("panics-in-runtime");
    let run = Spec::new("value-panic-debug").spool(dir.path()).run();
    assert_eq!(run.says("survived"), "1");
    for s in dir.spools() {
        assert!(
            s.of_kind(KIND_PANIC).is_empty(),
            "a `Debug` impl that panicked inside the instrument is not the \
             program panicking; spool {} recorded one",
            s.serial
        );
    }
    assert_eq!(
        run.stderr, "",
        "and the hook does not chain for it either: nothing is printed"
    );
}

/// The header's `truncated` counter witnesses truncations that reached the
/// wire. A message cut on a thread with no spool is a message no reader will
/// ever meet, and counting it would make the header describe a record that does
/// not exist -- in the one case where the thread goes on to open a spool anyway.
#[test]
fn a_truncation_the_hook_could_not_write_is_not_counted() {
    let dir = TempDir::reserved("panics-truncated-before-spool");
    let run = Spec::new("panic-truncated-before-spool")
        .spool(dir.path())
        .run();
    assert_eq!(run.says("survived"), "1");
    assert_eq!(run.says_u64("msg_bytes"), 6000, "past the hook's 4096 cap");
    let child = dir
        .spools()
        .into_iter()
        .find(|s| s.serial != 1)
        .expect("the unwinding thread opened a spool from its Drop");
    assert!(
        child.of_kind(KIND_PANIC).is_empty(),
        "the thread had no spool when the hook ran, so the PANIC record went \
         nowhere -- which is what makes the counter's claim checkable"
    );
    assert!(
        !child.of_kind(KIND_CALL).is_empty(),
        "and it DID open one during the unwind, or this pins nothing"
    );
    assert_eq!(
        child.truncated, 0,
        "a cut the hook could not write is not a truncation this thread's \
         header should claim"
    );
}

/// The hook opens nothing. A thread that panics having recorded no event has no
/// frame for a PANIC record to close, and buying that record would cost the
/// guarantee that the hook cannot fail -- a hook that failed would print, and a
/// second panic while the thread is already panicking aborts the process.
#[test]
fn a_panic_on_a_thread_that_recorded_nothing_opens_no_spool() {
    let dir = TempDir::reserved("panics-unrecorded-thread");
    let run = Spec::new("panic-unrecorded-thread").spool(dir.path()).run();
    assert_eq!(run.says("survived"), "1");
    let spools = dir.spools();
    assert_eq!(
        spools.len(),
        1,
        "only the thread that recorded an event has a spool; found {:?}",
        spools.iter().map(|s| s.serial).collect::<Vec<_>>()
    );
    assert_eq!(spools[0].serial, 1, "and it is main's");
    assert!(
        spools[0].of_kind(KIND_PANIC).is_empty(),
        "a panic on another thread is not main's panic"
    );
    assert!(
        run.stderr.contains("orphan boom"),
        "the program still printed it: recording nothing is not silencing \
         anything; stderr was {:?}",
        run.stderr
    );
}

/// rustc's panic message names the thread AND its OS thread id -- `thread
/// 'main' (3844444) panicked at ...` -- and the id differs between two
/// processes for reasons that have nothing to do with this recorder. That token,
/// and only that token, is masked. The count comes back with the text so a test
/// can refuse to compare two strings the mask never fired on.
fn mask_thread_ids(stderr: &str) -> (String, usize) {
    const MARK: &str = ") panicked at ";
    let mut out = String::with_capacity(stderr.len());
    let mut rest = stderr;
    let mut masked = 0usize;
    while let Some(at) = rest.find(MARK) {
        let Some(open) = rest[..at].rfind("' (") else {
            break;
        };
        let digits = &rest[open + 3..at];
        if digits.is_empty() || !digits.bytes().all(|b| b.is_ascii_digit()) {
            break;
        }
        out.push_str(&rest[..open + 3]);
        out.push_str("<tid>");
        out.push_str(MARK);
        rest = &rest[at + MARK.len()..];
        masked += 1;
    }
    out.push_str(rest);
    (out, masked)
}

#[test]
fn masking_touches_the_thread_id_and_nothing_else() {
    let (masked, n) = mask_thread_ids(
        "thread 'main' (123) panicked at src/x.rs:1:2:\nboom (7) and (8)\n\
         thread '<unnamed>' (4) panicked at src/x.rs:3:4:\nlater\n",
    );
    assert_eq!(n, 2);
    assert_eq!(
        masked,
        "thread 'main' (<tid>) panicked at src/x.rs:1:2:\nboom (7) and (8)\n\
         thread '<unnamed>' (<tid>) panicked at src/x.rs:3:4:\nlater\n"
    );
    assert_eq!(mask_thread_ids("nothing here"), ("nothing here".into(), 0));
}

/// Endpoint E7, at the granularity that matters for a panic: the same program,
/// once with the recorder configured and once without, prints the same bytes.
#[test]
fn the_chained_hook_changes_not_one_byte_of_the_programs_own_stderr() {
    // (scenario, how many panic messages the program itself prints)
    for (scenario, expected_messages) in [
        ("ret-panic", 1),
        ("panic-caught", 1),
        ("panic-non-string", 1),
        ("panic-uncaught", 1),
        // The instrument-provoked one: silent with the recorder on, and no
        // panic at all with it off, because the capture never runs.
        ("value-panic-debug", 0),
    ] {
        let dir = TempDir::reserved(&format!("panics-e7-{scenario}"));
        let off = Spec::new(scenario)
            .env("RUST_BACKTRACE", "0")
            .allow_failure()
            .run();
        let on = Spec::new(scenario)
            .spool(dir.path())
            .env("RUST_BACKTRACE", "0")
            .allow_failure()
            .run();

        let (off_text, off_n) = mask_thread_ids(&off.stderr);
        let (on_text, on_n) = mask_thread_ids(&on.stderr);
        assert_eq!(
            off_text, on_text,
            "{scenario}: the recorder changed the program's stderr"
        );
        assert_eq!(off_n, expected_messages, "{scenario}: without the recorder");
        assert_eq!(on_n, expected_messages, "{scenario}: with it");
        assert_eq!(
            off.output.status.code(),
            on.output.status.code(),
            "{scenario}: and the exit status is the program's own"
        );
        if expected_messages > 0 {
            assert!(
                off.stderr.contains("panicked at"),
                "{scenario}: this arm compares two panic messages, not two empty \
                 strings; stderr was {:?}",
                off.stderr
            );
        }
        // The recorder still recorded: an identical stderr from a run that
        // wrote nothing would prove nothing.
        assert!(
            !dir.spools().is_empty(),
            "{scenario}: the configured run recorded no spool at all"
        );
    }
}

#[test]
fn an_uncaught_panic_leaves_the_frame_open_at_neither_end() {
    let dir = TempDir::reserved("panics-uncaught");
    let run = Spec::new("panic-uncaught")
        .spool(dir.path())
        .allow_failure()
        .run();
    assert_eq!(
        run.output.status.code(),
        Some(101),
        "an unhandled panic is still the program's own exit status"
    );
    let s = dir.spool(1);
    let panics = s.of_kind(KIND_PANIC);
    assert_eq!(panics.len(), 1);
    assert_eq!(panics[0].panic_value().1, "uncaught boom");
    let ret = s.the_return(18);
    assert_eq!(
        ret.outcome, OUTCOME_PANIC,
        "unwinding out of main still drops the guard"
    );
    assert!(
        s.has_thread_end(),
        "and still runs the thread-local destructor that ends the spool"
    );
}
