//! The wire format, byte for byte, read by a parser written from the plan's
//! format block rather than from `src/spool.rs` (see `common/mod.rs`).

mod common;

use common::{
    Spec, TempDir, HEADER_FIXED, KIND_CALL, KIND_RETURN, KIND_THREAD_END, OUTCOME_NONE,
    RECORD_FIXED, TAG_NO_VALUE,
};

#[test]
fn header_and_records_are_exactly_the_documented_bytes() {
    let dir = TempDir::reserved("wire-header");
    let run = Spec::new("main-only").spool(dir.path()).run();

    let spools = dir.spools();
    assert_eq!(
        spools.len(),
        1,
        "one emitting thread, one spool: {spools:?}"
    );
    let s = &spools[0];

    assert_eq!(
        s.path.file_name().unwrap().to_string_lossy(),
        format!("{}.1.spool", run.pid),
        "spool files are named <pid>.<thread_serial>.spool"
    );
    assert_eq!(s.version, 2, "wire version");
    assert_eq!(s.flags, 0, "flags are reserved and zero in v1");
    assert_eq!(s.serial, 1, "the main thread is serial 1");
    assert_eq!(s.name, "main", "the header carries the thread name");
    assert_eq!(s.records_dropped, 0);
    assert_eq!(s.truncated, 0);
    assert_eq!(
        s.header_len(),
        HEADER_FIXED + 4,
        "28 fixed bytes then the name"
    );

    let kinds: Vec<u8> = s.records.iter().map(|r| r.kind).collect();
    assert_eq!(
        kinds,
        vec![KIND_CALL, KIND_RETURN, KIND_THREAD_END],
        "one frame on a thread that exits cleanly"
    );

    let call = &s.records[0];
    assert_eq!(call.unit_id(), 0, "the first unit to register is id 0");
    assert_eq!(call.site_index(), 7, "the site index the scenario passed");
    assert_eq!(
        call.site, 7,
        "unit 0 in bits 31..24 leaves the raw word equal to the index"
    );
    assert_eq!(
        call.outcome, OUTCOME_NONE,
        "outcome is 0 on every non-RETURN kind"
    );
    assert!(call.payload.is_empty(), "a CALL carries no payload");

    let ret = &s.records[1];
    assert_eq!(ret.site, call.site, "the RETURN closes the CALL's site");
    assert_eq!(ret.outcome, OUTCOME_NONE, "a -> () fn stashes nothing");
    assert_eq!(
        ret.payload,
        vec![TAG_NO_VALUE, 0],
        "tag 0, not truncated, no text"
    );

    let end = &s.records[2];
    assert_eq!(end.site, 0, "THREAD_END belongs to no site");
    assert_eq!(end.outcome, OUTCOME_NONE);
    assert!(end.payload.is_empty());

    assert!(
        s.records.windows(2).all(|w| w[0].seq < w[1].seq),
        "sequence numbers are strictly increasing: {:?}",
        s.records.iter().map(|r| r.seq).collect::<Vec<_>>()
    );
    assert_eq!(
        s.records[0].seq, 0,
        "the process-global sequence starts at 0"
    );
    assert!(
        s.records.windows(2).all(|w| w[0].ts_ns <= w[1].ts_ns),
        "CLOCK_MONOTONIC never goes backwards"
    );
    assert!(s.records[0].ts_ns > 0, "ts_ns is a real clock reading");

    let expected_len = s.header_len() + RECORD_FIXED + (RECORD_FIXED + 2) + RECORD_FIXED;
    assert_eq!(
        s.file_len, expected_len,
        "a thread that ends cleanly ftruncates its spool to exactly what it wrote"
    );
    assert!(
        !s.stopped_on_unwritten,
        "a truncated spool has no kind-0 tail to stop at"
    );
    assert_eq!(
        s.stopped_at, s.file_len,
        "the reader consumed the whole file"
    );
}

