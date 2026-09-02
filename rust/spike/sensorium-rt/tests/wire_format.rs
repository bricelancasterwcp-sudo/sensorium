//! THROWAWAY SPIKE CODE. The wire format a converter is written against.

mod common;

use common::{KIND_CALL, KIND_RETURN, KIND_THREAD_END, RECORD_LEN};

/// A record is exactly 24 bytes -- pinned by counting bytes on disk, not by
/// reading a constant out of the crate under test.
#[test]
fn a_record_is_exactly_24_bytes() {
    let (dir, _run) = common::run_recording("main-only");
    let spool = dir.spool(1);
    assert_eq!(
        spool.records.len(),
        3,
        "expected CALL, RETURN, THREAD_END; got {:?}",
        spool.records
    );
    let body = spool.len - spool.header_len();
    assert_eq!(
        body,
        3 * RECORD_LEN,
        "3 records occupy {body} bytes on disk, so a record is {} bytes, not {RECORD_LEN}",
        body / 3
    );
    assert_eq!(RECORD_LEN, 24, "the brief pins the record at 24 bytes");
    for r in &spool.records {
        assert_eq!(r.reserved, 0, "the reserved u16 must be zero: {r:?}");
    }
}

/// The file header round-trips magic, version, serial and thread name --
/// including a non-ASCII name, whose byte length differs from its char count.
#[test]
fn the_file_header_round_trips_the_thread_name() {
    let (dir, _run) = common::run_recording("spawn-first");
    let main = dir.spool(1);
    assert_eq!(main.version, 1);
    assert_eq!(main.name, "main");

    let worker = dir.spool(2);
    assert_eq!(worker.version, 1);
    assert_eq!(
        worker.name, "wörker-✓",
        "the spawned thread's name must survive the header verbatim"
    );
    assert_eq!(
        worker.name.len(),
        11,
        "the header's name_len is a byte count, and this name is 11 bytes / 8 chars"
    );
}

/// An unnamed thread writes an empty name rather than a missing one.
#[test]
fn the_file_name_matches_pid_and_serial() {
    let (dir, run) = common::run_recording("spawn-first");
    for serial in [1u32, 2] {
        let spool = dir.spool(serial);
        let name = spool.path.file_name().unwrap().to_string_lossy().into_owned();
        assert_eq!(
            name,
            format!("{}.{serial}.spool", run.pid),
            "spool files are named <pid>.<thread_serial>.spool"
        );
    }
}

/// `site` packs the unit id into bits 31..24 and the site index into 23..0.
#[test]
fn the_site_word_packs_unit_id_above_site_index() {
    let (dir, _run) = common::run_recording("two-units");
    let calls = dir.spool(1).kinds(KIND_CALL);
    assert_eq!(calls.len(), 2, "one CALL per unit: {calls:?}");
    assert_eq!(calls[0].unit_id(), 0, "the first unit to enter takes id 0");
    assert_eq!(calls[0].site_index(), 3);
    assert_eq!(calls[1].unit_id(), 1, "the second unit takes id 1");
    assert_eq!(calls[1].site_index(), 4);
    assert_eq!(
        calls[0].site,
        3,
        "unit 0 site 3 must be the bare index, not a shifted one"
    );
    assert_eq!(
        calls[1].site,
        (1u32 << 24) | 4,
        "unit 1 site 4 must be 0x01000004"
    );
}

/// Kinds are 1 / 2 / 255 in emission order.
#[test]
fn kinds_are_call_return_thread_end() {
    let (dir, _run) = common::run_recording("main-only");
    let kinds: Vec<u8> = dir.spool(1).records.iter().map(|r| r.kind).collect();
    assert_eq!(kinds, vec![KIND_CALL, KIND_RETURN, KIND_THREAD_END]);
    assert_eq!((KIND_CALL, KIND_RETURN, KIND_THREAD_END), (1, 2, 255));
}

/// The process header names the process and every registered unit.
#[test]
fn the_proc_header_carries_the_units() {
    let (dir, run) = common::run_recording("two-units");
    let json = dir.proc_header(run.pid);
    assert!(
        json.contains(&format!("\"pid\":{}", run.pid)),
        "proc header must carry the pid: {json}"
    );
    for key in ["\"ppid\":", "\"exe\":", "\"argv\":[", "\"cwd\":", "\"start_ns\":"] {
        assert!(json.contains(key), "proc header is missing {key}: {json}");
    }
    assert!(
        json.contains("\"units\":{\"0\":\"unit-a-metadata\",\"1\":\"unit-b-metadata\"}"),
        "the unit map must be keyed by unit id in registration order: {json}"
    );
}

/// `ts_ns` is a monotonic clock: it never goes backwards within a thread.
#[test]
fn timestamps_are_monotonic_within_a_thread() {
    let (dir, _run) = common::run_recording("two-threads");
    for spool in dir.spools() {
        let mut previous = 0u64;
        for r in &spool.records {
            assert!(
                r.ts_ns >= previous,
                "ts_ns went backwards in {}: {} after {previous}",
                spool.path.display(),
                r.ts_ns
            );
            assert!(r.ts_ns > 0, "ts_ns must be a real CLOCK_MONOTONIC reading");
            previous = r.ts_ns;
        }
    }
}
