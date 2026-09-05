//! Err flow through the REAL binary: what wire v3's two record kinds and its
//! typed `err` RETURN BECOME -- events, payloads, refusals and meta.
//!
//! What a SEQUENCE of them becomes -- §2a's chain identity, end to end -- is
//! `convert_errflow_chains.rs`. The two were one file until it passed 800
//! lines; the fixture they share is `tests/common/spooldir.rs`.

mod common;

use common::spooldir::{
    events, kinds, meta, two_fns_and_a_try, Fixture, HOW_ARM_AMBIGUOUS, HOW_SINK_OK, HOW_TRY,
    KIND_HANDLED, KIND_RAISE,
};
use common::wire::{self, closure_site, err_site, marked_site, site};

// ---------------------------------------------------------------------------
// The events a `?` chain becomes
// ---------------------------------------------------------------------------

#[test]
fn a_try_chain_is_written_as_an_origin_raise_and_a_hop() {
    let f = Fixture::new("errflow-try-chain");
    f.manifest(&two_fns_and_a_try());
    wire::write_proc_header_caps(
        &f.spool_dir,
        601,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(601, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .err_flow(
            3,
            1300,
            0,
            2,
            KIND_RAISE,
            HOW_TRY,
            Some("demo::E"),
            Some("E1"),
        )
        .ret_none(4, 1400, 0, 0)
        .thread_end(5, 1500)
        .write(&f.spool_dir);
    let conn = f.converted();

    assert_eq!(
        kinds(&conn),
        ["CALL", "CALL", "RAISE", "RETURN", "RAISE", "RETURN"],
        "the origin RAISE goes IN FRONT of the RETURN that carried the Err out"
    );
    let rows = events(&conn);
    let (_, origin_line, origin) = &rows[2];
    assert_eq!(origin["how"], serde_json::json!("exit"));
    assert_eq!(origin["exc"]["kind"], serde_json::json!("err"));
    assert_eq!(origin["exc"]["type"], serde_json::json!("demo::E"));
    assert_eq!(
        origin["exc"]["msg"],
        serde_json::json!("E1"),
        "the error's own Debug, not the Result's"
    );
    assert_eq!(origin["exc"]["serial"], serde_json::json!(1_u64 << 32));
    assert_eq!(
        origin["exc"]["loc"],
        serde_json::json!("crates/demo/src/lib.rs:10")
    );
    assert_eq!(*origin_line, Some(10), "the frame the Err left");
    assert_eq!(origin["chain"]["hop"], serde_json::json!(1));
    assert_eq!(origin["chain"]["origin"], serde_json::json!("workspace"));
    assert_eq!(origin["chain"]["translated"], serde_json::json!(false));

    let (_, try_line, hop) = &rows[4];
    assert_eq!(hop["how"], serde_json::json!("try"));
    assert_eq!(hop["chain"]["hop"], serde_json::json!(2));
    assert_eq!(
        hop["exc"]["serial"], origin["exc"]["serial"],
        "one chain, two events"
    );
    assert_eq!(*try_line, Some(5), "the `?`'s own line, from the manifest");
    assert_eq!(
        hop["exc"]["loc"],
        serde_json::json!("crates/demo/src/lib.rs:5")
    );
    assert_eq!(
        hop["chain"]["terminal"],
        serde_json::json!("propagated"),
        "still open when the thread ended, on a frame that is neither test nor main"
    );
}

/// The two err-flow events belong to the frame they were recorded in, not to
/// the site's own qualname: `code_id` is the top frame's, which is what makes
/// `frame` and `tree` able to place them.
#[test]
fn an_err_flow_event_is_attached_to_the_frame_it_fired_in() {
    let f = Fixture::new("errflow-frame-attachment");
    f.manifest(&two_fns_and_a_try());
    wire::write_proc_header_caps(
        &f.spool_dir,
        602,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(602, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .err_flow(
            1,
            1100,
            0,
            2,
            KIND_RAISE,
            HOW_TRY,
            Some("demo::E"),
            Some("E1"),
        )
        .ret_none(2, 1200, 0, 0)
        .thread_end(3, 1300)
        .write(&f.spool_dir);
    let conn = f.converted();

    let (frame_id, code_id, qualname): (i64, i64, String) = conn
        .query_row(
            "SELECT e.frame_id, e.code_id, c.qualname FROM events e JOIN code_objects c \
             ON c.id = e.code_id WHERE e.kind = 'RAISE'",
            [],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .unwrap();
    let (call_frame, call_code): (i64, i64) = conn
        .query_row("SELECT f.id, f.code_id FROM frames f", [], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })
        .unwrap();
    assert_eq!(frame_id, call_frame);
    assert_eq!(code_id, call_code);
    assert_eq!(qualname, "outer");
}

/// A sink absorbing the chain, then an `ok` close: the shape a SWALLOWED
/// verdict is made of. The converter records the FACT and no verdict.
#[test]
fn a_sink_then_an_ok_close_is_recorded_as_a_swallowed_candidate() {
    let f = Fixture::new("errflow-sink-swallow");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "inner", 10, "value"),
        err_site(2, "outer", 6, "sink", "sink_ok"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        603,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(603, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .err_flow(
            3,
            1300,
            0,
            2,
            KIND_HANDLED,
            HOW_SINK_OK,
            Some("demo::E"),
            Some("E1"),
        )
        .ret_ok_dbg(4, 1400, 0, 0, "()", false)
        .thread_end(5, 1500)
        .write(&f.spool_dir);
    let conn = f.converted();

    assert_eq!(
        kinds(&conn),
        ["CALL", "CALL", "RAISE", "RETURN", "HANDLED", "RETURN"]
    );
    let rows = events(&conn);
    let handled = &rows[4].2;
    assert_eq!(handled["how"], serde_json::json!("sink_ok"));
    assert_eq!(
        handled["chain"]["terminal"],
        serde_json::json!("swallowed_candidate")
    );
    assert_eq!(handled["exc"]["serial"], rows[2].2["exc"]["serial"]);
    assert_eq!(
        meta(&conn, "err_flow_records"),
        serde_json::json!({"raise": 0, "handled": 1}),
        "the synthesised origin RAISE is an EVENT, never a record"
    );
}

/// An `Err(..) =>` arm binds nothing, so the record carries no type and no
/// message: the type comes from the chain it continues (design R4).
#[test]
fn an_unbound_arm_takes_its_type_from_the_chain_and_declares_its_message_unread() {
    let f = Fixture::new("errflow-unbound-arm");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "inner", 10, "value"),
        err_site(2, "outer", 8, "arm", "arm_ambiguous"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        604,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(604, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .err_flow(3, 1300, 0, 2, KIND_HANDLED, HOW_ARM_AMBIGUOUS, None, None)
        .ret_ok_dbg(4, 1400, 0, 0, "()", false)
        .thread_end(5, 1500)
        .write(&f.spool_dir);
    let rows = events(&f.converted());
    let arm = &rows[4].2;
    assert_eq!(arm["exc"]["type"], serde_json::json!("demo::E"));
    assert_eq!(arm["exc"]["unread"], serde_json::json!(["msg"]));
    assert_eq!(
        arm["chain"]["terminal"],
        serde_json::json!("ambiguous_escaped")
    );
}

// ---------------------------------------------------------------------------
// What a v2 spool still does
// ---------------------------------------------------------------------------

/// Design R1: "a v2 spool still converts". Its `err` RETURN carries no type
/// block, so it is no chain's origin and grows no RAISE -- the event stream of
/// a rung-2 recording is what it always was.
#[test]
fn a_v2_err_return_converts_exactly_as_it_did_with_no_origin_raise() {
    let f = Fixture::new("errflow-v2-unchanged");
    f.manifest(&[site(0, "outer", 3, "value")]);
    wire::write_proc_header(
        &f.spool_dir,
        605,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(605, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_err_dbg(1, 1100, 0, 0, "Err(E1)")
        .thread_end(2, 1200)
        .write(&f.spool_dir);
    let conn = f.converted();

    assert_eq!(kinds(&conn), ["CALL", "RETURN"]);
    let rows = events(&conn);
    assert_eq!(rows[1].2["outcome"], serde_json::json!("err"));
    assert_eq!(
        rows[1].2["value"],
        serde_json::json!({"k": "dbg", "v": "Err(E1)", "trunc": false})
    );
    assert_eq!(
        meta(&conn, "capabilities")["err_flow"],
        serde_json::json!(false),
        "a proc header that declares nothing must not gain a capability here"
    );
}

// ---------------------------------------------------------------------------
// Refusals (design R1b)
// ---------------------------------------------------------------------------

#[test]
fn a_call_naming_an_err_flow_site_is_refused_by_name() {
    let f = Fixture::new("errflow-call-on-try-site");
    f.manifest(&[err_site(0, "outer", 5, "try", "try")]);
    wire::write_proc_header(
        &f.spool_dir,
        606,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(606, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .write(&f.spool_dir);
    let err = f.refusal();
    assert!(err.contains("crates/demo/src/lib.rs:5"), "{err}");
    assert!(err.contains("`try` site"), "{err}");
    assert!(err.contains("not a frame"), "{err}");
}

#[test]
fn an_err_flow_record_naming_a_frame_site_is_refused_by_name() {
    let f = Fixture::new("errflow-raise-on-fn-site");
    f.manifest(&[site(0, "outer", 3, "value")]);
    wire::write_proc_header(
        &f.spool_dir,
        607,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(607, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .err_flow(1, 1100, 0, 0, KIND_RAISE, HOW_TRY, Some("E"), Some("x"))
        .write(&f.spool_dir);
    let err = f.refusal();
    assert!(err.contains("crates/demo/src/lib.rs:3"), "{err}");
    assert!(err.contains("`fn` frame site"), "{err}");
}

/// `exit` (8) is the converter's own `how` and no runtime may write it; nor may
/// 0, nor anything above.
#[test]
fn an_err_flow_record_carrying_the_converters_own_how_is_refused() {
    let f = Fixture::new("errflow-how-eight");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        err_site(1, "outer", 5, "try", "try"),
    ]);
    wire::write_proc_header(
        &f.spool_dir,
        608,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(608, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .err_flow(1, 1100, 0, 1, KIND_RAISE, 8, Some("E"), Some("x"))
        .write(&f.spool_dir);
    let err = f.refusal();
    assert!(err.contains("how byte 8"), "{err}");
    assert!(err.contains("1..=7"), "{err}");
}

/// The transformer wrote the manifest row and the runtime wrote the byte from
/// the same splice, so the two disagreeing is corruption.
#[test]
fn an_err_flow_record_whose_how_the_manifest_contradicts_is_refused() {
    let f = Fixture::new("errflow-how-disagrees");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        err_site(1, "outer", 6, "sink", "sink_unwrap_or"),
    ]);
    wire::write_proc_header(
        &f.spool_dir,
        609,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(609, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .err_flow(
            1,
            1100,
            0,
            1,
            KIND_HANDLED,
            HOW_SINK_OK,
            Some("E"),
            Some("x"),
        )
        .write(&f.spool_dir);
    let err = f.refusal();
    assert!(err.contains("how `sink_ok`"), "{err}");
    assert!(err.contains("writes `sink_unwrap_or`"), "{err}");
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

#[test]
fn the_meta_carries_the_err_flow_counters_the_marks_and_the_partial_list() {
    let f = Fixture::new("errflow-meta");
    f.manifest(&[
        marked_site(0, "tests::t", 3, "value", true, false),
        closure_site(1, "tests::t::{{closure}}#0", 7),
        err_site(2, "tests::t", 5, "sink", "sink_ok"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        610,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(610, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_ok_dbg(2, 1200, 0, 1, "Ok(())", false)
        // A sink whose frame has already closed: no event, counted instead.
        .err_flow(
            3,
            1300,
            0,
            2,
            KIND_HANDLED,
            HOW_SINK_OK,
            Some("demo::E"),
            Some("E1"),
        )
        .ret_ok_dbg(4, 1400, 0, 0, "Ok(())", false)
        .err_flow(
            5,
            1500,
            0,
            2,
            KIND_HANDLED,
            HOW_SINK_OK,
            Some("demo::E"),
            Some("E2"),
        )
        .thread_end(6, 1600)
        .write(&f.spool_dir);
    let conn = f.converted();

    assert_eq!(
        meta(&conn, "err_flow_records"),
        serde_json::json!({"raise": 0, "handled": 2})
    );
    assert_eq!(
        meta(&conn, "err_flow_outside_frames"),
        serde_json::json!(1),
        "the record after the last frame closed has nothing to be reported against"
    );
    assert_eq!(meta(&conn, "closure_frames"), serde_json::json!(1));
    assert_eq!(
        meta(&conn, "capabilities")["err_flow"],
        serde_json::json!(true)
    );

    let partial = meta(&conn, "partial");
    assert_eq!(partial[0]["reason"], serde_json::json!("macro-arg"));
    assert_eq!(partial[0]["kind"], serde_json::json!("try"));

    let sites = meta(&conn, "sites");
    assert_eq!(sites.as_array().unwrap().len(), 3);
    assert_eq!(sites[0]["kind"], serde_json::json!("fn"));
    assert_eq!(sites[0]["test"], serde_json::json!(true));
    assert_eq!(sites[0]["main"], serde_json::json!(false));
    assert_eq!(sites[1]["kind"], serde_json::json!("closure"));
    assert_eq!(sites[1]["line"], serde_json::json!(7));
    assert_eq!(sites[2]["how"], serde_json::json!("sink_ok"));
    // The first HANDLED fired while the outer frame was still open and is an
    // event; the second, after every frame had closed, is the counted one.
    assert_eq!(
        kinds(&conn),
        ["CALL", "CALL", "RETURN", "HANDLED", "RETURN"]
    );
    // Nothing raised that `Err` inside this recording, so its chain was born
    // outside instrumented code (design R8's `dependency_swallow`).
    assert_eq!(
        events(&conn)[3].2["chain"]["origin"],
        serde_json::json!("outside")
    );
}

// ---------------------------------------------------------------------------
// Fingerprints (design R12)
// ---------------------------------------------------------------------------

/// RAISE and HANDLED are causal kinds (TRACE-FORMAT §5), so a run whose `?`
/// fired and one whose did not are two different runs -- which is the whole
/// point of a fingerprint.
#[test]
fn a_run_whose_try_fired_has_a_different_fingerprint_from_one_whose_did_not() {
    fn fingerprint(name: &str, pid: u32, with_try: bool) -> String {
        let f = Fixture::new(name);
        f.manifest(&two_fns_and_a_try());
        wire::write_proc_header_caps(
            &f.spool_dir,
            pid,
            1,
            "/w/target/deps/demo",
            &[(0, "meta1")],
            None,
            Some(true),
        );
        let mut b = wire::SpoolBuilder::new(pid, 1, "main")
            .version(3)
            .call(0, 1000, 0, 0);
        if with_try {
            b = b.err_flow(
                1,
                1100,
                0,
                2,
                KIND_RAISE,
                HOW_TRY,
                Some("demo::E"),
                Some("E1"),
            );
        }
        b.ret_none(2, 1200, 0, 0)
            .thread_end(3, 1300)
            .write(&f.spool_dir);
        let conn = f.converted();
        conn.query_row("SELECT hash FROM fingerprints", [], |r| r.get(0))
            .unwrap()
    }

    let with = fingerprint("errflow-fp-with", 612, true);
    let without = fingerprint("errflow-fp-without", 613, false);
    assert_ne!(
        with, without,
        "a RAISE must enter the causal stream the fingerprint is taken over"
    );
}

// ---------------------------------------------------------------------------
// Panics keep their own namespace (design R7)
// ---------------------------------------------------------------------------

#[test]
fn a_panic_raise_is_kind_panic_and_keeps_its_serial_numbering() {
    let f = Fixture::new("errflow-panic-kind");
    f.manifest(&[site(0, "outer", 3, "value")]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        614,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(614, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .panic_record(1, 1100, "crates/demo/src/lib.rs:4:9", "boom")
        .ret_panic(2, 1200, 0, 0)
        .thread_end(3, 1300)
        .write(&f.spool_dir);
    let conn = f.converted();
    let rows = events(&conn);
    assert_eq!(rows[1].2["exc"]["kind"], serde_json::json!("panic"));
    assert_eq!(
        rows[1].2["exc"]["serial"],
        serde_json::json!(1),
        "panic serials are still counted from 1, disjoint from the chain namespace"
    );
    let unwind: String = conn
        .query_row("SELECT unwind_exc FROM frames", [], |r| r.get(0))
        .unwrap();
    let unwind: serde_json::Value = serde_json::from_str(&unwind).unwrap();
    assert_eq!(unwind["kind"], serde_json::json!("panic"));
}
