//! Unit registration and the 8-bit ceiling (`rust/HONESTY.md` §8, item 13).

mod common;

use common::{Spec, TempDir, KIND_CALL};

#[test]
fn two_units_get_ids_zero_and_one_and_the_proc_header_maps_both() {
    let dir = TempDir::reserved("units-two");
    let run = Spec::new("two-units").spool(dir.path()).run();

    let s = dir.spool(1);
    let calls = s.of_kind(KIND_CALL);
    assert_eq!(calls.len(), 2);
    assert_eq!((calls[0].unit_id(), calls[0].site_index()), (0, 80));
    assert_eq!((calls[1].unit_id(), calls[1].site_index()), (1, 81));
    assert_eq!(
        calls[1].site,
        (1u32 << 24) | 81,
        "the unit id lives in bits 31..24 of the site word"
    );

    let units = dir.proc_header(run.pid);
    let units = units.get("units");
    assert_eq!(units.obj().len(), 2);
    assert_eq!(units.get("0").str(), "scenario-unit-a");
    assert_eq!(units.get("1").str(), "scenario-unit-b");
}

#[test]
fn the_two_hundred_and_fifty_sixth_unit_makes_the_runtime_refuse() {
    let dir = TempDir::reserved("units-ceiling");
    let run = Spec::new("unit-ceiling").spool(dir.path()).run();

    let s = dir.spool(1);
    let calls = s.of_kind(KIND_CALL);
    assert_eq!(
        calls.len(),
        255,
        "ids run 0..=254, so 255 units record and everything after is inert"
    );
    assert_eq!((calls[0].unit_id(), calls[0].site_index()), (0, 300));
    assert_eq!((calls[254].unit_id(), calls[254].site_index()), (254, 254));
    for refused_site in [255u32, 256, 257] {
        assert!(
            calls.iter().all(|c| c.site_index() != refused_site),
            "site {refused_site} was entered after the refusal and must not be on the wire"
        );
    }

    let header = dir.proc_header(run.pid);
    assert_eq!(header.get("units").obj().len(), 255);
    assert_eq!(header.get("units").get("0").str(), "scenario-unit-a");
    assert_eq!(header.get("units").get("254").str(), "the-255th-unit");
    assert!(
        header.get("units").opt("255").is_none(),
        "id 255 is never assigned: it would alias with the site index mask"
    );
    assert_eq!(
        header.get("refused").get("at").str(),
        "the-256th-unit",
        "the refusal is in the trace, not only on stderr"
    );

    let lines: Vec<&str> = run.stderr.lines().collect();
    assert_eq!(lines.len(), 1, "one line, once: {lines:?}");
    assert!(
        lines[0].contains("the-256th-unit"),
        "the line names the unit it refused at: {:?}",
        lines[0]
    );
    assert!(lines[0].starts_with("sensorium-rt:"));
}

#[test]
fn a_frame_opened_before_the_refusal_still_closes() {
    let dir = TempDir::reserved("units-ceiling-pairs");
    Spec::new("unit-ceiling").spool(dir.path()).run();
    let s = dir.spool(1);
    assert_eq!(
        s.of_kind(KIND_CALL).len(),
        s.of_kind(common::KIND_RETURN).len(),
        "refusal gates enter, never the closing of a frame that is already open"
    );
    // Site 300's frame was opened first and is still open when the 256th unit is
    // refused. Its RETURN is the last thing before THREAD_END.
    let tail: Vec<(u8, u32)> = s.records[s.records.len() - 2..]
        .iter()
        .map(|r| (r.kind, r.site_index()))
        .collect();
    assert_eq!(
        tail,
        vec![(common::KIND_RETURN, 300), (common::KIND_THREAD_END, 0)],
        "the frame held open across the refusal still closed"
    );
}