#[test]
fn the_proc_header_carries_the_process_and_its_units() {
    let dir = TempDir::reserved("wire-proc");
    let run = Spec::new("main-only").spool(dir.path()).run();
    let h = dir.proc_header(run.pid);

    assert_eq!(h.get("pid").u64(), u64::from(run.pid));
    assert_eq!(
        h.get("ppid").u64(),
        u64::from(std::process::id()),
        "the scenario's parent is this test process"
    );
    assert!(
        h.get("exe").str().ends_with("scenario"),
        "exe: {:?}",
        h.get("exe").str()
    );
    let argv: Vec<&str> = h.get("argv").arr().iter().map(|j| j.str()).collect();
    assert_eq!(argv.len(), 2, "argv: {argv:?}");
    assert_eq!(argv[1], "main-only");
    assert_eq!(
        h.get("cwd").str(),
        std::env::current_dir().unwrap().to_string_lossy(),
        "the scenario inherits this process's working directory"
    );
    assert!(h.get("start_ns").u64() > 0);
    assert!(
        h.get("start_realtime_ns").u64() > 1_600_000_000_000_000_000,
        "start_realtime_ns is CLOCK_REALTIME nanoseconds since the epoch, got {}",
        h.get("start_realtime_ns").u64()
    );
    assert_eq!(
        h.get("env").get("SENSORIUM_SPOOL").str(),
        dir.path().to_string_lossy(),
        "the full environment is in the header"
    );
    let eh = h.get("env_hash").str();
    assert_eq!(
        eh.len(),
        16,
        "env_hash is the first 16 hex chars of a sha256"
    );
    assert!(
        eh.chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()),
        "env_hash is lowercase hex: {eh:?}"
    );
    assert_eq!(
        h.get("units").obj().len(),
        1,
        "one unit ran, so one unit is mapped"
    );
    assert_eq!(h.get("units").get("0").str(), "scenario-unit-a");
    assert!(h.get("refused").is_null(), "nothing was refused");
    assert_eq!(h.get("rt_version").str(), "sensorium-rt 0.1.0");
}

/// A thread with no name: `name_len` is 0 and the records start at byte 28, the
/// header's whole fixed size. Nothing in the format needs a name to be present.
#[test]
fn a_thread_with_no_name_has_a_zero_length_name_field() {
    let dir = TempDir::reserved("wire-unnamed");
    Spec::new("unnamed-thread").spool(dir.path()).run();
    let s = dir.spool(2);
    assert_eq!(s.name, "", "std::thread::spawn names nothing");
    assert_eq!(s.header_len(), HEADER_FIXED, "records start at byte 28");
    let calls = s.of_kind(KIND_CALL);
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].site_index(), 76);
    assert!(s.has_thread_end());
    assert_eq!(
        s.file_len,
        HEADER_FIXED + RECORD_FIXED + (RECORD_FIXED + 2) + RECORD_FIXED
    );
}

/// A site index that needs all 24 of its bits must survive the site word.
#[test]
fn a_site_index_that_fills_all_twenty_four_bits_round_trips() {
    let dir = TempDir::reserved("wire-widesite");
    Spec::new("wide-site").spool(dir.path()).run();
    let call = dir.spool(1).of_kind(KIND_CALL).remove(0);
    assert_eq!(call.site_index(), 0x00ab_cdef);
    assert!(
        call.site_index() > u32::from(u16::MAX),
        "and it is wider than 16 bits"
    );
    assert_eq!(call.unit_id(), 0, "with nothing bled into the unit id");
    assert_eq!(call.site, 0x00ab_cdef);
}

/// The proc header is written through a temporary and renamed. A run that ends
/// cleanly leaves no temporary behind.
#[test]
fn the_proc_header_leaves_no_temporary_behind() {
    let dir = TempDir::reserved("wire-notmp");
    let run = Spec::new("two-units").spool(dir.path()).run();
    let left: Vec<String> = dir
        .walk()
        .iter()
        .map(|p| p.file_name().unwrap().to_string_lossy().into_owned())
        .collect();
    let mut expected = vec![
        format!("{}.proc.json", run.pid),
        format!("{}.1.spool", run.pid),
    ];
    expected.sort();
    let mut left_sorted = left.clone();
    left_sorted.sort();
    assert_eq!(
        left_sorted, expected,
        "the spool directory holds exactly these"
    );
}

#[test]
fn env_hash_follows_the_environment() {
    let dir_a = TempDir::reserved("wire-envhash");
    let run_a = Spec::new("main-only")
        .spool(dir_a.path())
        .env("SENSORIUM_SCENARIO_MARKER", "one")
        .run();
    let run_b = Spec::new("main-only")
        .spool(dir_a.path())
        .env("SENSORIUM_SCENARIO_MARKER", "one")
        .run();
    let run_c = Spec::new("main-only")
        .spool(dir_a.path())
        .env("SENSORIUM_SCENARIO_MARKER", "two")
        .run();

    let a = dir_a
        .proc_header(run_a.pid)
        .get("env_hash")
        .str()
        .to_owned();
    let b = dir_a
        .proc_header(run_b.pid)
        .get("env_hash")
        .str()
        .to_owned();
    let c = dir_a
        .proc_header(run_c.pid)
        .get("env_hash")
        .str()
        .to_owned();
    assert_eq!(a, b, "the same environment hashes the same");
    assert_ne!(a, c, "a changed variable changes the hash");
}
