//! The wire reader's tests, over HAND-BUILT bytes: every fixture here is
//! written from the format block at the top of the module it tests, never by
//! running the runtime, so a bug the writer and the reader share cannot pass
//! them.

use super::*;
fn header(name: &str, records_dropped: u64, truncated: u64) -> Vec<u8> {
    header_v(name, records_dropped, truncated, 2)
}

fn header_v(name: &str, records_dropped: u64, truncated: u64, version: u8) -> Vec<u8> {
    let mut b = vec![0u8; HEADER_FIXED];
    b[0..4].copy_from_slice(b"SNSR");
    b[4] = version;
    b[5] = 0;
    b[6..8].copy_from_slice(&(name.len() as u16).to_le_bytes());
    b[8..12].copy_from_slice(&7u32.to_le_bytes());
    b[12..20].copy_from_slice(&records_dropped.to_le_bytes());
    b[20..28].copy_from_slice(&truncated.to_le_bytes());
    b.extend_from_slice(name.as_bytes());
    b
}

fn record(seq: u64, ts_ns: u64, site: u32, kind: u8, outcome: u8, payload: &[u8]) -> Vec<u8> {
    let mut b = Vec::new();
    b.extend_from_slice(&seq.to_le_bytes());
    b.extend_from_slice(&ts_ns.to_le_bytes());
    b.extend_from_slice(&site.to_le_bytes());
    b.push(kind);
    b.push(outcome);
    b.extend_from_slice(&(payload.len() as u16).to_le_bytes());
    b.extend_from_slice(payload);
    b
}

#[test]
fn a_header_with_no_records_parses_to_an_empty_stream() {
    let bytes = header("main", 0, 0);
    let s = parse_spool_bytes("t", &bytes).unwrap();
    assert_eq!(s.serial, 7);
    assert_eq!(s.name, "main");
    assert!(s.records.is_empty());
}

#[test]
fn a_torn_tail_kind_zero_stops_the_reader_without_erroring() {
    let mut bytes = header("t", 0, 0);
    bytes.extend(record(0, 100, 1, KIND_CALL, 0, &[]));
    bytes.extend(vec![0u8; RECORD_FIXED]); // kind 0: the unwritten tail
    let s = parse_spool_bytes("t", &bytes).unwrap();
    assert_eq!(s.records.len(), 1);
}

#[test]
fn seq_going_backwards_is_a_named_error() {
    let mut bytes = header("t", 0, 0);
    bytes.extend(record(5, 1, 0, KIND_CALL, 0, &[]));
    bytes.extend(record(3, 2, 0, KIND_CALL, 0, &[]));
    let err = parse_spool_bytes("t.spool", &bytes).unwrap_err();
    assert!(err.contains("t.spool"), "{err}");
    assert!(err.contains("backwards"), "{err}");
}

#[test]
fn a_bad_magic_is_refused() {
    let bytes = vec![0u8; HEADER_FIXED];
    let err = parse_spool_bytes("x", &bytes).unwrap_err();
    assert!(err.contains("magic"), "{err}");
}

#[test]
fn a_return_payload_decodes_tag_truncated_and_text() {
    let p = parse_return_payload("t", &[1, 1, b'O', b'k'], false).unwrap();
    assert_eq!(p.tag, TAG_DEBUG);
    assert!(p.truncated);
    assert_eq!(p.text, "Ok");
}

#[test]
fn a_panic_payload_splits_loc_and_msg_on_loc_len() {
    let mut bytes = 3u16.to_le_bytes().to_vec();
    bytes.extend_from_slice(b"a.rs");
    bytes.extend_from_slice(b"boom");
    // loc_len = 3 but "a.rs" is 4 bytes: loc = "a.r", msg = "sboom".
    let p = parse_panic_payload("t", &bytes).unwrap();
    assert_eq!(p.loc, "a.r");
    assert_eq!(p.msg, "sboom");
}

