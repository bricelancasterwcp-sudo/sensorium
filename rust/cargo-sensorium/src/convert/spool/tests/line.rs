//! The LINE payload reader's tests (wire kind 6), over HAND-BUILT bytes --
//! `super::tests`'s discipline and `super::tests`'s reason for being a
//! separate file: the two together passed 800 lines, and a LINE payload is a
//! subject of its own (its own grammar, its own four-then-five tags, its own
//! version gate).
//!
//! Every fixture here is written from the format block at the top of
//! [`super::line`], never by running the runtime, so a bug the writer and the
//! reader share cannot pass them.

use super::super::line::{parse_line_payload, LinePayload};
use super::super::KIND_LINE;

/// The v3 reading, which is what every fixture below that predates wire v4
/// asks for. The version is a PARAMETER of the reader because tag 4 is legal
/// only from v4 (B1), so a fixture written before it must say which reading
/// it is pinning rather than inherit today's.
fn parse_line_v3(label: &str, payload: &[u8]) -> Result<LinePayload, String> {
    parse_line_payload(label, payload, 3)
}

/// One delta block, by the grammar: `u16 name_len, name, u8 tag, u8 truncated,
/// [u16 text_len, text] iff tag == 1`. Built here rather than by a typed helper
/// so the tag byte can be anything -- including the 0 the runtime never writes.
fn delta(name: &[u8], tag: u8, truncated: u8, text: Option<&str>) -> Vec<u8> {
    let mut b = (name.len() as u16).to_le_bytes().to_vec();
    b.extend_from_slice(name);
    b.push(tag);
    b.push(truncated);
    if let Some(text) = text {
        b.extend_from_slice(&(text.len() as u16).to_le_bytes());
        b.extend_from_slice(text.as_bytes());
    }
    b
}

fn line_payload(flags: u8, blocks: &[Vec<u8>]) -> Vec<u8> {
    let mut b = vec![flags];
    b.extend_from_slice(&(blocks.len() as u16).to_le_bytes());
    for block in blocks {
        b.extend_from_slice(block);
    }
    b
}

/// Task 1's own pinned vector for `("x", debug "5"), ("buf", unread)`, byte for
/// byte (`sensorium-rt/src/line/tests.rs`
/// `two_deltas_encode_to_the_bytes_the_wire_format_names`). The two sides are
/// written independently from the same grammar; this is where they are held
/// against each other.
#[test]
fn a_line_payload_round_trips_the_vector_the_runtimes_own_test_pins() {
    #[rustfmt::skip]
    let payload: Vec<u8> = vec![
        0x00,                         // flags: nothing dropped
        0x02, 0x00,                   // n = 2
        0x01, 0x00, b'x',             // name_len 1, "x"
        0x01, 0x00,                   // tag 1 (debug text), truncated 0
        0x01, 0x00, b'5',             // text_len 1, "5"
        0x03, 0x00, b'b', b'u', b'f', // name_len 3, "buf"
        0x02, 0x00,                   // tag 2 (unread), truncated 0
    ];
    let p = parse_line_v3("t", &payload).unwrap();
    assert!(!p.dropped);
    assert_eq!(p.deltas.len(), 2);
    assert_eq!(p.deltas[0].0, "x");
    assert_eq!(
        p.deltas[0].1,
        serde_json::json!({"k": "dbg", "v": "5", "trunc": false})
    );
    assert_eq!(p.deltas[1].0, "buf");
    assert_eq!(p.deltas[1].1, serde_json::json!({"k": "unread"}));
}

/// A statement that wrote nothing is still a row: three bytes, no deltas, and
/// NOT a refusal.
#[test]
fn a_line_payload_with_no_deltas_is_a_record_not_an_error() {
    let p = parse_line_v3("t", &[0, 0, 0]).unwrap();
    assert!(!p.dropped);
    assert!(p.deltas.is_empty());
}

/// `flags.bit0` is the runtime saying the record is SHORT. A reader that
/// dropped it would report a partial statement as a complete one.
#[test]
fn the_dropped_flag_is_read_off_bit_zero() {
    let p = parse_line_v3("t", &line_payload(1, &[delta(b"x", 2, 0, None)])).unwrap();
    assert!(p.dropped);
    assert_eq!(p.deltas.len(), 1);
}

