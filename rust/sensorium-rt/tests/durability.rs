//! What a spool loses (`rust/HONESTY.md` §4), read off the bytes.
//!
//! Four rows, one per way a process can end while a thread is blocked in
//! `recv()` with N complete frames behind it. In every row the blocked thread's
//! spool holds all N frames complete and is followed by a kind-0 tail; only
//! `THREAD_END` is absent, because no destructor ran on that thread.
//!
//! Kinds 4 and 5 go through `Spool::record` exactly as kinds 1 and 2 do, so the
//! one-record bound is theirs too -- but "exactly as" is a claim, and the
//! err-flow rows below are what falsify it: a SIGKILL row and, under
//! `test-hooks`, the drop-accounting row with RAISE and HANDLED attempts in the
//! arithmetic.

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
    assert_eq!(header.get("rt_version").str(), "sensorium-rt 0.3.0");
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

/// The same SIGKILL row, on a thread whose every frame also wrote a RAISE and a
/// HANDLED: four records per iteration, all four kinds whole, the tail zero.
#[test]
fn sigkill_leaves_the_blocked_threads_err_records_whole() {
    use common::{KIND_CALL, KIND_HANDLED, KIND_RAISE, KIND_RETURN};

    let dir = TempDir::reserved("durability-kill-errflow");
    let marks = TempDir::created("durability-kill-errflow-marks");
    let ready = marks.path().join("ready");
    Spec::new("blocked-errflow")
        .arg(&N.to_string())
        .arg(ready.to_str().unwrap())
        .spool(dir.path())
        .run_and_kill(&ready);

    let s = blocked_spool(&dir);
    assert_eq!(
        s.records.len(),
        N * 4,
        "four records per iteration: CALL, RAISE, HANDLED, RETURN"
    );
    assert!(!s.has_thread_end(), "the thread never returned");
    assert!(
        s.stopped_on_unwritten,
        "the reader must stop at a kind-0 record, not at EOF"
    );
    assert!(s.tail_is_zero, "and the mapping past it is untouched");
    assert_eq!(s.records_dropped, 0);

    for (i, r) in s.records.iter().enumerate() {
        let iteration = (i / 4) as u32;
        let (kind, site) = match i % 4 {
            0 => (KIND_CALL, 600 + iteration),
            1 => (KIND_RAISE, 700 + iteration),
            2 => (KIND_HANDLED, 800 + iteration),
            _ => (KIND_RETURN, 600 + iteration),
        };
        assert_eq!(
            (r.kind, r.site_index()),
            (kind, site),
            "record {i} is out of order or torn"
        );
    }
    // Every err record read back whole: the payload parses, and its flags agree
    // with what it carries.
    for (kind, _, e) in s.err_sites() {
        assert!(kind == KIND_RAISE || kind == KIND_HANDLED);
        assert_eq!(e.type_name.as_deref(), Some("u8"));
        assert_eq!(e.msg.as_deref(), Some("7"));
    }
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

/// The same accounting with err records in it: a RAISE and a HANDLED are
/// attempted on every iteration whether or not the frame's CALL was written, so
/// the arithmetic names them separately from the RETURNs.
#[cfg(feature = "test-hooks")]
#[test]
fn a_spool_that_cannot_grow_counts_the_err_records_it_drops_too() {
    use common::{KIND_CALL, KIND_HANDLED, KIND_RAISE, KIND_RETURN};

    const LIMIT: u64 = 65_536;
    const ITERATIONS: u64 = 3_000;

    let dir = TempDir::reserved("durability-limit-errflow");
    let run = Spec::new("errflow-spool-limit")
        .arg(&ITERATIONS.to_string())
        .spool(dir.path())
        .env("SENSORIUM_TEST_SPOOL_LIMIT", LIMIT.to_string())
        .run();
    assert_eq!(run.says_u64("iterations"), ITERATIONS);

    let s = dir.spool(1);
    assert!(s.file_len as u64 <= LIMIT, "the spool grew past its limit");
    let calls = s.of_kind(KIND_CALL).len() as u64;
    let written = s.records.len() as u64;
    assert!(written < ITERATIONS * 4, "the limit has to bite: {written}");
    assert!(
        s.of_kind(KIND_RAISE).len() > 0 && s.of_kind(KIND_HANDLED).len() > 0,
        "some err records were written before the limit bit"
    );
    // Each iteration attempts a CALL, a RAISE and a HANDLED unconditionally --
    // an err site does not need its frame's CALL to have been written -- and a
    // RETURN only where the CALL was. THREAD_END is one more attempt.
    let attempted = 3 * ITERATIONS + calls + 1;
    assert_eq!(
        s.records_dropped,
        attempted - written,
        "records_dropped is what the writer knew it could not write \
         ({attempted} attempted, {written} written)"
    );
    assert!(s.records_dropped > 0);
    // A RETURN is ATTEMPTED for every written CALL, but the spool can break
    // between the two -- so at most one frame (the last one whose CALL fit) is
    // left without its RETURN on disk.
    let returns = s.of_kind(KIND_RETURN).len() as u64;
    assert!(
        returns <= calls && calls - returns <= 1,
        "{calls} CALLs written, {returns} RETURNs: a broken spool costs at most \
         the frame it broke inside"
    );
    assert!(!s.has_thread_end());
}