#[test]
fn units_in_order_sorts_by_numeric_id_not_by_string() {
    let mut units = BTreeMap::new();
    units.insert("10".to_owned(), "ten".to_owned());
    units.insert("2".to_owned(), "two".to_owned());
    let header = ProcHeader {
        pid: 1,
        ppid: 0,
        exe: String::new(),
        argv: vec![],
        cwd: String::new(),
        start_ns: 0,
        start_realtime_ns: 0,
        env: BTreeMap::new(),
        env_hash: String::new(),
        units,
        refused: None,
        rt_version: String::new(),
        capabilities: BTreeMap::new(),
    };
    assert_eq!(
        header.units_in_order(),
        vec!["two".to_owned(), "ten".to_owned()]
    );
}

// -- wire v3 ----------------------------------------------------------

/// Design R1: v3 is read, v2 is still read, and the version is carried per
/// FILE because it is what decides how an `err` RETURN's payload is cut.
#[test]
fn both_wire_versions_are_read_and_the_files_own_version_is_kept() {
    for version in [2u8, 3] {
        let s = parse_spool_bytes("t", &header_v("main", 0, 0, version)).unwrap();
        assert_eq!(s.version, version);
    }
}

#[test]
fn a_version_this_converter_does_not_read_is_refused_by_number() {
    let err = parse_spool_bytes("t", &header_v("main", 0, 0, 4)).unwrap_err();
    assert!(err.contains("version 4"), "{err}");
    assert!(err.contains("versions 2 and 3"), "{err}");
}

/// The err-flow record kinds and `how` bytes, written out as NUMBERS: they
/// are wire-format values, and asserting them against the constants beside
/// them would pin nothing at all.
#[test]
fn the_err_flow_kinds_and_hows_are_the_numbers_the_wire_format_names() {
    assert_eq!(KIND_RAISE, 4);
    assert_eq!(KIND_HANDLED, 5);
    for (byte, how) in [
        (1u8, How::Try),
        (2, How::SinkOk),
        (3, How::SinkUnwrapOr),
        (4, How::SinkLetUnderscore),
        (5, How::ArmPropagate),
        (6, How::ArmHandled),
        (7, How::ArmAmbiguous),
    ] {
        assert_eq!(How::from_wire(byte), Some(how), "how byte {byte}");
    }
    assert_eq!(How::from_wire(0), None);
    assert_eq!(How::from_wire(8), None, "`exit` is the converter's own");
    assert_eq!(How::from_wire(9), None);
}

/// A `how` that lets the `Err` out writes a RAISE; every other writes a
/// HANDLED. Spelled one at a time, so a row moving between the two kinds
/// is a failing assertion rather than a widened range.
#[test]
fn only_the_propagating_hows_belong_to_a_raise() {
    assert!(How::Try.is_raise());
    assert!(How::ArmPropagate.is_raise());
    assert!(How::Exit.is_raise());
    for how in [
        How::SinkOk,
        How::SinkUnwrapOr,
        How::SinkLetUnderscore,
        How::ArmHandled,
        How::ArmAmbiguous,
    ] {
        assert!(!how.is_raise(), "{}", how.as_str());
        assert_eq!(how.wire_kind(), KIND_HANDLED);
    }
    assert_eq!(How::Try.wire_kind(), KIND_RAISE);
}

/// `arm_ambiguous` is HANDLED-class but never a SWALLOWED candidate
/// (design R2), which is the one distinction `is_sink` exists to make.
#[test]
fn an_ambiguous_arm_is_handled_class_but_not_a_sink() {
    assert!(How::SinkOk.is_sink());
    assert!(How::SinkUnwrapOr.is_sink());
    assert!(How::SinkLetUnderscore.is_sink());
    assert!(How::ArmHandled.is_sink());
    assert!(!How::ArmAmbiguous.is_sink());
    assert!(!How::Try.is_sink());
}

#[test]
fn a_how_byte_no_runtime_writes_is_refused_by_number() {
    let err = parse_how("t", KIND_RAISE, 8).unwrap_err();
    assert!(err.contains("how byte 8"), "{err}");
    assert!(err.contains("1..=7"), "{err}");
    assert!(parse_how("t", KIND_RAISE, 0).is_err());
}

