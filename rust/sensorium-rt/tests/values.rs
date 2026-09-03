//! Return values: the 200-byte cap, the two ways a value goes unread, and the
//! per-thread truncation counter.

mod common;

use common::{Spec, TempDir, KIND_RETURN, OUTCOME_OK, TAG_DEBUG, TAG_UNREAD};

/// The cap the runtime formats through, restated here rather than imported, so
/// that moving it in `probe.rs` fails this file.
const CAP: usize = 200;

#[test]
fn a_value_with_no_debug_impl_reads_unread() {
    let dir = TempDir::reserved("values-nodebug");
    Spec::new("value-nodebug").spool(dir.path()).run();
    let r = dir.spool(1).the_return(20);
    assert_eq!(
        r.outcome, OUTCOME_OK,
        "a non-Result value crosses the boundary as ok"
    );
    let (tag, trunc, text) = r.ret_value();
    assert_eq!(tag, TAG_UNREAD);
    assert!(!trunc);
    assert_eq!(text, "", "unread is unread: there is no text to carry");
}

/// The cap bounds what a capture COSTS IN BYTES, whatever the value's size: a
/// 10^3-element and a 10^6-element `Vec` produce the same 200-byte payload and
/// the same 200-byte allocation.
///
/// It does NOT bound the traversal (`rust/HONESTY.md` §2): std's collection
/// `Debug` impls go through `Formatter::debug_list`, which short-circuits its
/// WRITES once the writer errors but still walks every element. Measured on
/// this box, a 10^6-element `Vec<u8>` capture costs ~10 ms with the cap and
/// ~8 ms without it. The arm below pins the case where the cap does stop the
/// work.
#[test]
fn a_vecs_capture_is_the_cap_whatever_the_vec_is() {
    let mut texts = Vec::new();
    for n in ["1000", "1000000"] {
        let dir = TempDir::reserved(&format!("values-big-{n}"));
        Spec::new("value-big").arg(n).spool(dir.path()).run();
        let s = dir.spool(1);
        let r = s.the_return(21);
        let (tag, trunc, text) = r.ret_value();
        assert_eq!(tag, TAG_DEBUG);
        assert!(trunc, "n={n}: the flag says the text is a prefix");
        assert_eq!(
            text.len(),
            CAP,
            "n={n}: the capping writer stops at {CAP} bytes, {} captured",
            text.len()
        );
        assert!(
            text.starts_with("[7, 7, 7"),
            "n={n}: the prefix is the real rendering"
        );
        assert_eq!(s.truncated, 1, "n={n}: one truncated capture, counted once");
        assert_eq!(
            r.payload.len(),
            2 + CAP,
            "n={n}: the wire payload is bounded by the cap too"
        );
        texts.push(text);
    }
    assert_eq!(
        texts[0], texts[1],
        "a thousand elements and a million read back identically"
    );
}

/// The mechanism, on the shape it works for: a hand-written `Debug` that
/// propagates the writer's error stops at the cap instead of running to the end.
/// Measured: 10^7 items cost ~1.5 us with the cap and ~99 ms without it.
#[test]
fn a_debug_impl_that_propagates_the_writers_error_stops_at_the_cap() {
    let dir = TempDir::reserved("values-earlystop");
    let run = Spec::new("value-early-stop")
        .arg("10000000")
        .spool(dir.path())
        .run();
    let r = dir.spool(1).the_return(24);
    let (tag, trunc, text) = r.ret_value();
    assert_eq!(tag, TAG_DEBUG);
    assert!(trunc);
    assert_eq!(text.len(), CAP);

    let ns = run.says_u64("capture_ns");
    assert!(
        ns < 10_000_000,
        "capturing 10^7 items took {ns} ns; the writer's Err must abort the formatter, \
         not merely suppress its output"
    );
}

#[test]
fn a_debug_impl_that_panics_reads_unread_and_the_program_continues() {
    let dir = TempDir::reserved("values-panicdbg");
    let run = Spec::new("value-panic-debug").spool(dir.path()).run();
    assert_eq!(run.says("survived"), "1", "the program was not unwound");
    let r = dir.spool(1).the_return(22);
    let (tag, trunc, text) = r.ret_value();
    assert_eq!(
        tag, TAG_UNREAD,
        "a panicking Debug and a missing Debug are the same two bytes on the wire"
    );
    assert!(!trunc);
    assert_eq!(text, "");
    assert!(
        !run.stderr.contains("panicked"),
        "an instrument-provoked panic is caught silently; stderr was: {:?}",
        run.stderr
    );
    assert_eq!(
        dir.spool(1).truncated,
        0,
        "a capture that could not be read was not truncated"
    );
}

#[test]
fn the_thread_header_counts_every_truncated_capture() {
    let dir = TempDir::reserved("values-truncount");
    let run = Spec::new("value-truncations")
        .arg("5")
        .spool(dir.path())
        .run();
    assert_eq!(run.says_u64("truncations"), 5);
    let s = dir.spool(1);
    let rets: Vec<_> = s
        .of_kind(KIND_RETURN)
        .into_iter()
        .filter(|r| r.site_index() == 23)
        .collect();
    assert_eq!(rets.len(), 5);
    for r in &rets {
        let (tag, trunc, text) = r.ret_value();
        assert_eq!(tag, TAG_DEBUG);
        assert!(trunc, "each of these renderings is longer than the cap");
        assert_eq!(text.len(), CAP);
    }
    assert_eq!(
        s.truncated, 5,
        "the header counter is the number of truncated captures on this thread"
    );
    assert_eq!(s.records_dropped, 0);
}
