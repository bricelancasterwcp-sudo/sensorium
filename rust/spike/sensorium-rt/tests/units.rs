//! THROWAWAY SPIKE CODE. Unit registration, its 8-bit ceiling, and reentrancy.

mod common;

use common::{TempDir, KIND_CALL};

/// A unit takes a process-unique id on its first `enter`, and keeps it.
#[test]
fn a_unit_registers_once_and_keeps_its_id() {
    let (dir, _run) = common::run_recording("two-threads");
    let ids: Vec<u8> = dir
        .spools()
        .iter()
        .flat_map(|s| s.kinds(KIND_CALL))
        .map(|r| r.unit_id())
        .collect();
    assert!(!ids.is_empty());
    assert!(
        ids.iter().all(|&id| id == 0),
        "one unit entered from two threads must register exactly once"
    );
}

/// The 256th distinct unit makes the runtime refuse to record: every later
/// `enter` is inert and one stderr line says why.
#[test]
fn the_256th_unit_makes_the_runtime_refuse_to_record() {
    let dir = TempDir::reserved();
    let run = common::run("unit-limit", &["300"], Some(dir.path()), None);

    let spool = dir.spool(1);
    let calls = spool.kinds(KIND_CALL);
    assert_eq!(
        calls.len(),
        255,
        "255 units fit in the 8-bit unit id; the 256th must be refused"
    );
    let ids: Vec<u8> = calls.iter().map(|r| r.unit_id()).collect();
    assert_eq!(ids[0], 0);
    assert_eq!(ids[254], 254, "ids run 0..=254 in registration order");
    assert!(
        calls.iter().enumerate().all(|(i, r)| r.site_index() == i as u32),
        "each unit entered at its own site index"
    );

    let lines: Vec<&str> = run.stderr.lines().filter(|l| !l.is_empty()).collect();
    assert_eq!(
        lines.len(),
        1,
        "one line, not one per refused unit; got {lines:?}"
    );
    assert!(
        lines[0].contains("refusing to record") && lines[0].contains("255"),
        "the line must say why: {}",
        lines[0]
    );

    let header = dir.proc_header(run.pid);
    assert!(
        header.contains("\"254\":"),
        "the proc header carries every registered unit"
    );
    assert!(
        !header.contains("\"255\":"),
        "and no refused one: {header}"
    );
}

/// A run that stays under the ceiling records every unit.
#[test]
fn units_below_the_ceiling_all_record() {
    let dir = TempDir::reserved();
    common::run("unit-limit", &["255"], Some(dir.path()), None);
    assert_eq!(
        dir.spool(1).kinds(KIND_CALL).len(),
        255,
        "255 units is exactly the ceiling and must record in full"
    );
}

/// `enter` reached from inside the runtime is inert.
#[test]
fn enter_is_inert_while_the_runtime_is_running() {
    let (dir, _run) = common::run_recording("reentrant");
    let sites: Vec<u32> = dir
        .spool(1)
        .kinds(KIND_CALL)
        .iter()
        .map(|r| r.site_index())
        .collect();
    assert_eq!(
        sites,
        vec![901],
        "site 900 was entered from inside the runtime and must be inert"
    );
}
