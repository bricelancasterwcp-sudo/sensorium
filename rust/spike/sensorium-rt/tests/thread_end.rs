//! THROWAWAY SPIKE CODE. `THREAD_END`, and the loss a buffered spool implies.

mod common;

use common::KIND_THREAD_END;

/// A thread that exits cleanly ends its spool with `THREAD_END`, and it is the
/// LAST record.
#[test]
fn thread_end_is_the_last_record_of_a_thread_that_exits_cleanly() {
    let (dir, _run) = common::run_recording("clean-thread");
    let worker = dir.spool(2);
    let last = worker.records.last().expect("the worker recorded something");
    assert_eq!(
        last.kind, KIND_THREAD_END,
        "a cleanly exiting thread's last record must be THREAD_END: {:?}",
        worker.records
    );
    assert_eq!(
        worker.records.iter().filter(|r| r.kind == KIND_THREAD_END).count(),
        1,
        "exactly one THREAD_END per thread"
    );
    assert_eq!(last.site, 0, "THREAD_END belongs to no site");
    assert_eq!(last.outcome, 0, "THREAD_END carries no outcome");
}

/// The main thread's own spool gets `THREAD_END` too, from the thread-local
/// destructor that glibc runs at process exit.
#[test]
fn the_main_thread_spool_also_ends_with_thread_end() {
    let (dir, _run) = common::run_recording("main-only");
    let main = dir.spool(1);
    assert_eq!(
        main.records.last().expect("main recorded something").kind,
        KIND_THREAD_END
    );
}

/// `std::process::exit(0)` is NOT a total loss. glibc's `exit()` calls
/// `__call_tls_dtors()`, so the CALLING thread's spool is flushed and closed
/// exactly as if `main` had returned; only the other live threads lose their
/// buffered tails.
///
/// This is the row the first version of this crate's report got wrong, which is
/// why it is measured here rather than reasoned about. Task 3's driver and
/// Task 4's converter both depend on knowing which of the three rows they are
/// in.
#[test]
fn process_exit_flushes_the_calling_threads_spool() {
    let (dir, _run) = common::run_recording("exit-with-live-thread");
    let spools = dir.spools();
    assert_eq!(spools.len(), 2, "main and the blocked thread: {spools:?}");

    let main = dir.spool(1);
    assert!(
        main.has_thread_end(),
        "process::exit runs the calling thread's TLS destructors, so its spool \
         must be closed with THREAD_END: {:?}",
        main.records
    );
    assert_eq!(
        main.records.last().expect("main recorded something").kind,
        KIND_THREAD_END,
        "and THREAD_END must be last"
    );
    assert!(
        main.records.iter().any(|r| r.site_index() == 5),
        "main's own CALL/RETURN survived the exit: {:?}",
        main.records
    );

    let blocked = dir.spool(2);
    assert_eq!(blocked.name, "leaked");
    assert!(
        !blocked.has_thread_end(),
        "the still-running thread ran no destructor: {:?}",
        blocked.records
    );
    assert_eq!(
        blocked.len,
        blocked.header_len(),
        "and so it is header-only -- the same loss a leaked thread suffers, \
         not a bigger one"
    );
}

/// `std::process::abort()` runs no destructor on any thread. This is the only
/// row of the loss model that is a TOTAL loss: even the aborting thread's own
/// buffered records are gone.
///
/// Box note: this raises SIGABRT, so where `kernel.core_pattern` is a bare
/// filename rather than a pipe, `cargo test` will drop a core file in the
/// package directory. On this box it is piped to apport, so nothing lands.
#[test]
fn abort_loses_every_buffered_record_including_the_aborting_threads() {
    let dir = common::TempDir::reserved();
    let run = common::run_allow_failure("abort-with-live-thread", Some(dir.path()));
    assert!(
        !run.output.status.success(),
        "the scenario must actually abort, got {:?}",
        run.output.status
    );

    let spools = dir.spools();
    assert_eq!(spools.len(), 2, "both spools were opened: {spools:?}");
    for spool in &spools {
        assert!(
            !spool.has_thread_end(),
            "abort runs no destructor, so no spool can carry THREAD_END: {:?}",
            spool.records
        );
        assert_eq!(
            spool.len,
            spool.header_len(),
            "abort leaves {} at its flushed header and nothing more; found {:?}",
            spool.path.display(),
            spool.records
        );
    }
    assert_eq!(
        spools.iter().map(|s| s.name.as_str()).collect::<Vec<_>>(),
        vec!["main", "leaked"],
        "including the aborting thread's own, which is what makes this row \
         different from process::exit"
    );
}

/// THE DOCUMENTED LOSS. A thread still blocked when the process exits never
/// runs its thread-local destructor: its buffered records are gone and its
/// spool has no `THREAD_END`. The header is flushed at open, so the spool is
/// still identifiable -- which is what the converter's `live_threads` needs.
///
/// Rung 2 replaces the `BufWriter` with the `MAP_SHARED` mapping of spec §4,
/// where the kernel keeps these pages. This test pins the spike's loss so the
/// findings can report it as measured rather than assumed.
#[test]
fn a_thread_leaked_at_process_exit_loses_its_buffered_tail() {
    let (dir, _run) = common::run_recording("leak");
    let spools = dir.spools();
    assert_eq!(
        spools.len(),
        2,
        "main and the leaked thread each opened a spool: {spools:?}"
    );

    let main = dir.spool(1);
    assert!(
        main.has_thread_end(),
        "the main thread exited cleanly and must have THREAD_END"
    );
    assert!(
        main.records.iter().any(|r| r.site_index() == 5),
        "main's own frame must be recorded: {:?}",
        main.records
    );

    let leaked = dir.spool(2);
    assert_eq!(
        leaked.name, "leaked",
        "the header is flushed at open, so a leaked spool still names its thread"
    );
    assert!(
        !leaked.has_thread_end(),
        "a thread alive at process exit cannot have written THREAD_END: {:?}",
        leaked.records
    );
    assert!(
        leaked.records.is_empty(),
        "the leaked thread's two records were in the BufWriter and are lost; \
         found {:?}",
        leaked.records
    );
    assert_eq!(
        leaked.len,
        leaked.header_len(),
        "a leaked spool is exactly its flushed header"
    );
}
