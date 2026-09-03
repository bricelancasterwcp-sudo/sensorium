//! What a spool loses (`rust/HONESTY.md` §4), read off the bytes.
//!
//! Four rows, one per way a process can end while a thread is blocked in
//! `recv()` with N complete frames behind it. In every row the blocked thread's
//! spool holds all N frames complete and is followed by a kind-0 tail; only
//! `THREAD_END` is absent, because no destructor ran on that thread.

mod common;

use common::{Spec, SpoolFile, TempDir};

/// `enter`s the blocked thread makes before it parks. Each is a CALL and a
/// RETURN.
const N: usize = 50;

fn assert_blocked_thread_is_whole(s: &SpoolFile, row: &str) {
    assert_eq!(
        s.records.len(),
        N * 2,
        "{row}: the blocked thread wrote {} of {} records",
        s.records.len(),
        N * 2
    );
    assert!(
        !s.has_thread_end(),
        "{row}: a thread that never returned cannot have written THREAD_END"
    );
    assert!(
        s.stopped_on_unwritten,
        "{row}: the reader must stop at a kind-0 record, not at EOF"
    );
    assert!(
        s.tail_is_zero,
        "{row}: everything after the last complete record is untouched mapping"
    );
    assert_eq!(s.records_dropped, 0, "{row}: nothing was knowingly dropped");
    for (i, r) in s.records.iter().enumerate() {
        let expected_site = 100 + (i / 2) as u32;
        assert_eq!(
            r.site_index(),
            expected_site,
            "{row}: record {i} is out of order or torn"
        );
    }
}

fn blocked_spool(dir: &TempDir) -> SpoolFile {
    dir.spool_named("blocked")
}

#[test]
fn a_return_from_main_leaves_the_blocked_threads_records_whole() {
    let dir = TempDir::reserved("durability-mainreturn");
    Spec::new("blocked-main-return")
        .arg(&N.to_string())
        .spool(dir.path())
        .run();
    assert_blocked_thread_is_whole(&blocked_spool(&dir), "return from main");
    assert!(
        dir.spool(1).has_thread_end(),
        "main's own thread-local destructor did run"
    );
}

#[test]
fn process_exit_leaves_the_blocked_threads_records_whole() {
    let dir = TempDir::reserved("durability-exit");
    Spec::new("blocked-exit")
        .arg(&N.to_string())
        .spool(dir.path())
        .run();
    assert_blocked_thread_is_whole(&blocked_spool(&dir), "process::exit(0)");
    assert!(
        dir.spool(1).has_thread_end(),
        "glibc's exit() runs the calling thread's TLS destructors"
    );
}

#[test]
fn abort_leaves_the_blocked_threads_records_whole() {
    let dir = TempDir::reserved("durability-abort");
    let run = Spec::new("blocked-abort")
        .arg(&N.to_string())
        .spool(dir.path())
        .allow_failure()
        .run();
    assert!(
        !run.output.status.success(),
        "abort() does not exit cleanly"
    );
    assert_blocked_thread_is_whole(&blocked_spool(&dir), "abort()");
    let main = dir.spool(1);
    assert!(
        !main.has_thread_end(),
        "abort() runs no destructor on any thread, main's included"
    );
    assert_eq!(
        main.records.len(),
        4,
        "and main's own two frames are still on disk, which is the whole point"
    );
    assert!(main.stopped_on_unwritten && main.tail_is_zero);
}

#[test]
fn sigkill_leaves_the_blocked_threads_records_whole() {
    let dir = TempDir::reserved("durability-kill");
    let marks = TempDir::created("durability-kill-marks");
    let ready = marks.path().join("ready");
    let pid = Spec::new("blocked-forever")
        .arg(ready.to_str().unwrap())
        .spool(dir.path())
        .run_and_kill(&ready);

    assert_blocked_thread_is_whole(&blocked_spool(&dir), "SIGKILL");
    let main = dir.spool(1);
    assert!(!main.has_thread_end(), "SIGKILL runs nothing");
    assert_eq!(main.records.len(), 4);

    // The proc header is rewritten at every unit registration, and this process
    // was killed at an arbitrary instant. It has to be whole JSON: written to a
    // temporary and renamed, never truncated in place, or one unlucky kill costs
    // the entire run rather than the one record §4 bounds it to.
    let header = dir.proc_header(pid);
    assert_eq!(header.get("pid").u64(), u64::from(pid));
    assert_eq!(header.get("rt_version").str(), "sensorium-rt 0.1.0");
    assert!(header.get("refused").is_null());
    let units = header.get("units");
    assert_eq!(
        units.obj().len(),
        2,
        "both units this process registered are named"
    );
    assert_eq!(units.get("0").str(), "scenario-unit-a");
    assert_eq!(units.get("1").str(), "scenario-unit-b");
    assert!(
        header.get("env").opt("SENSORIUM_SPOOL").is_some(),
        "and the rest of the header survived with it"
    );
}

/// A synthetic disk-full: the runtime cannot grow the spool, goes inert for
/// that thread, and counts every record it could not write.
#[cfg(feature = "test-hooks")]
#[test]
fn a_spool_that_cannot_grow_counts_what_it_drops() {
    use common::{KIND_CALL, KIND_RETURN};

    const LIMIT: u64 = 65_536;
    const ITERATIONS: u64 = 6_000;

    let dir = TempDir::reserved("durability-limit");
    let run = Spec::new("spool-limit")
        .arg(&ITERATIONS.to_string())
        .spool(dir.path())
        .env("SENSORIUM_TEST_SPOOL_LIMIT", LIMIT.to_string())
        .run();
    assert_eq!(run.says_u64("iterations"), ITERATIONS);

    let s = dir.spool(1);
    assert!(
        s.file_len as u64 <= LIMIT,
        "the spool grew past its limit: {} > {LIMIT}",
        s.file_len
    );
    let calls = s.of_kind(KIND_CALL).len() as u64;
    let written = s.records.len() as u64;
    assert!(
        written < ITERATIONS * 2,
        "the limit has to bite: {written} records written for {ITERATIONS} frames"
    );
    // Every iteration attempts a CALL; only an iteration whose CALL was written
    // goes on to attempt a RETURN. THREAD_END is one more attempt.
    let attempted = ITERATIONS + calls + 1;
    assert_eq!(
        s.records_dropped,
        attempted - written,
        "records_dropped is what the writer knew it could not write \
         ({attempted} attempted, {written} written)"
    );
    assert!(s.records_dropped > 0);
    assert!(
        !s.has_thread_end(),
        "THREAD_END could not be written either"
    );
    assert_eq!(s.of_kind(KIND_RETURN).len() as u64, written - calls);
}