/// The writer's own truncation flag rides the delta, exactly as it does on a
/// RETURN value.
#[test]
fn a_cut_debug_text_carries_trunc_true() {
    let p = parse_line_v3("t", &line_payload(0, &[delta(b"s", 1, 1, Some("ab"))])).unwrap();
    assert_eq!(
        p.deltas[0].1,
        serde_json::json!({"k": "dbg", "v": "ab", "trunc": true})
    );
}

/// An empty `Debug` rendering was READ and rendered nothing (tag 1); a value
/// with no `Debug` impl was not read at all (tag 2). The runtime keeps the two
/// apart in bytes, and so must this reader.
#[test]
fn an_empty_debug_rendering_stays_a_read_value_here_too() {
    let p = parse_line_v3("t", &line_payload(0, &[delta(b"s", 1, 0, Some(""))])).unwrap();
    assert_eq!(
        p.deltas[0].1,
        serde_json::json!({"k": "dbg", "v": "", "trunc": false})
    );
}

#[test]
fn a_line_payload_shorter_than_its_three_fixed_bytes_is_refused_by_label() {
    let err = parse_line_v3("pid 1 thread 1 seq 4", &[0, 0]).unwrap_err();
    assert!(err.contains("pid 1 thread 1 seq 4"), "{err}");
    assert!(err.contains("LINE payload"), "{err}");
}

/// Three ways one record can run off its own end: a name, a text, and a delta
/// block that stops mid-header. Each names the label and the delta.
#[test]
fn a_line_payload_that_runs_past_its_end_is_refused_by_label_and_field() {
    let mut name_past = line_payload(0, &[delta(b"xyz", 2, 0, None)]);
    name_past.truncate(6); // "xyz" cut to one byte
    let err = parse_line_v3("L", &name_past).unwrap_err();
    assert!(err.contains('L'), "{err}");
    assert!(err.contains("name"), "{err}");

    let mut text_past = line_payload(0, &[delta(b"x", 1, 0, Some("hello"))]);
    text_past.truncate(text_past.len() - 3);
    let err = parse_line_v3("L", &text_past).unwrap_err();
    assert!(err.contains("delta `x`"), "{err}");
    assert!(err.contains("text"), "{err}");

    // `block` and not `delta`: with no tag byte there is nothing to say which
    // of the two this was.
    let short_block = line_payload(0, &[vec![0x01, 0x00, b'x']]); // no tag byte
    let err = parse_line_v3("L", &short_block).unwrap_err();
    assert!(err.contains("block `x`"), "{err}");
}

/// Design amendment A7: tag 0 is legal in the grammar and unwritable by the
/// runtime, so meeting one is corruption -- and the refusal names the delta,
/// never a row guessed from it.
#[test]
fn a_delta_carrying_tag_zero_is_refused_by_name() {
    let err = parse_line_v3("L", &line_payload(0, &[delta(b"x", 0, 0, None)])).unwrap_err();
    assert!(err.contains('L'), "{err}");
    assert!(err.contains("delta `x`"), "{err}");
    assert!(err.contains("tag 0"), "{err}");
}

#[test]
fn a_delta_carrying_an_unknown_tag_is_refused_by_number() {
    let err = parse_line_v3("L", &line_payload(0, &[delta(b"x", 4, 0, None)])).unwrap_err();
    assert!(err.contains("delta `x`"), "{err}");
    assert!(err.contains("tag 4"), "{err}");
    assert!(err.contains("not 0..=3"), "{err}");
}

/// The deltas become one JSON OBJECT, so a repeated name would silently
/// overwrite the earlier reading and the row would claim a statement wrote one
/// value where the record says two. The transformer never emits a duplicate
/// (one splice, one `bound_names` walk), so meeting one is corruption.
#[test]
fn a_duplicate_delta_name_within_one_record_is_refused() {
    let payload = line_payload(0, &[delta(b"x", 2, 0, None), delta(b"x", 1, 0, Some("5"))]);
    let err = parse_line_v3("L", &payload).unwrap_err();
    assert!(err.contains('L'), "{err}");
    assert!(err.contains("delta `x`"), "{err}");
    assert!(err.contains("twice"), "{err}");
}

