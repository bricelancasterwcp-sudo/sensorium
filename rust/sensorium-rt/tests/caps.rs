//! Per-site call cap: three stored calls, three counted elisions, one sidecar.

mod common;

use common::{Json, Spec, TempDir, KIND_CALL};

#[test]
fn max_calls_keeps_three_and_writes_an_elision_sidecar() {
    let dir = TempDir::reserved("cap-loop");
    let run = Spec::new("cap-loop")
        .spool(dir.path())
        .env("SENSORIUM_MAX_CALLS", "3")
        .env("SENSORIUM_MAX_EVENTS", "0")
        .env("SENSORIUM_MAX_BYTES", "0")
        .run();
    assert_eq!(
        run.says_u64("formatted"),
        3,
        "the args closure runs only for a kept call"
    );
    let calls = dir.spool(1).of_kind(KIND_CALL);
    assert_eq!(calls.len(), 3);
    assert!(calls
        .iter()
        .all(|c| c.site_index() == 70 && !c.payload.is_empty()));
    let side_path = dir.path().join(format!("{}.elision.json", run.pid));
    let side = Json::parse(&std::fs::read_to_string(&side_path).expect("sidecar"));
    assert_eq!(side.get("calls_elided").u64(), 3);
    assert_eq!(side.get("max_calls").u64(), 3);
    assert_eq!(side.get("max_events").u64(), 0);
    assert_eq!(side.get("max_bytes").u64(), 0);
    assert_eq!(side.get("hit").arr().len(), 1);
    assert_eq!(side.get("hit").arr()[0].str(), "max_calls");
    assert!(side.opt("failures_kept").is_none());
    let sites = side.get("sites").arr();
    assert_eq!(sites.len(), 1);
    assert_eq!(sites[0].get("unit").u64(), 0);
    assert_eq!(sites[0].get("site").u64(), 70);
    assert_eq!(sites[0].get("elided").u64(), 3);
    assert_eq!(sites[0].get("kept").u64(), 3);
    assert!(side.get("events_recorded").u64() >= 6);
    let names: Vec<String> = dir
        .walk()
        .iter()
        .map(|p| p.file_name().unwrap().to_string_lossy().into_owned())
        .collect();
    assert!(names.iter().all(|n| !n.ends_with(".tmp")), "{names:?}");
}
