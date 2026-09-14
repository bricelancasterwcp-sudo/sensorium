//! Rule v1 over the VALUES and MESSAGES a conversion writes, end to end
//! through the REAL binary.
//!
//! The rule itself is unit-tested in `src/convert/redaction.rs` and the
//! rendering the fixtures pin is `tests/fixtures/rust-spools/redacted-values`.
//! What is here is the pair of facts neither of those can reach: that ONE
//! withheld text written into TWO rows carries one digest and counts once
//! (R16), and that the value the converter SYNTHESISES for a unit return is
//! never withheld at all (R17). Both are properties of the walk, so both need
//! a real conversion of a real spool.
//!
//! The spool bytes are `common::wire`'s, written from the format block and
//! never by running the runtime, like every other `convert_*` suite.

mod common;

use common::spooldir::{events, kinds, meta, Fixture};
use common::wire::{self, err_site, site};

/// The error a firing function returns, as the exit probe rendered the whole
/// `Result` -- and as `err_debug_text` reads the `Err`'s own text out of it.
const RET_TEXT: &str = r#"Err(Vault("hunter2"))"#;
const INNER_TEXT: &str = r#"Vault("hunter2")"#;

#[test]
fn an_err_return_taken_by_name_is_withheld_on_its_origin_raise_under_one_digest() {
    // R16. `demo::get_token` fires the name rule, so its returned value is
    // withheld WHOLE -- and in Rust an `Err` return IS the return value, so
    // the origin RAISE the converter synthesises in front of that RETURN
    // repeats the very text the rule just took. Content-ruling that row would
    // publish, one event earlier, the value the row after it withholds.
    //
    // One text, two rows: one digest, and ONE count -- the panic path's rule
    // (`convert_panics.rs`) at the other site that writes a text twice.
    let f = Fixture::new("redaction-err-return-name");
    let material = f.with_redaction_key();
    f.manifest(&[
        site(0, "demo::run", 3, "value"),
        site(1, "demo::get_token", 10, "value"),
        err_site(2, "demo::run", 5, "try", "try"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        701,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(701, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some(RET_TEXT))
        .ret_none(3, 1300, 0, 0)
        .thread_end(4, 1400)
        .write(&f.spool_dir);
    let conn = f.converted();

    assert_eq!(
        kinds(&conn),
        ["CALL", "CALL", "RAISE", "RETURN", "RETURN"],
        "the origin RAISE goes in front of the RETURN that carried the Err out"
    );
    let rows = events(&conn);
    let (_, _, origin) = &rows[2];
    let (_, _, ret) = &rows[3];

    // The RETURN: taken whole by name, with the store's digest of the text.
    let expected = sensorium_rt::redact::Key::from_bytes(&material)
        .digest(RET_TEXT)
        .expect("a 32-byte key takes digests");
    assert_eq!(ret["value"]["v"], serde_json::json!("<redacted>"), "{ret}");
    assert_eq!(
        ret["value"]["redacted"],
        serde_json::json!({"by": "name", "digest": expected}),
        "{ret}"
    );

    // The origin RAISE: the SAME withholding, not a content scan that would
    // have found nothing in `Vault("hunter2")` and left it standing.
    assert_eq!(
        origin["exc"]["msg"],
        serde_json::json!("<redacted>"),
        "{origin}"
    );
    assert_eq!(
        origin["exc"]["redacted"], ret["value"]["redacted"],
        "one value, two rows, one digest"
    );

    // One withheld text, counted once.
    let redaction = meta(&conn, "redaction");
    assert_eq!(redaction["values"], 1, "{redaction}");

    // And neither spelling of the secret reached the trace.
    for row in [origin, ret] {
        let text = row.to_string();
        assert!(!text.contains("hunter2"), "{text}");
        assert!(!text.contains(INNER_TEXT), "{text}");
    }
}

#[test]
fn the_same_err_return_under_an_ordinary_name_keeps_its_content_ruled_message() {
    // The discriminating half: byte for byte the fixture above with the
    // callee RENAMED, so what the first test proves is the NAME rule and not
    // the shape of the records around it. `demo::load` fires on nothing, so
    // the value stands and the origin RAISE's message takes the content rule
    // -- which finds no §2.2 shape in `Vault("hunter2")` and leaves it alone.
    let f = Fixture::new("redaction-err-return-plain");
    f.with_redaction_key();
    f.manifest(&[
        site(0, "demo::run", 3, "value"),
        site(1, "demo::load", 10, "value"),
        err_site(2, "demo::run", 5, "try", "try"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        702,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(702, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some(RET_TEXT))
        .ret_none(3, 1300, 0, 0)
        .thread_end(4, 1400)
        .write(&f.spool_dir);
    let conn = f.converted();

    let rows = events(&conn);
    let (_, _, origin) = &rows[2];
    let (_, _, ret) = &rows[3];
    assert_eq!(ret["value"]["v"], serde_json::json!(RET_TEXT), "{ret}");
    assert!(ret["value"].get("redacted").is_none(), "{ret}");
    assert_eq!(
        origin["exc"]["msg"],
        serde_json::json!(INNER_TEXT),
        "{origin}"
    );
    assert!(origin["exc"].get("redacted").is_none(), "{origin}");
    assert_eq!(meta(&conn, "redaction")["values"], 0);
}

#[test]
fn a_unit_return_under_a_firing_name_keeps_its_value_and_is_not_counted() {
    // R17. The wire carries NO value for a frame the manifest says returns
    // `()`; the `{"k":"dbg","v":"()"}` on the row is the converter's own
    // reading of that silence. Withholding it would put `<redacted>` where a
    // reader can see there was nothing to take, publish a digest of the
    // constant `"()"` that positively identifies what it stands for, and
    // count a value nobody lost.
    //
    // `demo::refresh_token` fires (`REFRESH` + `TOKEN`), which is the whole
    // point: this is the carve-out and not an absence of the rule.
    let f = Fixture::new("redaction-unit-return");
    f.with_redaction_key();
    f.manifest(&[site(0, "demo::refresh_token", 3, "unit")]);
    wire::write_proc_header(
        &f.spool_dir,
        703,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(703, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 1100, 0, 0)
        .thread_end(2, 1200)
        .write(&f.spool_dir);
    let conn = f.converted();

    let rows = events(&conn);
    let (_, _, ret) = &rows[1];
    assert_eq!(ret["outcome"], serde_json::json!("ok"));
    assert_eq!(
        ret["value"],
        serde_json::json!({"k": "dbg", "v": "()"}),
        "no marker, no mark, and no `trunc` key this shape never carried"
    );
    assert_eq!(
        meta(&conn, "redaction")["values"],
        0,
        "a value that hides nothing is not one of `values`"
    );
}

#[test]
fn a_value_under_the_same_firing_name_is_still_taken() {
    // The discriminating half of R17: the same qualname, a real value, and
    // the rule fires. Without this the carve-out above would pass just as
    // well if the name rule had been deleted.
    let f = Fixture::new("redaction-unit-return-control");
    f.with_redaction_key();
    f.manifest(&[site(0, "demo::refresh_token", 3, "value")]);
    wire::write_proc_header(
        &f.spool_dir,
        704,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(704, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_ok_dbg(1, 1100, 0, 0, "Session { id: 1 }", false)
        .thread_end(2, 1200)
        .write(&f.spool_dir);
    let conn = f.converted();
    let rows = events(&conn);
    let (_, _, ret) = &rows[1];
    assert_eq!(ret["value"]["v"], serde_json::json!("<redacted>"), "{ret}");
    assert_eq!(meta(&conn, "redaction")["values"], 1);
}