#[test]
fn a_how_belonging_to_the_other_record_kind_is_refused() {
    let err = parse_how("t", KIND_RAISE, 2).unwrap_err();
    assert!(err.contains("sink_ok"), "{err}");
    assert!(err.contains("kind 5"), "{err}");
    assert!(parse_how("t", KIND_HANDLED, 1).is_err(), "try is a RAISE");
}

/// Match ergonomics bind an arm's error by reference; one leading `&` or
/// `&mut ` is the artefact, and only one (design R4).
#[test]
fn one_leading_reference_is_stripped_from_a_recorded_type() {
    assert_eq!(strip_ref("io::Error"), "io::Error");
    assert_eq!(strip_ref("&io::Error"), "io::Error");
    assert_eq!(strip_ref("&mut io::Error"), "io::Error");
    assert_eq!(strip_ref("&&io::Error"), "&io::Error", "one, not all");
    assert_eq!(strip_ref("&mut &E"), "&E");
}

fn err_payload(flags: u8, ty: &str, msg: &str) -> Vec<u8> {
    let mut p = vec![flags];
    p.extend_from_slice(&(ty.len() as u16).to_le_bytes());
    p.extend_from_slice(ty.as_bytes());
    p.extend_from_slice(msg.as_bytes());
    p
}

#[test]
fn an_err_flow_payload_decodes_its_type_and_message() {
    let p = parse_errflow_payload("t", &err_payload(0b1001, "io::Error", "Os { .. }")).unwrap();
    assert_eq!(p.type_name.as_deref(), Some("io::Error"));
    assert_eq!(p.msg.as_deref(), Some("Os { .. }"));
    assert!(!p.type_truncated);
    assert!(!p.msg_truncated);
}

/// Absent and empty are different facts, and the flags are what separate
/// them: an `Err(_) =>` arm records neither field, and a `Debug` impl that
/// rendered nothing records an empty one.
#[test]
fn an_absent_field_and_an_empty_one_are_read_apart() {
    let unbound = parse_errflow_payload("t", &err_payload(0, "", "")).unwrap();
    assert_eq!(unbound.type_name, None);
    assert_eq!(unbound.msg, None);
    let empty = parse_errflow_payload("t", &err_payload(0b1001, "", "")).unwrap();
    assert_eq!(empty.type_name.as_deref(), Some(""));
    assert_eq!(empty.msg.as_deref(), Some(""));
}

#[test]
fn the_two_truncation_bits_are_read_off_the_flags() {
    let p = parse_errflow_payload("t", &err_payload(0b1111, "T", "m")).unwrap();
    assert!(p.type_truncated);
    assert!(p.msg_truncated);
}

/// A by-ref arm and a `?` must record the same `E`, so the strip happens
/// at the parse and not at every use.
#[test]
fn an_err_flow_payloads_type_is_stripped_of_its_binding_reference() {
    let p = parse_errflow_payload("t", &err_payload(0b1000, "&io::Error", "")).unwrap();
    assert_eq!(p.type_name.as_deref(), Some("io::Error"));
}

#[test]
fn an_err_flow_payload_that_is_shorter_than_its_fixed_bytes_is_refused() {
    let err = parse_errflow_payload("t", &[0, 0]).unwrap_err();
    assert!(err.contains("3 fixed bytes"), "{err}");
}

#[test]
fn an_err_flow_payloads_type_len_past_its_end_is_refused() {
    let mut p = vec![0b1000u8];
    p.extend_from_slice(&9u16.to_le_bytes());
    p.extend_from_slice(b"ab");
    let err = parse_errflow_payload("t", &p).unwrap_err();
    assert!(err.contains("type_len 9"), "{err}");
}

/// The flags byte and the bytes after it are written by one call, so the
/// two disagreeing is corruption rather than a shape to interpret.
#[test]
fn a_payload_whose_flags_contradict_its_bytes_is_refused() {
    let ty = parse_errflow_payload("t", &err_payload(0, "E", "")).unwrap_err();
    assert!(ty.contains("declares no type"), "{ty}");
    let msg = parse_errflow_payload("t", &err_payload(0, "", "boom")).unwrap_err();
    assert!(msg.contains("declares no message"), "{msg}");
}