#[test]
fn a_delta_name_that_is_not_utf8_is_refused() {
    let err = parse_line_v3("L", &line_payload(0, &[delta(&[0xff], 2, 0, None)])).unwrap_err();
    assert!(err.contains("not UTF-8"), "{err}");
}

// -- tag 3: the names a statement's scope took with it (rt 0.5.0) -----------

/// The fourth tag is a NAME and not a value: it says this binding's scope
/// ended on this row (design 2026-09-12 §5.3), so it belongs in `unbound` and
/// nowhere in `deltas`. A reader that routed it into the deltas would fold a
/// dead name forward as though the statement had written it -- the exact
/// wrong answer the tag exists to prevent.
#[test]
fn a_tag_three_block_is_an_unbound_name_and_never_a_delta() {
    let p = parse_line_v3("t", &line_payload(0, &[delta(b"a", 3, 0, None)])).unwrap();
    assert_eq!(p.unbound, ["a"]);
    assert!(p.deltas.is_empty(), "{:?}", p.deltas);
    assert!(!p.dropped);
}

/// `n` counts deltas AND names, the names ride after the deltas, and each list
/// keeps the order the record carried -- source order, which is what `frame`
/// prints after `unbound:`.
#[test]
fn deltas_and_unbound_names_ride_one_record_each_into_its_own_list() {
    let payload = line_payload(
        0,
        &[
            delta(b"acc", 1, 0, Some("6")),
            delta(b"n", 3, 0, None),
            delta(b"big", 3, 0, None),
        ],
    );
    let p = parse_line_v3("t", &payload).unwrap();
    assert_eq!(p.deltas.len(), 1);
    assert_eq!(p.deltas[0].0, "acc");
    assert_eq!(
        p.deltas[0].1,
        serde_json::json!({"k": "dbg", "v": "6", "trunc": false})
    );
    assert_eq!(p.unbound, ["n", "big"], "record order, not sorted");
}

/// `flags.bit0` is over the WHOLE payload: a name that did not fit sets it and
/// ends the row exactly as a delta does, so a short record carrying names is
/// still a short record and still says so.
#[test]
fn a_short_record_that_carries_names_is_still_marked_short() {
    let payload = line_payload(1, &[delta(b"x", 2, 0, None), delta(b"y", 3, 0, None)]);
    let p = parse_line_v3("t", &payload).unwrap();
    assert!(p.dropped);
    assert_eq!(p.deltas.len(), 1);
    assert_eq!(p.unbound, ["y"]);
}

/// A statement writes what it writes and unbinds what dies with it, and the
/// transformer lists a name bound in both a head pattern and an inner `let`
/// ONCE -- so a name on both lists is corruption, in either order, and the
/// refusal says which contradiction it met rather than keying one over the
/// other.
#[test]
fn a_name_on_both_lists_within_one_record_is_refused_in_either_order() {
    let expected = "L: LINE payload names `x` as both a delta and an unbound name; a statement \
                    cannot write what it unbinds";

    let delta_first = line_payload(0, &[delta(b"x", 1, 0, Some("2")), delta(b"x", 3, 0, None)]);
    assert_eq!(parse_line_v3("L", &delta_first).unwrap_err(), expected);

    let name_first = line_payload(0, &[delta(b"x", 3, 0, None), delta(b"x", 1, 0, Some("2"))]);
    assert_eq!(parse_line_v3("L", &name_first).unwrap_err(), expected);
}

/// The same rule read on the second list: a scope ends once, so a name listed
/// twice as unbound is the same corruption a repeated delta is, and the
/// sentence names which list it met it on.
#[test]
fn a_duplicate_unbound_name_within_one_record_is_refused() {
    let payload = line_payload(0, &[delta(b"x", 3, 0, None), delta(b"x", 3, 0, None)]);
    let err = parse_line_v3("L", &payload).unwrap_err();
    assert!(err.contains('L'), "{err}");
    assert!(err.contains("unbound name `x`"), "{err}");
    assert!(err.contains("twice"), "{err}");
}

/// `n` and the payload's length must agree exactly: bytes after the last delta
/// are a record this reader cannot account for, not padding to skip.
#[test]
fn bytes_after_the_last_delta_are_refused() {
    let mut payload = line_payload(0, &[delta(b"x", 2, 0, None)]);
    payload.push(0);
    let err = parse_line_v3("L", &payload).unwrap_err();
    assert!(err.contains("L: "), "{err}");
    assert!(err.contains("after"), "{err}");
}

// -- tag 4: a delta the RUNTIME redacted by name (wire v4) -----------------

/// The capture a tag-4 block reads as: the marker where the value was, the
/// digest the runtime wrote in its place, and `trunc: false` -- the wire's
/// truncated byte is 0 on this tag by construction (B1: a digest never says
/// whether the value it stands for was cut), so the row says so in words.
#[test]
fn a_tag_four_delta_reads_as_a_capture_the_recorder_took_by_name() {
    let payload = line_payload(0, &[delta(b"token", 4, 0, Some("aabbccddeeff0011"))]);
    let p = parse_line_payload("t", &payload, 4).unwrap();
    assert_eq!(p.deltas.len(), 1);
    assert_eq!(p.deltas[0].0, "token");
    assert_eq!(
        p.deltas[0].1,
        serde_json::json!({"k": "dbg", "v": "<redacted>", "trunc": false,
                           "redacted": {"by": "name", "digest": "aabbccddeeff0011"}})
    );
}

/// An UNKEYED recorder writes the tag with an EMPTY text block: the value was
/// taken, and there is no digest to put beside it. `null` and not `""` -- the
/// three renderers tell "redacted, no digest" from "redacted, digest ..." by
/// this field, and an empty string would render as `<redacted #>`.
#[test]
fn a_tag_four_delta_from_an_unkeyed_recorder_carries_a_null_digest() {
    let payload = line_payload(0, &[delta(b"token", 4, 0, Some(""))]);
    let p = parse_line_payload("t", &payload, 4).unwrap();
    assert_eq!(
        p.deltas[0].1,
        serde_json::json!({"k": "dbg", "v": "<redacted>", "trunc": false,
                           "redacted": {"by": "name", "digest": null}})
    );
}

/// B1: tag 4 is read ONLY on a version-4 file. A v3 spool carrying one is
/// corruption -- no runtime that writes v3 writes the tag -- and the refusal
/// is the one this reader already had, naming the range v3 knows.
#[test]
fn a_tag_four_delta_on_a_version_three_spool_is_still_refused_by_number() {
    let payload = line_payload(0, &[delta(b"token", 4, 0, Some("aabbccddeeff0011"))]);
    let err = parse_line_payload("L", &payload, 3).unwrap_err();
    assert!(err.contains("delta `token`"), "{err}");
    assert!(err.contains("tag 4"), "{err}");
    assert!(err.contains("not 0..=3"), "{err}");
}

/// ...and from v4 the range the refusal names moves with it, so a reader
/// meeting tag 5 is told what this version's grammar actually allows.
#[test]
fn an_unknown_tag_on_a_version_four_spool_is_refused_against_the_wider_range() {
    let err = parse_line_payload("L", &line_payload(0, &[delta(b"x", 5, 0, None)]), 4).unwrap_err();
    assert!(err.contains("delta `x`"), "{err}");
    assert!(err.contains("tag 5"), "{err}");
    assert!(err.contains("not 0..=4"), "{err}");
}

/// The other four tags are unmoved by the version: a v4 spool's ordinary
/// delta, unread value and unbound name read exactly as a v3 one's.
#[test]
fn the_older_tags_read_the_same_on_a_version_four_spool() {
    let payload = line_payload(
        0,
        &[
            delta(b"x", 1, 0, Some("5")),
            delta(b"buf", 2, 0, None),
            delta(b"gone", 3, 0, None),
        ],
    );
    let p = parse_line_payload("t", &payload, 4).unwrap();
    assert_eq!(
        p.deltas[0].1,
        serde_json::json!({"k": "dbg", "v": "5", "trunc": false})
    );
    assert_eq!(p.deltas[1].1, serde_json::json!({"k": "unread"}));
    assert_eq!(p.unbound, ["gone"]);
}

/// The mirrored constant, as a NUMBER: the converter reads the wire, and
/// asserting it against the writer's own constant would pin nothing.
#[test]
fn the_line_kind_is_the_number_the_wire_format_names() {
    assert_eq!(KIND_LINE, 6);
}