// -- the typed `err` RETURN -------------------------------------------

#[test]
fn an_err_returns_type_block_is_read_before_its_text() {
    let mut p = vec![1u8, 0u8, 1u8];
    p.extend_from_slice(&7u16.to_le_bytes());
    p.extend_from_slice(b"demo::E");
    p.extend_from_slice(b"Err(E1)");
    let r = parse_return_payload("t", &p, true).unwrap();
    assert_eq!(r.tag, TAG_DEBUG);
    assert_eq!(r.err_type.as_deref(), Some("demo::E"));
    assert!(!r.err_type_truncated);
    assert_eq!(r.text, "Err(E1)");
}

/// The block is written on every `err`, even with no type to name, so its
/// presence never has to be inferred from the payload's length.
#[test]
fn an_err_return_with_no_type_to_name_still_carries_the_block() {
    let p = vec![0u8, 0u8, 0u8, 0u8, 0u8];
    let r = parse_return_payload("t", &p, true).unwrap();
    assert_eq!(r.err_type, None);
    assert_eq!(r.text, "");
}

/// The same bytes read WITHOUT the block are a v2 payload, and reading one
/// as the other is exactly the mistake the version guard exists to stop.
#[test]
fn a_v2_return_payload_reads_its_text_from_byte_two() {
    let p = b"\x01\x00Err(E1)";
    let r = parse_return_payload("t", p, false).unwrap();
    assert_eq!(r.text, "Err(E1)");
    assert_eq!(r.err_type, None);
    assert!(
        parse_return_payload("t", p, true).is_err(),
        "reading a v2 payload as v3 takes the text's own bytes for a \
         type_len, which is why the version guard is at the call site"
    );
}

#[test]
fn an_err_returns_type_len_past_its_end_is_refused() {
    let mut p = vec![1u8, 0u8, 1u8];
    p.extend_from_slice(&40u16.to_le_bytes());
    p.extend_from_slice(b"E");
    let err = parse_return_payload("t", &p, true).unwrap_err();
    assert!(err.contains("type_len 40"), "{err}");
}

#[test]
fn an_err_return_shorter_than_its_type_block_is_refused() {
    let err = parse_return_payload("t", &[1, 0, 0], true).unwrap_err();
    assert!(err.contains("5 fixed bytes"), "{err}");
}

#[test]
fn an_err_returns_truncated_type_is_flagged() {
    let mut p = vec![0u8, 0u8, 0b11u8];
    p.extend_from_slice(&1u16.to_le_bytes());
    p.extend_from_slice(b"E");
    let r = parse_return_payload("t", &p, true).unwrap();
    assert_eq!(r.err_type.as_deref(), Some("E"));
    assert!(r.err_type_truncated);
}

/// A record of either err-flow kind parses out of a whole spool file, so
/// the `how` byte's place in the record header is pinned too.
#[test]
fn a_v3_spool_carries_its_err_flow_records_through_the_reader() {
    let mut bytes = header_v("main", 0, 0, 3);
    bytes.extend(record(0, 100, 1, KIND_CALL, 0, &[]));
    bytes.extend(record(
        1,
        200,
        1,
        KIND_RAISE,
        1,
        &err_payload(0b1001, "E", "x"),
    ));
    bytes.extend(record(
        2,
        300,
        1,
        KIND_HANDLED,
        2,
        &err_payload(0b1000, "E", ""),
    ));
    let s = parse_spool_bytes("t", &bytes).unwrap();
    assert_eq!(s.records.len(), 3);
    assert_eq!(s.records[1].kind, KIND_RAISE);
    assert_eq!(s.records[1].outcome, 1, "the how rides the outcome byte");
    assert_eq!(s.records[2].kind, KIND_HANDLED);
    assert_eq!(s.records[2].outcome, 2);
}
